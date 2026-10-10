# Native pinned-reader faults and comparison — October 10

The prototype passed private native cgroup migration/deletion checks and showed
lower CPU cost in a finite reader-component comparison. **This is not producer
cost acceptance, deployment approval, or a replay of a rejected cohort.**

## Source and evidence

Comparison code freeze: `dcc434d210e4dd82d23cb539f40beab384180a1b`.
All 862 local regressions passed; 14 targeted Linux tests passed. Fresh stage:
`/var/lib/qcrl-stream/receive-loop-pinned-rsX39ZYB`.
Externally obtained originating inventory byte SHA-256:
`7cd667b5bc58cb16545c2237c8469d6699e19c3fa941f9e34a9f0412a98630cc`.
Original artifacts, source Git bundle, frozen declaration, driver and offline
receipts are retained under
`.qcrl/reviews/pinned-reader-comparison-20261010-RvRtnbq7/`.

Independent offline revalidation matched 11 exact artifact/script/result files
and six declaration source hashes, verified 600 live ordered samples and their
native identity/counter intervals, case order and timing arithmetic, and actual
unit command, security/quotas, PID/boot/cgroup binding and lifetime enclosure.
Origin bytes were checked before and after analysis. A first verifier completed
its checks and wrote its receipt, then hit a summary-print KeyError. The summary
was corrected and checks were rerun read-only into `offline-revalidation.json`;
the first receipt was retained. No native capture was replayed.

## Lifecycle faults

Only two fresh owned cgroups and one owned disposable child were used. After a
successful pinned read, the child was moved from the first private group to the
second. Kernel membership changed and the next read failed closed. A new reader
then pinned the second group; the child was moved back and that now-empty group
was deleted. The reader again rejected the stale target. Neither failure could
become a complete report. The child was reaped and both groups removed; a separate
read-only SSH check confirmed both group paths were absent. No existing cgroup,
collector process, quota or infrastructure setting was changed.

Real kernel PID reuse was not forced; prior native process-exit coverage and
fixture start-ID mismatch coverage do not establish that remaining case.

## Component cost

Three rotated original/pinned pairs each made 100 reads of the same explicit
live target. Total process CPU includes construction, first read, remaining reads,
common expected-identity checks and finish/cleanup. Samples were materialized and
interval-validated afterward. No cadence was tested: these were finite helper
batches, not the 30-second producer workload or a 100-ms scheduled observer.

| Round (zero-based) | Original total CPU | Pinned total CPU |
| --- | ---: | ---: |
| 0 | 29.465 ms | 19.092 ms |
| 1 | 30.125 ms | 19.039 ms |
| 2 | 29.118 ms | 19.980 ms |

Pinned total CPU was approximately 31–37% lower in these three comparisons.
Its cold acquisition cost was higher (0.80–0.89 ms versus 0.49–0.65 ms), and its
steady cost was lower (183–192 microseconds/read versus 288–298). These are
small source-bound component measurements on one host, not a randomized causal
estimate, a universal speedup, or proof of meeting the unchanged 5% combined-CPU
gate. The full probe also has worker-side CPU-stamp cost which this does not fix.

## Public state and next work

Public checkout/configuration/service states matched before and after; only the
owned diagnostic child, empty private groups and comparison unit were retired.
No trades, credentials, public collector restart or QuantConnect sync occurred.
Cadence, CPU coverage and rejected experiment thresholds remain unchanged.

Next: isolated observer integration with explicit reader-method/source receipts,
cleanup-before-acknowledgment tests and independent sideband linkage. Then declare
a distinct combined-cost experiment before any producer-cohort execution. Do not
substitute this component result for the full gate or silently reduce coverage.
