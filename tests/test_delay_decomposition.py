from copy import deepcopy
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import delay_decomposition as delay
from tests.test_receive_recovery import tracker
from tests.test_receive_path import stamp


def record(callback=2, delivery=5):
    t = tracker(); t.observe_frame(1,1,True,b'same',stamp(callback))
    return t.deliver(1,'same',stamp(delivery))


class DelayDecompositionTests(unittest.TestCase):
    def test_paired_bracket_closure(self):
        r = record(); r['receive_marker']['last_receive_observation']['monotonic_after'] = 2.001
        r['application_delivery']['monotonic_after'] = 5.002
        s = delay.split(1,r)
        self.assertAlmostEqual(s['pre_callback'][0]+s['post_callback'][0]+.001,s['total'][0])
        self.assertAlmostEqual(s['pre_callback'][1]+s['post_callback'][1]-.001,s['total'][1])
        self.assertEqual(s['dominance'],'post_callback')

    def test_unknown_and_ineligible_never_receive_components(self):
        r = record(); r['receive_marker'] = None
        self.assertEqual(set(delay.split(1,r)),{'status','total'})
        r = record(); r['last_observation_to_delivery']['timing_eligible'] = False
        self.assertEqual(delay.split(1,r)['status'],'ineligible')
        self.assertNotIn('post_callback',delay.split(1,r))

    def test_last_callback_boundary_not_first_fragment(self):
        r = record(callback=4); r['receive_marker']['first_receive_observation'] = stamp(2)
        r['receive_marker']['fragment_count'] = 2
        self.assertEqual(delay.split(1,r)['pre_callback'],[3,3])

    def test_bad_clock_domains_and_reverse_clocks_rejected(self):
        r = record()
        for value in (-1,float('nan'),True,6):
            with self.assertRaises(ContractError): delay.split(value,r)
        bad = deepcopy(r); bad['receive_marker']['last_receive_observation']['clock_domain']='other'
        with self.assertRaises(ContractError): delay.split(1,bad)

    def test_tail_keeps_unknown_denominator(self):
        rs = [record(delivery=4),record(delivery=10)]; rs[1]['receive_marker']=None
        obs = [{'begin':1,'deadline':1,'send_start':1,'send_end':1,'phase_rate':rate} for rate in (500,3000)]
        s = delay.summarize(obs,rs)
        self.assertEqual(s['all']['total_upper_tail']['counts']['unknown'],1)
        self.assertEqual(s['all']['total_upper_tail']['counts']['eligible'],0)
        self.assertEqual(s['all']['population']['counts']['deliveries'],2)

    def test_quantiles_not_added_and_midpoint_means_close(self):
        rs = [record(callback=2,delivery=11),record(callback=10,delivery=11)]
        obs = [{'begin':1,'deadline':1,'send_start':1,'send_end':1,'phase_rate':rate} for rate in (500,3000)]
        s = delay.summarize(obs,rs)['all']['population']
        m = s['paired_midpoint_means_seconds']
        self.assertEqual(m['pre_callback']+m['post_callback'],m['total'])
        v = s['matched_eligible']
        self.assertGreater(v['pre_callback']['upper']['p99_seconds']+v['post_callback']['upper']['p99_seconds'],
                           v['total']['upper']['p99_seconds'])

    def test_message_budget_and_missing_phase_fail_closed(self):
        with self.assertRaises(ContractError): delay.summarize([],[])
        with patch.dict(delay.POLICY,max_messages_per_case=0):
            with self.assertRaises(ContractError): delay.summarize([{}],[record()])
        with self.assertRaises(ContractError): delay.summarize([{'begin':1,'phase_rate':500}],[record()])

    def test_origin_tamper_traversal_and_unpinned_audit_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'evidence').mkdir()
            (root/'origin-inventory.sha256').write_text('a'*64+'  ./../escape\n')
            with self.assertRaises(ContractError): delay.verify_origin(root)
            (root/'evidence'/'item').write_text('different')
            (root/'origin-inventory.sha256').write_text('a'*64+'  ./item\n')
            with self.assertRaises(ContractError): delay.verify_origin(root)
            audit={'schema_version':'wrong','audit_sha256':None}
            audit['audit_sha256']=payload_hash({'schema_version':'wrong'})
            import json
            (root/'independent-audit.json').write_text(json.dumps(audit))
            with self.assertRaises(ContractError): delay.analyze_review(root,'b'*64)


if __name__ == '__main__': unittest.main()
