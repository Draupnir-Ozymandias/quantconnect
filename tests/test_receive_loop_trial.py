from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import receive_loop_trial as trial, receive_loop_overhead as plan
from infra.stream import receive_loop_contract as loop, burst_reader_comparison as burst
from tests.test_reader_comparison import corpus
from tests.test_receive_adapter import AVAILABLE


def fixture_worker(role,root,selected):
    # Test-only tiny workload; not exposed by the worker CLI or a benchmark receipt.
    digest=burst.load_corpus(Path(root)/'corpus.json')['corpus_sha256']
    with patch.object(plan,'CORPUS_SHA256',digest), patch.object(burst,'POLICY',dict(
            burst.POLICY,cycles=1,phases=[{'rate':500,'seconds':.01},{'rate':3000,'seconds':.001}])):
        if role=='consume': trial.consume(root,0,selected,require_isolation=False)
        else: trial.produce(root,0,selected)


def synthetic_cases():
    cases=[]
    for pair in range(3):
        for selected in ('baseline','instrumented'):
            cases.append({'pair':pair,'lane':selected,'eligible':30000,'linked':30000,
                'sideband_complete':True,'rss_max_bytes':100,'rss_sample_count':8,
                'metrics':{'messages':30000,'unknown_receive_records':0,'recovery_generations':0,
                    'consumer_timed_cpu_seconds':10,
                    'phase_windows':[{'target_rate':500,'attained_begin_messages_per_second':500},
                                     {'target_rate':3000,'attained_begin_messages_per_second':3000}],
                    'phases':{rate:{'producer_deadline_lateness':{'max_seconds':.01},
                        'producer_begin_to_delivery_upper':{'p99_seconds':.1,'max_seconds':.2}}
                              for rate in ('500','3000')}}})
    return cases


class ReceiveLoopTrialGateTests(unittest.TestCase):
    def test_good_ratios_never_replace_independent_resource_origin_gate(self):
        result=trial.evaluate_metrics(synthetic_cases())
        self.assertEqual(result['metric_gate'],'pass')
        self.assertEqual(result['advancement'],'inconclusive')
        self.assertFalse(result['public_rollout_authorized'])

    def test_one_pair_failure_not_rescued_by_other_pairs(self):
        cases=synthetic_cases(); cases[1]['metrics']['consumer_timed_cpu_seconds']=11
        result=trial.evaluate_metrics(cases)
        self.assertEqual(result['metric_gate'],'reject')
        self.assertIn('0:cpu_regression',result['failures'])

    def test_missing_zero_invalid_producer_and_sampling_inconclusive(self):
        for change in (lambda c:c[0].update(rss_max_bytes=None),
                       lambda c:c[0]['metrics'].update(consumer_timed_cpu_seconds=0),
                       lambda c:c[0]['metrics']['phase_windows'][0].update(attained_begin_messages_per_second=450),
                       lambda c:c[0].update(rss_sample_count=7)):
            cases=synthetic_cases(); change(cases)
            self.assertEqual(trial.evaluate_metrics(cases)['metric_gate'],'inconclusive')

    def test_coverage_incomplete_and_duplicate_population_rejected(self):
        cases=synthetic_cases(); cases[1]['linked']=29999
        self.assertEqual(trial.evaluate_metrics(cases)['metric_gate'],'reject')
        with self.assertRaises(ContractError): trial.evaluate_metrics(cases[:-1])
        cases[-1]=deepcopy(cases[0])
        with self.assertRaises(ContractError): trial.evaluate_metrics(cases)
        for pair,selected in ((True,'baseline'),(3,'baseline'),(0,'public')):
            with self.assertRaises(ContractError): trial.case_path('/tmp/test',pair,selected)

    def test_nonfinite_negative_metrics_fail_closed(self):
        for value in (float('nan'),float('inf'),-1,True):
            cases=synthetic_cases(); cases[1]['metrics']['consumer_timed_cpu_seconds']=value
            with self.assertRaises(ContractError): trial.evaluate_metrics(cases)

    def test_every_ratio_and_incomplete_observation_gates(self):
        for change in (lambda c:c[1].update(sideband_complete=False),
                       lambda c:c[1].update(rss_max_bytes=112),
                       lambda c:c[1]['metrics']['phases']['500']['producer_begin_to_delivery_upper'].update(p99_seconds=.11),
                       lambda c:c[1]['metrics']['phases']['3000']['producer_begin_to_delivery_upper'].update(max_seconds=.23)):
            cases=synthetic_cases(); change(cases)
            self.assertEqual(trial.evaluate_metrics(cases)['metric_gate'],'reject')

    def test_declared_interval_order_not_case_listing_order(self):
        cases=synthetic_cases(); by={(c['pair'],c['lane']):c for c in cases}
        for index,key in enumerate([(0,'baseline'),(0,'instrumented'),(1,'instrumented'),
                                    (1,'baseline'),(2,'baseline'),(2,'instrumented')]):
            by[key]['measurement']={'begin_monotonic':index*10,
                'post_window_finished_monotonic':index*10+5,'consumer_identity':{'boot_id':'same'}}
        self.assertTrue(trial.measured_order(cases))
        by[(1,'baseline')]['measurement']['begin_monotonic']=1
        self.assertFalse(trial.measured_order(cases))


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class ReceiveLoopTrialFixtureTests(unittest.TestCase):
    def test_private_workers_both_lanes_and_independent_tamper_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json'; c=corpus(); source.write_text(json.dumps(c))
            root=Path(tmp)/'run'; contract=loop.declare(plan.ANALYSIS_SHA256,loop.runtime_receipt())
            with patch.object(plan,'CORPUS_SHA256',c['corpus_sha256']):
                declaration=plan.declare(source,contract); trial.stage(root,declaration,source)
                with self.assertRaises(FileExistsError): trial.stage(root,declaration,source)
                for selected in ('baseline','instrumented'):
                    def command(role):
                        return [sys.executable,'-c','from tests.test_receive_loop_trial import fixture_worker; fixture_worker('
                                +repr(role)+','+repr(str(root))+','+repr(selected)+')']
                    producer=subprocess.Popen(command('produce'))
                    try:
                        ready=root/'0'/selected/'ready.json'; deadline=time.monotonic()+10
                        while not ready.exists():
                            if time.monotonic()>deadline: self.fail('fixture producer did not become ready')
                            time.sleep(.01)
                        result=subprocess.run(command('consume'),capture_output=True,text=True,timeout=20)
                        self.assertEqual(result.returncode,0,result.stderr)
                        self.assertEqual(producer.wait(timeout=10),0)
                        with patch.object(burst,'POLICY',dict(burst.POLICY,cycles=1,
                                phases=[{'rate':500,'seconds':.01},{'rate':3000,'seconds':.001}])):
                            verified=trial.verify_case(root,0,selected,require_isolation=False)
                            self.assertEqual(verified['metrics']['messages'],8)
                            self.assertEqual(verified['eligible'],8)
                            if selected=='instrumented': self.assertEqual(verified['linked'],8)
                            # Audit is repeatable, not a mutable cached-report trust path.
                            self.assertEqual(trial.verify_case(root,0,selected,False)['case_report_sha256'],verified['case_report_sha256'])
                            path=root/'0'/selected/'measurement.json'; bad=json.loads(path.read_text())
                            original=deepcopy(bad)
                            bad['begin_monotonic']=bad['end_monotonic']
                            bad.pop('measurement_sha256'); bad['measurement_sha256']=payload_hash(bad)
                            path.write_text(json.dumps(bad))
                            with self.assertRaises(ContractError): trial.verify_case(root,0,selected,False)
                            path.write_text(json.dumps(original))
                            deliveries=root/'0'/selected/'deliveries.json'; saved=json.loads(deliveries.read_text())
                            bad_delivery=deepcopy(saved); bad_delivery['stamps'][0]['monotonic_after']+=1
                            bad_delivery.pop('delivery_sha256'); bad_delivery['delivery_sha256']=payload_hash(bad_delivery)
                            deliveries.write_text(json.dumps(bad_delivery))
                            with self.assertRaises(ContractError): trial.verify_case(root,0,selected,False)
                            deliveries.write_text(json.dumps(saved))
                            bad=deepcopy(original)
                            bad['stream_spec_sha256']='f'*64; bad.pop('measurement_sha256')
                            bad['measurement_sha256']=payload_hash(bad); path.write_text(json.dumps(bad))
                            with self.assertRaises(ContractError): trial.verify_case(root,0,selected,False)
                        replay=subprocess.run(command('consume'),capture_output=True,text=True,timeout=10)
                        self.assertNotEqual(replay.returncode,0)
                    finally:
                        if producer.poll() is None: producer.terminate(); producer.wait(timeout=5)

    def test_preconnect_failure_retains_partial_receipts_and_refuses_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json'; c=corpus(); source.write_text(json.dumps(c))
            root=Path(tmp)/'run'; contract=loop.declare(plan.ANALYSIS_SHA256,loop.runtime_receipt())
            with patch.object(plan,'CORPUS_SHA256',c['corpus_sha256']):
                trial.stage(root,plan.declare(source,contract),source)
                with trial.scope(): declaration,_,spec=trial.context(root)
                case=root/'0'/'baseline'; case.mkdir(parents=True)
                identity=burst.identity(); identity['pid']+=10000
                trial.signed(case/'ready.json',{'uri':'ws://127.0.0.1:1','plan_sha256':declaration['plan_sha256'],
                    'mode':'recorder','receive_policy':'v3','fixture_base_utc':spec['event_start_at_utc'],
                    'origin_monotonic':time.monotonic(),'producer_identity':identity},'ready_sha256')
                with patch.object(trial.market_stream,'collect_market_stream',side_effect=RuntimeError('fixture fault')):
                    with self.assertRaises(ContractError): trial.consume(root,0,'baseline',require_isolation=False)
                self.assertTrue((case/'failure.json').exists())
                self.assertTrue((case/'measurement.json').exists())
                self.assertEqual(burst.read(case/'deliveries.json','delivery_sha256')['raws'],[])
                with self.assertRaises(FileExistsError): trial.consume(root,0,'baseline')

    def test_public_uri_rejected_before_any_adapter_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'input.json'; c=corpus(); source.write_text(json.dumps(c))
            root=Path(tmp)/'run'; contract=loop.declare(plan.ANALYSIS_SHA256,loop.runtime_receipt())
            with patch.object(plan,'CORPUS_SHA256',c['corpus_sha256']):
                trial.stage(root,plan.declare(source,contract),source)
                case=root/'0'/'baseline'; case.mkdir(parents=True)
                trial.signed(case/'ready.json',{'uri':'wss://ws-subscriptions-clob.polymarket.com/ws/market'},'ready_sha256')
                with patch.object(trial,'ObservedSocket') as adapter:
                    with self.assertRaises(ContractError): trial.consume(root,0,'baseline')
                    adapter.assert_not_called()


if __name__=='__main__': unittest.main()
