"""Common Linux measurements; no unit/resource acceptance from self-reports."""
import os
import platform
import resource
import time

from execution_truth.contracts import ContractError
from infra.stream.receive_loop_validity import number, ordered

METHOD = {'schema_version': 'qcrl.validity_resource_method.v1',
          'rss': 'two_samples_linux_getrusage_process_highwater_kib_times_1024',
          'rss_scope': 'process_lifetime_through_sample_not_current_or_window_peak',
          'cpu': 'process_time_delta_including_common_resource_samples',
          'combined_rss': 'sum_of_each_role_max_sample_no_shared_page_deduplication',
          'unit_and_origin_verification_required': True}


def sample():
    if platform.system() != 'Linux':
        return {'error': 'unsupported_platform', 'pid': os.getpid()}
    try:
        before = time.monotonic()
        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        after = time.monotonic()
        ordered(before, after)
        if type(value) is not int or value <= 0:
            raise ContractError('positive native RSS required')
        return dict(error=None, pid=os.getpid(), before=before, after=after,
                    rss_bytes=value*1024, method=METHOD['rss'])
    except Exception as exc:
        return {'error': type(exc).__name__, 'pid': os.getpid()}


def summarize(done, identity):
    cpu = done.get('cpu_seconds')
    if cpu is not None and number(cpu) < 0:
        raise ContractError('negative timed CPU')
    values = done.get('resource_samples')
    if not isinstance(values, list) or len(values) != 2:
        raise ContractError('two common resource samples required')
    rss = []
    for value in values:
        if value.get('pid') != identity['pid']:
            raise ContractError('resource sample PID differs')
        if value.get('error') is not None:
            continue
        ordered(value['before'], value['after'])
        if (value.get('method') != METHOD['rss'] or type(value.get('rss_bytes')) is not int
                or value['rss_bytes'] <= 0):
            raise ContractError('resource sample method/value differs')
        if not done['begin'] <= value['before'] <= value['after'] <= done['end']:
            raise ContractError('resource samples outside declared CPU window')
        rss.append(value['rss_bytes'])
    return dict(cpu_seconds=cpu, rss_max_bytes=max(rss) if len(rss) == 2 else None,
                rss_samples_observed=len(rss), resource_verified=False)
