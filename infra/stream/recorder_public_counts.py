"""Fixed public-study policy and exact interval counts; no network or launcher."""
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
import math

from execution_truth.contracts import ContractError, payload_hash

ORIGINAL_PLAN = dict(schema_version='qcrl.public_feed_interval_counts.study.v1',
    case='btc5m-20261017T160000Z-local-counts-01',
    event_start='2026-10-17T16:00:00Z', event_end='2026-10-17T16:05:00Z',
    discovery='2026-10-17T15:55:00Z', freeze_cutoff='2026-10-17T15:59:00Z',
    arm='2026-10-17T16:00:40Z', nominal_epoch='2026-10-17T16:01:00Z',
    seconds=60, tail_seconds=5, acquisition_seconds=90, frame_cap=60000,
    readiness_lead_seconds=1, connection_attempts=1, reconnects=0,
    open_timeout_seconds=10, close_timeout_seconds=5,
    disk_start_bytes=2*1024**3, disk_reserve_bytes=1024**3,
    spool_cap_bytes=1024**3, auxiliary_cap_bytes=64*1024**2,
    completion_cap_bytes=32*1024**2,
    unit=dict(CPUQuota='75%', MemoryMax='512M', TasksMax='32', RuntimeMaxSec='240'),
    rss_thread_cpu=False, original_application_verdict='fail',
    aggregate_acceptance_defined=False, venue_completeness_proven=False,
    orders_authorized=False)

# A prospective successor, never a repair/relabel of the 16:00 target's not-run.
SUCCESSOR_V2_PLAN=deepcopy(ORIGINAL_PLAN)
SUCCESSOR_V2_PLAN.update(schema_version='qcrl.public_feed_interval_counts.study.v2',
    parent_plan_sha256=payload_hash(ORIGINAL_PLAN),
    case='btc5m-20261017T170000Z-local-counts-02',
    event_start='2026-10-17T17:00:00Z',event_end='2026-10-17T17:05:00Z',
    discovery='2026-10-17T16:55:00Z',freeze_cutoff='2026-10-17T16:59:00Z',
    arm='2026-10-17T17:00:40Z',nominal_epoch='2026-10-17T17:01:00Z',
    tls_policy='qcrl.verified_ca_descriptor_snapshot.v1')

# New authorization and fixed window; both expired declarations remain intact.
SUCCESSOR_V3_PLAN=deepcopy(SUCCESSOR_V2_PLAN)
SUCCESSOR_V3_PLAN.update(schema_version='qcrl.public_feed_interval_counts.study.v3',
    parent_plan_sha256=payload_hash(SUCCESSOR_V2_PLAN),
    case='btc5m-20261017T183000Z-local-counts-03',
    event_start='2026-10-17T18:30:00Z',event_end='2026-10-17T18:35:00Z',
    discovery='2026-10-17T18:25:00Z',freeze_cutoff='2026-10-17T18:29:00Z',
    arm='2026-10-17T18:30:40Z',nominal_epoch='2026-10-17T18:31:00Z')


# A new prospective public target uses the independently validated stop owner.
# Prior plans and their evidence remain immutable; all measurement limits persist.
SUCCESSOR_V4_PLAN=deepcopy(SUCCESSOR_V3_PLAN)
SUCCESSOR_V4_PLAN.update(schema_version='qcrl.public_feed_interval_counts.study.v4',
    parent_plan_sha256=payload_hash(SUCCESSOR_V3_PLAN),
    case='btc5m-20261019T160000Z-local-counts-04',
    event_start='2026-10-19T16:00:00Z',event_end='2026-10-19T16:05:00Z',
    discovery='2026-10-19T15:55:00Z',freeze_cutoff='2026-10-19T15:59:00Z',
    arm='2026-10-19T16:00:40Z',nominal_epoch='2026-10-19T16:01:00Z',
    stop_policy_sha256='dde0e19b05f04cc802432520d1dc6e30a3294eaaeb2e21ddb8d2f026adc8e9b3')


PLAN=deepcopy(SUCCESSOR_V4_PLAN)
PLAN.update(schema_version='qcrl.public_feed_interval_counts.study.v5',
    parent_plan_sha256=payload_hash(SUCCESSOR_V4_PLAN),
    case='btc5m-20261020T160000Z-local-counts-05',
    event_start='2026-10-20T16:00:00Z',event_end='2026-10-20T16:05:00Z',
    discovery='2026-10-20T15:55:00Z',freeze_cutoff='2026-10-20T15:59:00Z',
    arm='2026-10-20T16:00:40Z',nominal_epoch='2026-10-20T16:01:00Z',
    notice_policy_sha256='6dec039e13620846ed83b0850d0d36a83325cb5afbf87372742359b7cd70bceb',
    publication_policy_sha256='9b07b4ecfa5c2c9a186e8f6a9bcb2e25fc2a890aeac98a65579de83a7d5a0f0e')


def require(ok, message):
    if not ok:
        raise ContractError(message)


def number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            'finite nonnegative clock required')
    return Fraction(value)


def utc(value):
    require(isinstance(value, str) and value.endswith('Z'), 'UTC Z timestamp required')
    result = datetime.fromisoformat(value[:-1]+'+00:00')
    require(result.tzinfo == timezone.utc, 'UTC timestamp required')
    return result


def epoch_ns(before, observed_utc, after):
    """After-endpoint reference, exact represented inputs, one upward rounding."""
    a, b = number(before), number(after)
    require(a <= b, 'anchor clock regressed')
    delta = utc(PLAN['nominal_epoch'])-utc(observed_utc)
    micros = (delta.days*86400+delta.seconds)*1000000+delta.microseconds
    reference = (b+Fraction(micros, 1000000))*1000000000
    result = -(-reference.numerator//reference.denominator)
    require(Fraction(result, 1000000000) > b, 'study epoch is not future')
    return result


def bins(frames, epoch, *, censored_from=None, coverage_complete=False):
    """Count known archived occurrences; missing acquisition coverage stays unknown.

    Caller must independently establish archive/clock-domain linkage. This is
    descriptive arithmetic, never a combined application acceptance evaluator.
    """
    require(type(epoch) is int and epoch >= 0, 'integer epoch nanoseconds required')
    require(isinstance(frames, list) and len(frames) <= PLAN['frame_cap'],
            'bounded archived occurrence list required')
    require(type(coverage_complete) is bool, 'explicit coverage state required')
    origin = Fraction(epoch, 1000000000)
    censor = number(censored_from) if censored_from is not None else None
    rows = [dict(slot=k, lower=0, upper_linked=0, possible_unplaced=0,
                 original_utc_wide_possible=0,
                 coverage=('censored' if censor is not None and origin+k+1 > censor
                           else 'recorded' if coverage_complete else 'unverified'))
            for k in range(PLAN['seconds'])]
    ambiguity, unplaced, outside, wide = [], [], {}, []
    for sequence, frame in enumerate(frames):
        require(isinstance(frame, dict) and frame.get('sequence') == sequence
                and type(frame.get('sequence')) is int, 'full ordered occurrence population required')
        try:
            before, after = (frame['returned'][key] for key in ('before', 'after'))
            lo, hi = number(before)-origin, number(after)-origin
            require(lo <= hi, 'observation clock regressed')
        except (ContractError, KeyError, TypeError, ValueError):
            unplaced.append(sequence)
            continue
        a, b = lo.numerator//lo.denominator, hi.numerator//hi.denominator
        # Bound work without truncating a multi-second candidate interval.
        candidates = list(range(max(0, a), min(59, b)+1))
        is_wide = after-before > .001  # Same literal float rule as original gate.
        if is_wide:
            wide.append(sequence)
        for k in candidates:
            rows[k]['upper_linked'] += 1
            rows[k]['original_utc_wide_possible'] += is_wide
            if a == b:
                rows[k]['lower'] += 1
        if a != b:
            ambiguity.append(dict(sequence=sequence, first_bin=a, last_bin=b,
                                  possible_primary_bins=candidates))
        if a < 0 or b >= 60:
            # Store ranges, not an unbounded expansion outside the primary window.
            outside[str(sequence)] = dict(first_bin=a, last_bin=b)
    for row in rows:
        row['possible_unplaced'] = len(unplaced)
        row['upper_archived'] = row['upper_linked']+len(unplaced)
        if unplaced and row['coverage'] == 'recorded':
            row['coverage'] = 'unplaced_clock'
        row['feed_activity_upper'] = None
    return dict(schema_version='qcrl.public_feed_interval_counts.description.v1',
        original_application_verdict='fail', plan_sha256=payload_hash(PLAN),
        historical_application_experiments=['Cohort02','RssCpu01'],
        population=len(frames), rows=rows, ambiguous=ambiguity,
        unplaced=unplaced, outside_primary=outside,
        original_utc_wide_sequences=wide, venue_completeness_proven=False,
        orders_authorized=False)


def plan():
    return deepcopy(PLAN)
