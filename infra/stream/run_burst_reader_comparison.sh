#!/usr/bin/env bash
# One finite declared localhost cohort. No public collectors are changed.
set -euo pipefail
test "$(id -u)" = 0
test "$#" = 1
run_root=$1
case "$run_root" in /var/lib/qcrl-stream/reader-burst-*) ;; *) exit 2 ;; esac
test ! -e "$run_root"
test "$(systemctl is-active qcrl-stream-pilot.service || true)" = inactive
test "$(df --output=avail -B1 /var/lib/qcrl-stream | tail -1)" -gt 4294967296
source_root=/opt/qcrl-stream
python=/opt/qcrl-stream/venv/bin/python
test -x "$python"
test -z "$(git -c safe.directory="$source_root" -C "$source_root" status --porcelain)"
install -d -o qcrl -g qcrl -m 750 "$run_root"
corpus=/var/lib/qcrl-stream/reader-comparison-linux-20261007-vDV2YH/input-corpus.json
sudo -u qcrl "$python" "$source_root/infra/stream/burst_reader_comparison.py" declare --root "$run_root" --corpus "$corpus"
git -c safe.directory="$source_root" -C "$source_root" rev-parse HEAD > "$run_root/source-commit.txt"
sha256sum /etc/qcrl-stream.env > "$run_root/collector-environment-before.sha256"
systemctl show qcrl-collector.timer qcrl-stream-pilot.service > "$run_root/collectors-before.properties"
common=(--property=User=qcrl --property=Group=qcrl --property=MemoryMax=512M --property=RemainAfterExit=yes
 --property=TasksMax=32 --property=RuntimeMaxSec=120 --property=NoNewPrivileges=yes
 --property=PrivateTmp=yes --property=ProtectSystem=strict --property=ProtectHome=yes
 --property="ReadWritePaths=$run_root" --working-directory="$source_root")
for round in 0 1 2; do
  case "$round" in 0) modes=(bare receive recorder);; 1) modes=(receive recorder bare);; 2) modes=(recorder bare receive);; esac
  for mode in "${modes[@]}"; do
    case_root="$run_root/$round-$mode"
    install -d -o qcrl -g qcrl -m 750 "$case_root"
    unit_tag="qcrl-burst-$(basename "$run_root")-$round-$mode"
    systemd-run --unit="$unit_tag-producer" "${common[@]}" --property=CPUQuota=100% \
      "$python" "$source_root/infra/stream/burst_reader_comparison.py" produce --root "$run_root" --case "$case_root" --mode "$mode"
    "$python" - "$case_root/ready.json" <<'PY'
import json, pathlib, sys, time
p=pathlib.Path(sys.argv[1]); deadline=time.monotonic()+15
while time.monotonic()<deadline:
    try:
        json.loads(p.read_text()); break
    except (FileNotFoundError,json.JSONDecodeError): time.sleep(.05)
else: raise SystemExit('producer did not become ready')
PY
    systemd-run --unit="$unit_tag-consumer" "${common[@]}" --property=CPUQuota=75% \
      "$python" "$source_root/infra/stream/burst_reader_comparison.py" consume --root "$run_root" --case "$case_root" --mode "$mode"
    for attempt in $(seq 1 240); do
      state=$(systemctl show "$unit_tag-consumer.service" -p SubState --value)
      test "$state" = exited && break
      test "$state" != failed
      sleep .5
    done
    for role in producer consumer; do
      for attempt in $(seq 1 100); do
        state=$(systemctl show "$unit_tag-$role.service" -p SubState --value)
        test "$state" = exited && break
        test "$state" != failed
        sleep .1
      done
      systemctl show "$unit_tag-$role.service" > "$case_root/$role-unit.properties"
      journalctl -u "$unit_tag-$role.service" --no-pager > "$case_root/$role-journal.txt"
      test "$(systemctl show "$unit_tag-$role.service" -p Result --value)" = success
      test "$(systemctl show "$unit_tag-$role.service" -p ExecMainStatus --value)" = 0
      test "$(systemctl show "$unit_tag-$role.service" -p SubState --value)" = exited
      systemctl stop "$unit_tag-$role.service"
    done
    sudo -u qcrl "$python" "$source_root/infra/stream/burst_reader_comparison.py" verify \
      --root "$run_root" --case "$case_root" --mode "$mode" --require-isolation > "$case_root/verification-output.json"
    printf 'VERIFIED %s\n' "$case_root"
  done
done
sha256sum /etc/qcrl-stream.env > "$run_root/collector-environment-after.sha256"
cmp "$run_root/collector-environment-before.sha256" "$run_root/collector-environment-after.sha256"
systemctl show qcrl-collector.timer qcrl-stream-pilot.service > "$run_root/collectors-after.properties"
printf 'FINITE_COHORT_COMPLETE %s\n' "$run_root"
