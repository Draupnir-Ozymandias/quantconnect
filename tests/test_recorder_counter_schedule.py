import unittest
from execution_truth.contracts import ContractError
from infra.stream.recorder_counter_schedule import scheduled_window
from tests.test_recorder_counter_prototype import make


class Clock:
    def __init__(self, value=0, shift=0): self.value,self.shift=value,shift
    def now(self): return self.value
    def pause(self, seconds): self.value += seconds+self.shift


class Probe:
    def __init__(self,clock,slow=False,fail=False,reset=False):
        self.clock,self.slow,self.fail,self.reset=clock,slow,fail,reset
        self.calls=0
    def sample(self):
        self.calls+=1
        if self.fail and self.calls==1: raise OSError('injected no retry')
        value,_=make(self.clock.value,50 if self.reset and self.calls==2 else self.calls*100,
                     read_cost=.006 if self.slow else .0001)
        self.clock.value=value['total_end']
        return value


class ScheduleTests(unittest.TestCase):
    def run_case(self,**kwargs):
        clock=Clock(kwargs.pop('at',0),kwargs.pop('shift',0))
        probe=Probe(clock,**kwargs)
        result=scheduled_window(probe,1,0,execute=True,clock=clock.now,pause=clock.pause)
        return result,probe

    def test_fixed_targets_one_attempt_enclosing_boundary(self):
        result,probe=self.run_case()
        self.assertEqual(probe.calls,2)
        self.assertEqual([r['target'] for r in result['rows']],[.95,61])
        self.assertTrue(result['enclosure_verified'])
        self.assertFalse(result['acceptance_demonstrated'])
        self.assertFalse(result['orders_authorized'])

    def test_early_and_late_wake_no_read_no_catch_up(self):
        for shift in (-.001,.1):
            result,probe=self.run_case(shift=shift)
            self.assertEqual(probe.calls,0)
            self.assertFalse(result['enclosure_verified'])
            self.assertEqual([r['target'] for r in result['rows']],[.95,61])

    def test_already_missed_pre_slot_retains_post_only(self):
        result,probe=self.run_case(at=2)
        self.assertEqual(probe.calls,1)
        self.assertFalse(result['rows'][0]['attempted'])
        self.assertEqual(result['rows'][0]['error'],'endpoint_deadline_missed')
        self.assertEqual(result['error'],'required_endpoint_unknown')

    def test_readiness_missed_refuses_both_without_sleep(self):
        clock=Clock(1)
        probe=Probe(clock)
        result=scheduled_window(probe,1,.99,execute=True,clock=clock.now,pause=clock.pause)
        self.assertEqual(probe.calls,0)
        self.assertEqual(clock.value,1)
        self.assertFalse(result['enclosure_verified'])

    def test_probe_failure_no_retry_preserves_successful_post(self):
        result,probe=self.run_case(fail=True)
        self.assertEqual(probe.calls,2)
        self.assertIn('OSError',result['rows'][0]['error'])
        self.assertEqual(result['rows'][1]['status'],'observed')
        self.assertFalse(result['enclosure_verified'])

    def test_pre_read_crossing_boundary_retained_not_retimed(self):
        result,probe=self.run_case(shift=.049)
        self.assertEqual(probe.calls,2)
        self.assertIsNotNone(result['rows'][0]['endpoint'])
        self.assertGreater(result['rows'][0]['endpoint']['after'],1)
        self.assertEqual(result['rows'][0]['error'],'pre_counter_did_not_finish_before_boundary')
        self.assertFalse(result['enclosure_verified'])

    def test_regression_between_endpoint_attempts_refused(self):
        clock=Clock()
        class Regressing(Probe):
            def sample(self):
                value=super().sample()
                self.clock.value=.1
                return value
        probe=Regressing(clock)
        result=scheduled_window(probe,1,0,execute=True,clock=clock.now,pause=clock.pause)
        self.assertEqual(probe.calls,1)
        self.assertEqual(result['rows'][1]['error'],'schedule_clock_regressed')
        self.assertFalse(result['enclosure_verified'])

    def test_slow_read_and_counter_reset_refused(self):
        for kwargs in ({'slow':True},{'reset':True}):
            result,probe=self.run_case(**kwargs)
            self.assertEqual(probe.calls,2)
            self.assertFalse(result['enclosure_verified'])
            self.assertIsNone(result['diagnostic'])

    def test_clock_and_execution_guards(self):
        clock=Clock()
        probe=Probe(clock)
        with self.assertRaises(ContractError): scheduled_window(probe,1,0)
        for boundary,ready in ((float('nan'),0),(1,float('inf')),(1,2),(0,0)):
            with self.assertRaises(ContractError):
                scheduled_window(probe,boundary,ready,execute=True,clock=clock.now,pause=clock.pause)
        self.assertEqual(probe.calls,0)


if __name__=='__main__': unittest.main()
