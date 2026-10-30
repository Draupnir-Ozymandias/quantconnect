"""Prospective BTC20 allocations; no I/O, retry, rate estimate or acceptance."""
from copy import deepcopy
from fractions import Fraction

from execution_truth.contracts import ContractError, payload_hash

POLICY = dict(schema_version='qcrl.btc20_phase_quotas.v1', seconds=20, tail_seconds=2,
    prewindow_seconds=5, frame_cap=60000,
    frames=dict(prewindow=8000, primary=50000, tail=2000),
    bytes=dict(prewindow=32*1024**2, primary=128*1024**2, tail=8*1024**2),
    record_cap_bytes=4*1024**2, terminal_bytes=32*1024**2,
    phase='return_before_endpoint_controls_append_clock',
    exhausted='stop_entire_acquisition_after_trigger_record_no_borrow_no_reset',
    bootstrap='charged_in_full_before_eligibility', venue_completeness_proven=False,
    original_60_second_cpu_window='unavailable_no_prorating')


class QuotaStop(ContractError):
    pass


class Allocations:
    def __init__(self, epoch_ns):
        self.epoch = Fraction(epoch_ns, 10**9)
        self.frames = {k: 0 for k in POLICY['frames']}
        self.bytes = {k: 0 for k in POLICY['bytes']}
        self.terminal = 0
        self.received = self.archived = 0
        self.stop = None
        self.unarchived = None
        self.terminal_first_ordinal = None

    def phase(self, before):
        delta = Fraction(before)-self.epoch
        return 'prewindow' if delta < 0 else 'primary' if delta < POLICY['seconds'] else 'tail'

    def receive(self, phase):
        self.received += 1
        self.frames[phase] += 1
        if self.frames[phase] >= POLICY['frames'][phase] and self.stop is None:
            self.stop = phase+'_frame_limit'

    def admit(self, phase, size):
        if type(size) is not int or not 0 < size <= POLICY['record_cap_bytes']:
            raise QuotaStop('encoded record exceeds four MiB')
        if phase == 'terminal' and self.terminal+size > POLICY['terminal_bytes']:
            raise QuotaStop('terminal byte allowance exhausted')

    def written(self, phase, size):
        if phase == 'terminal':
            self.terminal += size
        else:
            self.bytes[phase] += size
            if self.bytes[phase] >= POLICY['bytes'][phase] and self.stop is None:
                self.stop = phase+'_byte_limit'

    def snapshot(self):
        return dict(policy_sha256=payload_hash(POLICY), received_occurrences=self.received,
            archived_occurrences=self.archived, phase_frames=deepcopy(self.frames),
            unallocated_occurrences=self.received-sum(self.frames.values()),
            phase_encoded_bytes=deepcopy(self.bytes), terminal_encoded_bytes=self.terminal,
            terminal_first_ordinal=self.terminal_first_ordinal,
            stop_reason=self.stop, unarchived_occurrence=deepcopy(self.unarchived),
            counters_reset=False, original_60_second_cpu_window=None,
            venue_completeness_proven=False)


def verify_archive_allocations(result, completion, root):
    """After ordinary archive/completion verification, recompute actual allocation.

    A disclosed unarchived return cannot make incomplete completion linkage pass.
    Its metadata remains available separately when that earlier verifier fails.
    """
    import gzip
    import json
    from pathlib import Path
    receipt=result['phase_allocations']
    if (receipt['policy_sha256'] != payload_hash(POLICY) or receipt['counters_reset'] is not False
            or result['summary']['phase_quota_policy_sha256'] != payload_hash(POLICY)):
        raise ContractError('phase allocation policy/reset differs')
    meter=Allocations(result['epoch_ns'])
    first=receipt['terminal_first_ordinal']
    if type(first) is not int or first < 0 or first != result['summary']['allocation_terminal_first_ordinal']:
        raise ContractError('terminal allocation watermark differs')
    by_ordinal={f['ordinal']:f for f in completion['frames']}
    for descriptor in sorted(Path(root).glob('segment-*.json')):
        name=json.loads(descriptor.read_bytes())['file']
        with gzip.open(Path(root)/name,'rb') as handle:
            for line in handle:
                row=json.loads(line)
                # Verify temporal stopping, not just final totals: exhausting one
                # phase forbids further acquisition in every other phase too.
                # Only terminal records may follow the retained trigger record.
                if meter.stop is not None and row['ordinal'] < first:
                    raise ContractError('acquisition record follows phase quota exhaustion')
                phase=('terminal' if row['ordinal']>=first else meter.phase(
                    by_ordinal[row['ordinal']]['returned']['before'] if row['kind']=='frame'
                    else row['local_monotonic_seconds']))
                if row['kind']=='frame':
                    if phase=='terminal':raise ContractError('incoming frame charged to terminal reserve')
                    meter.receive(phase);meter.archived+=1
                meter.admit(phase,len(line));meter.written(phase,len(line))
    for key,want in (('phase_encoded_bytes',meter.bytes),('terminal_encoded_bytes',meter.terminal),
                     ('archived_occurrences',meter.archived),('phase_frames',meter.frames),
                     ('received_occurrences',meter.received),('unallocated_occurrences',0)):
        if receipt[key] != want:raise ContractError('archive allocation differs: '+key)
    if receipt['unarchived_occurrence'] is not None:
        raise ContractError('unarchived occurrence prevents complete population linkage')
    if receipt['stop_reason']!=meter.stop:raise ContractError('allocation stop reason differs')
    if any(meter.frames[k]>POLICY['frames'][k] or meter.bytes[k]>POLICY['bytes'][k]+POLICY['record_cap_bytes']
           for k in meter.frames):raise ContractError('phase allocation exceeded')
    if receipt['original_60_second_cpu_window'] is not None or receipt['venue_completeness_proven'] is not False:
        raise ContractError('unsupported allocation acceptance claim')
    return deepcopy(receipt)
