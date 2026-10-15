"""Prospective readiness allowance: actual adapter/auditor paths and faults."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from execution_truth.contracts import ContractError, payload_hash
from infra.stream import recorder_persistence_cohort as cohort
from infra.stream import recorder_persistence_cohort_audit as audit
from infra.stream.recorder_wait_production import CommandError, Production
from tests.test_recorder_persistence_cohort import STAGE


def raw_properties(role='tests'):
    value=cohort.spec(STAGE,role,None if role=='tests' else 'steady-0')
    raw=dict(value['properties'],MemoryMax='1073741824' if role=='tests' else '536870912',
        CPUQuotaPerSecUSec='750ms',RuntimeMaxUSec='4min',Id=value['unit']+'.service',
        ActiveState='active',SubState='exited',Result='success',ExecMainStatus='0',ExecMainCode='1',
        ExecMainPID='10',ExecMainStartTimestampMonotonic='1000000',ExecMainExitTimestampMonotonic='2000000')
    args=[cohort.PYTHON,'-m','unittest','discover','-s','tests','-q'] if role=='tests' else [cohort.PYTHON,
        '-m','infra.stream.recorder_persistence_cohort','--root',STAGE+'/evidence/steady-0',
        '--worker',role,'--case','steady-0','--execute']
    raw['ExecStart']='{ argv[]='+' '.join(args)+' ; }'
    return value,raw


class ReadinessMemoryTests(unittest.TestCase):
    def test_pinned_envelope_and_unchanged_measurement_plan(self):
        self.assertEqual(payload_hash(cohort.READINESS_ENVELOPE),'3da708ded82b8ca4f5dcb868401130e8bd9e9b447c19542f7d1842ac2572ce09')
        self.assertEqual(payload_hash(cohort.PLAN),'eca23ef82ac9ca72a816a9580483a35657df364ea081f7772f8e5c0477b1fa6b')
        self.assertEqual(cohort.declaration()['readiness_envelope'],cohort.READINESS_ENVELOPE)
        for role in ('producer','consumer'):
            self.assertEqual(cohort.spec(STAGE,role,'steady-0')['properties']['MemoryMax'],'512M')

    def test_effective_readiness_exact_memory_cpu_time_and_hardening(self):
        value,raw=raw_properties();original=deepcopy(raw)
        self.assertEqual(cohort.verify_cohort_properties(raw,value),value['properties'])
        self.assertEqual(raw,original)
        for key,bad in [('MemoryMax','536870912'),('MemoryMax','1073741825'),('MemoryMax','max'),
            ('CPUQuotaPerSecUSec','1s'),('RuntimeMaxUSec','5min'),('TasksMax','33'),('User','root'),
            ('PrivateTmp','no'),('ReadWritePaths','/'),('IPAddressAllow','0.0.0.0/0')]:
            with self.subTest(key=key,bad=bad),self.assertRaises(ContractError):
                cohort.verify_cohort_properties(dict(raw,**{key:bad}),value)

    def test_measurement_units_reject_readiness_allowance(self):
        for role in ('producer','consumer'):
            value,raw=raw_properties(role)
            self.assertEqual(cohort.verify_cohort_properties(raw,value),value['properties'])
            with self.assertRaises(ContractError):cohort.verify_cohort_properties(dict(raw,MemoryMax='1073741824'),value)

    def test_actual_start_specs_only_readiness_changes(self):
        ops=object.__new__(cohort.CohortProduction);ops.root=Path(STAGE);ops.evidence=ops.root/'evidence';ops.specs={};ops.case_name=None
        with patch.object(cohort,'command',return_value='') as command:
            ops.start(cohort.spec(STAGE,'tests'))
            ops.case_name='steady-0';ops.start(cohort.spec(STAGE,'consumer','steady-0'))
        self.assertIn('--property=MemoryMax=1G',command.call_args_list[0].args[0])
        self.assertIn('--property=MemoryMax=512M',command.call_args_list[1].args[0])
        self.assertEqual(command.call_args_list[0].args[0][-6:],['-m','unittest','discover','-s','tests','-q'])

    def capture(self,d,raw,fault=None):
        ops=object.__new__(cohort.CohortProduction);ops.evidence=Path(d)
        value,_=raw_properties();unit=value['unit'];ops.specs={unit:value}
        text='\n'.join(k+'='+v for k,v in raw.items())
        props=CommandError('properties fault',b'partial actual properties') if fault=='properties' else (text,raw)
        journal=CommandError('journal cap',b'partial journal') if fault=='journal' else 'retained journal'
        with patch.object(ops,'properties',side_effect=props if isinstance(props,Exception) else None,
                return_value=None if isinstance(props,Exception) else props),patch.object(cohort,'command',
                side_effect=journal if isinstance(journal,Exception) else None,return_value=journal):
            return ops.capture(unit,max_journal_bytes=65536)

    def test_actual_readiness_capture_preserves_true_bytes_and_oom(self):
        value,raw=raw_properties()
        with tempfile.TemporaryDirectory() as d:
            result=self.capture(d,dict(raw,Result='oom-kill',ExecMainStatus='9',SubState='failed'))
            self.assertEqual((result['result'],result['exec_status']),('oom-kill',9))
            self.assertIn('MemoryMax=1073741824',(Path(d)/(value['unit']+'-properties.txt')).read_text())
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.capture(d,raw)['observed_properties']['MemoryMax'],'1G')

    def test_capture_retains_partial_output_and_rejects_wrong_limit(self):
        value,raw=raw_properties()
        for fault in ('properties','journal','wrong_limit'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as d:
                with self.assertRaises(ContractError):self.capture(d,dict(raw,MemoryMax='536870912') if fault=='wrong_limit' else raw,fault)
                suffix='-properties.partial' if fault=='properties' else '-journal.txt'
                self.assertTrue((Path(d)/(value['unit']+suffix)).is_file())
                if fault!='wrong_limit':self.assertTrue((Path(d)/(value['unit']+'-capture-error.json')).is_file())

    def test_measurement_capture_delegates_to_frozen_adapter(self):
        ops=object.__new__(cohort.CohortProduction);value,_=raw_properties('consumer');ops.specs={value['unit']:value}
        with patch.object(Production,'capture',return_value={'original':True}) as capture:
            self.assertEqual(ops.capture(value['unit'],max_journal_bytes=65536),{'original':True})
            capture.assert_called_once_with(value['unit'],max_journal_bytes=65536)

    def test_independent_auditor_accepts_exact_readiness_only(self):
        value,raw=raw_properties()
        self.assertEqual(audit.verify_unit(raw,value,STAGE+'/source')['pid'],10)
        for key,bad in [('MemoryMax','536870912'),('Result','oom-kill'),('ExecMainStatus','9'),
            ('ExecMainExitTimestampMonotonic','241000001'),('ExecStart','{ argv[]=wrong ; }')]:
            with self.subTest(key=key),self.assertRaises(ContractError):
                audit.verify_unit(dict(raw,**{key:bad}),value,STAGE+'/source')
