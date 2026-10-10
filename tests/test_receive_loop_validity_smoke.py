import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity_smoke import smoke


class SmokeBarrierTests(unittest.TestCase):
    def test_explicit_execution_required_before_reader(self):
        with patch('infra.stream.receive_loop_validity_smoke.CounterReader') as reader:
            with self.assertRaises(ContractError): smoke()
            reader.assert_not_called()

    def test_nonlinux_refused_before_reader(self):
        with patch('infra.stream.receive_loop_validity_smoke.platform.system', return_value='Darwin'), \
             patch('infra.stream.receive_loop_validity_smoke.CounterReader') as reader:
            with self.assertRaises(ContractError): smoke(execute=True)
            reader.assert_not_called()


if __name__ == '__main__': unittest.main()
