# Compact candidate finite Linux launcher

Separate module: `infra.stream.receive_loop_compact_launch`. It requires explicit
--execute, Linux root and a new canonical stage named
`/var/lib/qcrl-stream/receive-loop-compact-<alphanumeric>/`, containing a clean
source checkout and regular preregistration/input-corpus files. The stage is
distinct from reference evidence; existing claims, inventories, units or outputs
are refused, never adopted or replayed. The checkout must be owned/readable by
qcrl, including Git access without a global trust exception.

It snapshots the public checkout/configuration/service state and requires the
daily collector timer active and pilot/observer services inactive. It never
starts, stops or restores public collectors. Any drift is failure.

First run the full test suite in a private bounded qcrl transient unit. Only a
successful test unit permits staging workers. Then execute the preregistered
six alternating cases serially, with separate producer and consumer cgroups.
Producer CPU quota is 100%, consumer/tests 75%; fixed limits are 512 MiB, 32
tasks and 120 seconds. No core affinity, resource relaxation or public network
selection is added. Numeric localhost is checked before either adapter connects.

Unit properties and journals are captured before stopping only this launcher's
own qcrl-compact-prefixed transient units. Failures preserve partial evidence,
capture/cleanup errors, claim and manifest; no retry. Final inventory records
exact originating evidence bytes. It is not an origin/resource or performance
audit. Completion alone does not establish overhead acceptance.

This implementation is tested without running the real cohort. Before any
approved launch, freeze worker/launcher/auditor sources, retain source/input byte
anchors, stage a fresh qcrl-owned checkout, and independently validate the new
preregistration. The fixed interpreter is /opt/qcrl-stream/venv/bin/python.
