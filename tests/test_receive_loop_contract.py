from copy import deepcopy
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import receive_loop_contract as loop
from tests.test_receive_adapter import AVAILABLE


@unittest.skipUnless(AVAILABLE,'pinned optional WebSocket library required')
class ReceiveLoopContractTests(unittest.TestCase):
    def test_source_receipt_and_method_pins(self):
        receipt=loop.runtime_receipt()
        loop.validate_receipt(receipt)
        self.assertEqual(len(receipt['methods']),13)
        self.assertEqual(receipt['source_files'],loop.SOURCE_PINS)
        self.assertFalse(receipt['capture_performed'])

    def test_contract_roundtrip_and_no_capture_authority(self):
        obj=loop.declare('a'*64,loop.runtime_receipt())
        loop.validate_contract(obj)
        self.assertFalse(obj['policy']['capture_authorized_by_contract'])
        self.assertFalse(obj['policy']['public_rollout_authorized'])
        self.assertEqual(obj['policy']['library_low_water_frames'],4)

    def test_tampering_even_rehashed_policy_rejected(self):
        obj=loop.declare('a'*64,loop.runtime_receipt())
        obj['policy']['library_high_water_frames']=32
        obj.pop('contract_sha256'); obj['contract_sha256']=payload_hash(obj)
        with self.assertRaises(ContractError): loop.validate_contract(obj)

    def test_rehashed_method_receipt_rejected(self):
        obj=loop.runtime_receipt()
        next(iter(obj['methods'].values()))['source_sha256']='b'*64
        obj.pop('receipt_sha256'); obj['receipt_sha256']=payload_hash(obj)
        with self.assertRaises(ContractError): loop.validate_receipt(obj)

    def test_wrong_library_version_rejected(self):
        with patch.object(loop,'version',return_value='15.0.2'):
            with self.assertRaises(ContractError): loop.runtime_receipt()

    def test_wrong_file_source_rejected(self):
        altered=dict(loop.SOURCE_PINS); altered['websockets.sync.connection']='b'*64
        with patch.object(loop,'SOURCE_PINS',altered):
            with self.assertRaises(ContractError): loop.runtime_receipt()

    def test_bad_analysis_hash_and_cross_platform_receipt(self):
        receipt=loop.runtime_receipt()
        for value in ('short','A'*64,None):
            with self.assertRaises(ContractError): loop.declare(value,receipt)
        other=deepcopy(receipt); other['platform']='Linux'; other['python_version']='3.9.25'
        other.pop('receipt_sha256'); other['receipt_sha256']=payload_hash(other)
        loop.validate_receipt(other)


if __name__ == '__main__': unittest.main()
