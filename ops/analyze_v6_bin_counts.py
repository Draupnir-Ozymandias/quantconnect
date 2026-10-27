"""Retrospective arithmetic over one hash-bound v6 CSV; no acquisition/API calls.

Run from any directory with the repository Python; writes JSON to stdout only.
This does not regenerate a historical report under successor recorder code.
"""
import csv
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import statistics


INPUT = Path(__file__).resolve().parents[1]/'docs/PUBLIC_FEED_COUNTS_V6_20261021.csv'
INPUT_SHA256 = 'b5712ba918794474132984ba5f96d9c7d69da9b0bf654285fb1eb93dd157860b'


def summarize():
    data = INPUT.read_bytes()
    if hashlib.sha256(data).hexdigest() != INPUT_SHA256:
        raise ValueError('v6 CSV differs from the retained input')
    rows = list(csv.DictReader(io.StringIO(data.decode('utf-8'))))
    assert [int(r['slot']) for r in rows] == list(range(60))
    whole, boundary = [], []
    for r in rows:
        assert r['coverage'] == 'unverified' and r['feed_activity_upper'] == 'null'
        assert int(r['possible_unplaced']) == 0
        assert r['lower'] == r['upper_archived'] == r['upper_linked']
        assert r['eligible_lower'] == r['eligible_upper_archived']
        if (r['acquisition'], r['book_eligibility']) == ('observed_local_interval', 'eligible_local_interval'):
            whole.append(r)
        else:
            boundary.append(r)
    assert [int(r['slot']) for r in whole] == list(range(24)) + list(range(28, 53))
    assert [int(r['slot']) for r in boundary] == [24, 25, 26, 27, 53, 54, 55, 56, 57, 58, 59]
    assert all(r['lower'] == r['eligible_lower'] for r in whole)
    counts = [int(r['lower']) for r in whole]
    ordered = sorted(counts)
    n, total = len(counts), sum(counts)
    # Nearest-rank percentile ceil(p*n), never interpolated.
    percentile = lambda p: ordered[(p*n+99)//100-1]
    ranking = sorted(whole, key=lambda r: (-int(r['lower']), int(r['slot'])))
    bottom = sorted(whole, key=lambda r: (int(r['lower']), int(r['slot'])))
    concentration = []
    for k in (1, 5, 10):
        top_sum = sum(int(r['lower']) for r in ranking[:k])
        bottom_sum = sum(int(r['lower']) for r in bottom[:k])
        concentration.append(dict(bins=k, top_slots=[int(r['slot']) for r in ranking[:k]],
            top_texts=top_sum, top_share=top_sum/total,
            bottom_slots=[int(r['slot']) for r in bottom[:k]],
            bottom_texts=bottom_sum, bottom_share=bottom_sum/total, equal_share=k/n))
    gini = Fraction(sum((2*i-n-1)*v for i, v in enumerate(ordered, 1)), n*total)
    blocks = []
    for lo, hi in ((0, 24), (28, 53)):
        block = [int(r['lower']) for r in whole if lo <= int(r['slot']) < hi]
        blocks.append(dict(first_slot=lo, last_slot=hi-1, bins=len(block), texts=sum(block),
                           mean=statistics.mean(block), share=sum(block)/total))
    return dict(schema_version='qcrl.v6.retrospective_bin_unevenness.v1',
        recording='btc5m-20261021T160000Z-local-counts-06', input_sha256=INPUT_SHA256,
        original_application_verdict='fail', recording_disposition='partial_or_unresolved',
        bin_count=n, raw_texts=total, eligible_texts=sum(int(r['eligible_lower']) for r in whole),
        primary_raw=sum(int(r['lower']) for r in rows),
        primary_eligible=sum(int(r['eligible_lower']) for r in rows),
        distribution=dict(minimum=min(counts), maximum=max(counts), mean=statistics.mean(counts),
            population_sd=statistics.pstdev(counts), cv=statistics.pstdev(counts)/statistics.mean(counts),
            nearest_rank_percentiles={str(p): percentile(p) for p in (10, 25, 50, 75, 90, 95, 99)},
            gini=float(gini), gini_exact=str(gini),
            count_ranges=[dict(lower=lo, upper_exclusive=hi, bins=sum(lo <= v < hi for v in counts))
                          for lo, hi in ((0, 500), (500, 600), (600, 700), (700, 800), (800, 900), (900, 1000))]),
        concentration=concentration, blocks=blocks,
        wide_utc_slots=[int(r['slot']) for r in whole if int(r['original_utc_wide_possible'])],
        boundary=[dict(slot=int(r['slot']), raw=int(r['lower']), eligible=int(r['eligible_lower']),
                       acquisition=r['acquisition'], book_eligibility=r['book_eligibility'],
                       silence=r['silence'], coverage=r['coverage'], feed_activity_upper=None)
                  for r in boundary])


if __name__ == '__main__':
    print(json.dumps(summarize(), indent=2, sort_keys=True, allow_nan=False))
