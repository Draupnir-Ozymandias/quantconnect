import copy
import ast
import inspect
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError,payload_hash
from execution_truth.market_stream import collect_market_stream as baseline_collect,stream_plan,verify_stream_log
from infra.stream.recorder_completion_lane import collect_with_completion as collect_market_stream
from infra.stream.recorder_completion_lane import CompletionStreamLog as SegmentedStreamLog
from infra.stream.recorder_completion import CompletionWitnesses,verify_completion
from tests.test_market_stream import Clock,Socket
from tests.test_taker_replay import raw_bundle


class CompletionTests(unittest.TestCase):
    def setup_case(self,root,**kwargs):
        clock=Clock();spec=stream_plan(raw_bundle(),segmented=True,max_seconds=4)
        observer=CompletionWitnesses(spec,'test.boot',clock=clock.utc,monotonic=clock.mono,
                                     execute=True,**kwargs)
        return clock,spec,observer

    def capture(self,root,**kwargs):
        clock,spec,observer=self.setup_case(root,**kwargs)
        socket=Socket(clock,['PONG','PONG'])
        collect_market_stream(raw_bundle(),spec,root,connector=lambda:socket,clock=clock.utc,
                              monotonic=clock.mono,pause=clock.pause,completion_observer=observer)
        report=observer.snapshot(root)
        return report,observer

    def manual(self,root):
        clock,spec,observer=self.setup_case(root)
        observer.validate_spec(spec)
        log=SegmentedStreamLog(root,clock.utc,clock.mono,spec['storage'],completion_observer=observer)
        log.append('session_start',{'spec':spec,'spec_sha256':payload_hash(spec)})
        observer.application_return('PONG',1)
        log.append('frame',{'connection':1,'raw_text':'PONG','classification':[{'event_type':'PONG','scope':'heartbeat'}]})
        return log,observer

    def signed(self,report):
        report['completion_sha256']=payload_hash({k:v for k,v in report.items() if k!='completion_sha256'})
        return report

    def test_real_archive_population_and_durable_linkage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';report,observer=self.capture(root)
            result=verify_completion(report,root,expected_domain='test.boot')
            self.assertTrue(result['completion_linkage_verified'])
            self.assertEqual(result['frames'],2)
            self.assertTrue(result['barriers']>=2)
            self.assertTrue(all(r['durable_upper_seconds']>=r['append_upper_seconds'] for r in result['latencies']))
            self.assertFalse(result['acceptance_demonstrated']);self.assertFalse(result['orders_authorized'])
            with self.assertRaises(ContractError):observer.snapshot(root)

    def test_observation_does_not_change_archive_bytes_or_fsync_population(self):
        with tempfile.TemporaryDirectory() as tmp:
            archives=[];counts=[]
            for enabled in (False,True):
                root=Path(tmp)/str(enabled);clock,spec,observer=self.setup_case(root)
                socket=Socket(clock,['PONG','PONG'])
                native=os.fsync
                with patch('execution_truth.stream_segments.os.fsync',wraps=native) as sync:
                    if enabled:
                        collect_market_stream(raw_bundle(),spec,root,connector=lambda:socket,clock=clock.utc,
                            monotonic=clock.mono,pause=clock.pause,completion_observer=observer)
                    else:
                        baseline_collect(raw_bundle(),spec,root,connector=lambda:socket,clock=clock.utc,
                            monotonic=clock.mono,pause=clock.pause)
                counts.append(sync.call_count)
                archives.append({p.name:p.read_bytes() for p in root.iterdir()})
            self.assertEqual(archives[0],archives[1]);self.assertEqual(counts[0],counts[1])

    def test_capacity_failure_preserves_raws(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';report,_=self.capture(root,capacity=1)
            self.assertFalse(report['complete']);self.assertEqual(len(report['frames']),1)
            self.assertEqual(verify_stream_log(root)['frames'],2)
            with self.assertRaises(ContractError):verify_completion(report,root,expected_domain='test.boot')

    def test_observation_exception_does_not_swallow_native_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            observer.application_return('PONG',1)
            with patch.object(observer,'boundary',side_effect=RuntimeError('observer fault')):
                log.append('frame',{'connection':1,'raw_text':'PONG','classification':[{'event_type':'PONG','scope':'heartbeat'}]})
            log.append('session_end',{'status':'lifecycle_stop'});log.close()
            report=observer.snapshot(root)
            self.assertFalse(report['complete']);self.assertEqual(verify_stream_log(root)['frames'],2)

    def test_write_failure_is_retained_and_not_replayed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            observer.application_return('PONG',1)
            with patch.object(log.writer,'write',side_effect=OSError('write fault')) as write:
                with self.assertRaises(OSError):log.append('frame',{'connection':1,'raw_text':'PONG','classification':[{'event_type':'PONG','scope':'heartbeat'}]})
                self.assertEqual(write.call_count,1)
            log.close();report=observer.snapshot(root)
            self.assertFalse(report['complete']);self.assertIn('append_failed',report['failure'])

    def test_sync_failure_has_no_success_watermark_or_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            before=len(observer.barriers)
            with patch('execution_truth.stream_segments.os.fsync',side_effect=OSError('sync fault')) as sync:
                with self.assertRaises(OSError):log.sync()
                self.assertEqual(sync.call_count,1)
            self.assertEqual(len(observer.barriers),before)
            log.close();report=observer.snapshot(root)
            self.assertFalse(report['complete']);self.assertIn('sync_failed',report['failure'])

    def test_crash_prefix_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            log.writer.close();log.raw.close()
            report=observer.snapshot(root)
            self.assertFalse(report['complete']);self.assertIsNone(report['manifest_file_sha256'])

    def test_missing_footer_cannot_pass_even_if_manifest_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            log.close();report=observer.snapshot(root)
            with self.assertRaises(ContractError):verify_completion(report,root,expected_domain='test.boot')

    def test_duplicate_raws_keep_distinct_occurrence_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';report,_=self.capture(root)
            self.assertNotEqual(report['frames'][0]['ordinal'],report['frames'][1]['ordinal'])
            tampered=copy.deepcopy(report);tampered['frames'][1]['ordinal']=tampered['frames'][0]['ordinal']
            with self.assertRaises(ContractError):verify_completion(self.signed(tampered),root,expected_domain='test.boot')

    def test_rehashed_population_clock_watermark_and_authority_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';report,_=self.capture(root)
            variants=[]
            value=copy.deepcopy(report);value['frames'].pop();variants.append(value)
            value=copy.deepcopy(report);value['frames'][0]['append_completed']=-1;variants.append(value)
            value=copy.deepcopy(report);value['barriers'][-1]['record_sha256']='0'*64;variants.append(value)
            value=copy.deepcopy(report);value['orders_authorized']=True;variants.append(value)
            value=copy.deepcopy(report);value['barriers']=[];variants.append(value)
            value=copy.deepcopy(report);value['frames'][0]['ordinal']=True;variants.append(value)
            for value in variants:
                with self.assertRaises(ContractError):verify_completion(self.signed(value),root,expected_domain='test.boot')
            with self.assertRaises(ContractError):verify_completion(report,root,expected_domain='other.boot')

    def test_constructor_and_single_use_barriers(self):
        clock=Clock();spec=stream_plan(raw_bundle(),segmented=True)
        for kwargs in ({},{'execute':True,'capacity':True},{'execute':True,'capacity':0},
                       {'execute':True,'barrier_capacity':65537}):
            with self.assertRaises(ContractError):
                CompletionWitnesses(spec,'test.boot',clock=clock.utc,monotonic=clock.mono,**kwargs)
        observer=CompletionWitnesses(spec,'test.boot',clock=clock.utc,monotonic=clock.mono,execute=True)
        with self.assertRaises(ContractError):observer.validate_spec({})
        observer.validate_spec(spec)
        with self.assertRaises(ContractError):observer.validate_spec(spec)

    def test_bad_clock_disables_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            clock,spec,observer=self.setup_case(Path(tmp)/'stream')
            observer.monotonic=lambda:float('nan')
            observer.application_return('PONG',1)
            self.assertIsNotNone(observer.failure)

    def test_unlinked_raw_or_connection_disables_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            observer.application_return('PONG',1)
            log.append('frame',{'connection':2,'raw_text':'PONG','classification':[{'event_type':'PONG','scope':'heartbeat'}]})
            log.close();self.assertFalse(observer.snapshot(root)['complete'])

    def test_barrier_capacity_does_not_change_native_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';report,_=self.capture(root,barrier_capacity=1)
            self.assertFalse(report['complete']);self.assertEqual(len(report['barriers']),1)
            self.assertTrue(verify_stream_log(root)['manifest_present'])

    def test_flush_failure_never_creates_successful_barrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            before=len(observer.barriers)
            with patch.object(log.writer,'flush',side_effect=OSError('flush fault')):
                with self.assertRaises(OSError):log.sync()
            self.assertEqual(len(observer.barriers),before)
            log.close();report=observer.snapshot(root)
            self.assertFalse(report['complete']);self.assertIn('sync_failed',report['failure'])

    def test_application_callback_exception_preserves_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';clock,spec,observer=self.setup_case(root)
            socket=Socket(clock,['PONG','PONG'])
            with patch.object(observer,'application_return',side_effect=RuntimeError('callback fault')) as callback:
                collect_market_stream(raw_bundle(),spec,root,connector=lambda:socket,clock=clock.utc,
                    monotonic=clock.mono,pause=clock.pause,completion_observer=observer)
            self.assertEqual(callback.call_count,1)
            self.assertEqual(verify_stream_log(root)['frames'],2)
            self.assertFalse(observer.snapshot(root)['complete'])

    def test_clock_binding_and_legacy_mode_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';clock,spec,observer=self.setup_case(root)
            with self.assertRaises(ContractError):
                collect_market_stream(raw_bundle(),spec,root,clock=clock.utc,
                    monotonic=lambda:0,pause=clock.pause,completion_observer=observer)
            self.assertFalse(root.exists())
            legacy=stream_plan(raw_bundle(),max_seconds=4)
            with self.assertRaises(ContractError):
                collect_market_stream(raw_bundle(),legacy,root,clock=clock.utc,
                    monotonic=clock.mono,pause=clock.pause,completion_observer=observer)

    def test_regressed_clock_and_unfinished_barrier_remain_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            observer.boundary('sync_begin',ordinal=log.ordinal-1,record_sha256=log.previous)
            observer.monotonic=lambda:-1
            observer.boundary('sync_complete')
            log.close();report=observer.snapshot(root)
            self.assertFalse(report['complete']);self.assertIsNotNone(report['unfinished_barrier'])

    def test_sideband_encoded_limit_refuses_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';clock,spec,observer=self.setup_case(root)
            socket=Socket(clock,['PONG','PONG'])
            collect_market_stream(raw_bundle(),spec,root,connector=lambda:socket,clock=clock.utc,
                monotonic=clock.mono,pause=clock.pause,completion_observer=observer)
            with patch.dict('infra.stream.recorder_completion.POLICY',{'max_encoded_bytes':1}):
                with self.assertRaises(ContractError):observer.snapshot(root)
            self.assertEqual(verify_stream_log(root)['frames'],2)

    def test_observer_disable_failure_cannot_swallow_writer_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';log,observer=self.manual(root)
            with patch.object(observer,'boundary',side_effect=RuntimeError('fault')), \
                    patch.object(observer,'disable',side_effect=RuntimeError('disable fault')):
                log.append('session_end',{'status':'lifecycle_stop'})
            log.close()
            self.assertTrue(verify_stream_log(root)['session_end_present'])

    def test_no_default_public_connector_or_reference_source_drift(self):
        from infra.stream import recorder_completion_lane as lane
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'stream';clock,spec,observer=self.setup_case(root)
            with self.assertRaises(ContractError):
                collect_market_stream(raw_bundle(),spec,root,clock=clock.utc,
                    monotonic=clock.mono,pause=clock.pause,completion_observer=observer)
            self.assertFalse(root.exists())
            with patch.dict(lane.REFERENCE_FILES,{'execution_truth/market_stream.py':'0'*64}):
                with self.assertRaises(ContractError):lane.verify_reference_sources()

    def test_reference_control_flow_unchanged_except_explicit_hooks(self):
        from execution_truth import market_stream,stream_segments
        from infra.stream import recorder_completion_lane as lane
        class StripHooks(ast.NodeTransformer):
            def visit_If(self,node):
                if any(isinstance(n,ast.Name) and n.id=='completion_observer' for n in ast.walk(node.test)):
                    return None
                if (isinstance(node.test,ast.Compare) and isinstance(node.test.left,ast.Name)
                        and node.test.left.id=='connector'):
                    return None
                return self.generic_visit(node)
            def visit_Expr(self,node):
                if (isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name)
                        and node.value.func.id=='verify_reference_sources'):
                    return None
                return self.generic_visit(node)
            def visit_Name(self,node):
                if node.id=='CompletionStreamLog':node.id='SegmentedStreamLog'
                return node
            def visit_ImportFrom(self,node):
                if node.module.startswith('execution_truth.'):
                    node.module=node.module[len('execution_truth.'):];node.level=1
                return node
        reference=ast.parse(inspect.getsource(market_stream.collect_market_stream))
        candidate=ast.parse(inspect.getsource(lane.collect_with_completion))
        f=candidate.body[0];f.name=reference.body[0].name
        f.args.kwonlyargs.pop();f.args.kw_defaults.pop()
        candidate=StripHooks().visit(candidate)
        self.assertEqual(ast.dump(reference),ast.dump(candidate))
        class StripWriterHooks(ast.NodeTransformer):
            def visit_If(self,node):
                if any(isinstance(n,ast.Attribute) and n.attr=='completion_observer' for n in ast.walk(node.test)):
                    return None
                return self.generic_visit(node)
            def visit_Try(self,node):
                return [self.visit(n) for n in node.body]
        import textwrap
        for name in ('append','sync','_seal'):
            reference=ast.parse(textwrap.dedent(inspect.getsource(getattr(stream_segments.SegmentedStreamLog,name))))
            candidate=ast.parse(textwrap.dedent(inspect.getsource(getattr(lane.CompletionStreamLog,name))))
            candidate=StripWriterHooks().visit(candidate)
            self.assertEqual(ast.dump(reference),ast.dump(candidate),name)
