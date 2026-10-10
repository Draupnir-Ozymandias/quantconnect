"""Explicit finite Linux smoke; no sockets, collector mutation or cohort execution."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import platform
import time

from execution_truth.contracts import ContractError, payload_hash
from infra.stream.receive_loop_validity import cpu_interval, counter_interval
from infra.stream.receive_loop_validity_probe import CounterReader, PacingProbe, cpu_stamp


def smoke(*, execute=False):
    if execute is not True or platform.system() != 'Linux':
        raise ContractError('explicit Linux smoke execution required')
    reader = CounterReader(os.getpid(), capacity=2)
    first = reader.read()
    if first.sample is None:
        raise ContractError('native cgroup read unavailable: '+str(first.error))
    cpu_first = cpu_stamp()
    probe = PacingProbe(3)
    sent = []
    for index in range(3):
        returned = probe.step(time.monotonic()+.001,
                              lambda begin: ('smoke', begin),
                              lambda raw: sent.append(raw))
        if returned is not None:
            raise ContractError('native send return changed')
    cpu_last = cpu_stamp()
    last = reader.read()
    if last.sample is None:
        raise ContractError('second native cgroup read unavailable: '+str(last.error))
    pacing = probe.finish()
    counters = reader.finish()
    cpu = cpu_interval(cpu_first, cpu_last)
    delta = counter_interval(first.sample, last.sample)
    if (not pacing['complete'] or not counters['complete'] or len(sent) != 3
            or cpu['status'] != 'observed' or delta['status'] == 'unavailable'
            or delta['deltas']['usage_usec'] is None):
        raise ContractError('native smoke identity/clock/completion failed')
    root = Path(__file__).resolve().parents[2]
    files = ('infra/stream/receive_loop_validity.py',
             'infra/stream/receive_loop_validity_probe.py',
             'infra/stream/receive_loop_validity_smoke.py')
    report = dict(schema_version='qcrl.receive_loop_validity_linux_smoke.v1',
                  python=platform.python_version(), machine=platform.machine(),
                  source_bytes={f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in files},
                  native_counter_samples=[asdict(first.sample), asdict(last.sample)],
                  cpu_interval=cpu, counter_interval=delta,
                  producer_partitions=[s.partition() for s in pacing['samples']],
                  smoke_passed=True, probe_cost_verified=False,
                  overhead_acceptance_established=False, cohort_executed=False,
                  collector_mutation_performed=False, orders_authorized=False)
    report['report_sha256'] = payload_hash(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(smoke(execute=args.execute), indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
