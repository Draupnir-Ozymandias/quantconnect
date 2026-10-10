from types import SimpleNamespace
import unittest
from unittest.mock import patch
from execution_truth.contracts import ContractError
from infra.stream import receive_loop_validity_resources as r


class ResourceTests(unittest.TestCase):
    def data(self):
        return dict(begin=0,end=3,cpu_seconds=.2,resource_samples=[
            dict(error=None,pid=10,before=.1,after=.2,rss_bytes=1024,method=r.METHOD['rss']),
            dict(error=None,pid=10,before=2,after=2.1,rss_bytes=2048,method=r.METHOD['rss'])])

    def test_native_units_and_error_not_zero(self):
        with patch.object(r.platform,'system',return_value='Linux'), \
             patch.object(r.resource,'getrusage',return_value=SimpleNamespace(ru_maxrss=12)):
            self.assertEqual(r.sample()['rss_bytes'],12288)
        with patch.object(r.platform,'system',return_value='Darwin'):
            self.assertEqual(r.sample()['error'],'unsupported_platform')

    def test_summary_labels_self_report_not_verified(self):
        out=r.summarize(self.data(),{'pid':10})
        self.assertEqual(out['rss_max_bytes'],2048)
        self.assertFalse(out['resource_verified'])

    def test_missing_one_sample_is_unknown_not_partial_peak(self):
        d=self.data();d['resource_samples'][1]={'error':'OSError','pid':10}
        self.assertIsNone(r.summarize(d,{'pid':10})['rss_max_bytes'])

    def test_pid_window_negative_cpu_and_method_refused(self):
        for change in ('pid','window','cpu','method'):
            d=self.data()
            if change=='pid':d['resource_samples'][0]['pid']=11
            elif change=='window':d['resource_samples'][0]['before']=-1
            elif change=='cpu':d['cpu_seconds']=-1
            else:d['resource_samples'][0]['method']='current_rss'
            with self.assertRaises(ContractError):r.summarize(d,{'pid':10})
