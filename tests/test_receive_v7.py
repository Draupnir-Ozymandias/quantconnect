from datetime import timedelta
import json
from pathlib import Path
import tempfile
import time
import unittest

from execution_truth.binance_source import _time
from execution_truth.contracts import payload_hash
from execution_truth.market_stream import collect_market_stream,stream_plan,verify_stream_log
from execution_truth.receive_path import policy_for,sample_clock
from execution_truth.rolling_stream import persist
from execution_truth.stream_receive_analysis import analyze_capture
from tests.test_reader_comparison import corpus


class ReceiveV7Tests(unittest.TestCase):
    def test_recorder_archive_recovery_and_versioned_analysis(self):
        c=corpus()
        declaration={'schema_version':'qcrl.synthetic_receive_burst_schedule.v1',
                     'network_access':False,'orders_authorized':False,'policy_sha256':payload_hash(policy_for('v3'))}
        declaration['plan_sha256']=payload_hash(declaration)
        spec=stream_plan(c['bundle'],max_seconds=15,max_frames=66,segmented=True,profiling=True,
            resilient=True,receive_path=True,freshness_telemetry=True,receive_policy='v3',
            source_plan_sha256=declaration['plan_sha256'])
        self.assertEqual(spec['schema_version'],'qcrl.public_market_stream_spec.v7')
        base=_time(spec['event_start_at_utc']); origin=time.monotonic()
        def clock(): return base+timedelta(seconds=time.monotonic()-origin)
        raw=json.loads(c['book_template'])
        for e in raw: e['timestamp']=str(int(base.timestamp()*1000))
        raw=json.dumps(raw)
        def connector(t,number,**kwargs):
            class Socket:
                reset=t.begin_connection(number)
                n=0
                def send(self,message): pass
                def recv(self,timeout):
                    if self.n==0:
                        for _ in range(65):
                            t.observe_frame(number,1,True,raw.encode(),sample_clock(clock,time.monotonic,t.domain))
                    if self.n==65:
                        t.observe_frame(number,1,True,raw.encode(),sample_clock(clock,time.monotonic,t.domain))
                    self.n+=1
                    return raw,t.deliver(number,raw,sample_clock(clock,time.monotonic,t.domain))
                def close(self): pass
            return Socket()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            summary=collect_market_stream(c['bundle'],spec,root/'stream',connector=connector,
                                          clock=clock,clock_domain='synthetic.v7')
            self.assertEqual(summary['status'],'frame_limit')
            verified=verify_stream_log(root/'stream')
            recovery=verified['receive_recovery_verification']['connections']['1']
            self.assertEqual(recovery['recovery_generations'],1)
            self.assertEqual(recovery['known'],65)
            self.assertEqual(recovery['unknown'],1)
            persist(root/'declaration.json',declaration)
            persist(root/'market-1.json',c['bundle'])
            report={'verification':verified}; report['report_sha256']=payload_hash(report)
            persist(root/'report.json',report)
            analysis=analyze_capture(root)
            self.assertEqual(analysis['schema_version'],'qcrl.receive_phase_analysis.v3')
            self.assertEqual(analysis['phases']['recovered']['available'],1)
            self.assertEqual(analysis['verified_recovery_generations_by_connection'],{'1':1})
            self.assertEqual(analysis['total']['unknown'],1)
