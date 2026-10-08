#!/usr/bin/env bash
# Six finite localhost measurements. Audits occur offline after all measurements.
set -euo pipefail
test "$(id -u)" = 0
test "$#" = 1
stage_root=$1
case "$stage_root" in /var/lib/qcrl-stream/encoding-confirmation-*) ;; *) exit 2 ;; esac
test ! -L "$stage_root"
source_root="$stage_root/source"
test ! -L "$source_root"
test -z "$(git -c safe.directory="$source_root" -C "$source_root" status --porcelain)"
test "$(systemctl is-active qcrl-stream-pilot.service || true)" = inactive
test "$(df --output=avail -B1 /var/lib/qcrl-stream | tail -1)" -gt 4294967296
evidence="$stage_root/evidence"
test ! -e "$evidence"
install -d -o qcrl -g qcrl -m 750 "$evidence"
sha256sum /etc/qcrl-stream.env > "$evidence/environment-before.sha256"
git -C /opt/qcrl-stream rev-parse HEAD > "$evidence/public-head-before.txt"
git -c safe.directory="$source_root" -C "$source_root" rev-parse HEAD > "$evidence/source-commit.txt"
systemctl show qcrl-collector.timer qcrl-stream-pilot.service > "$evidence/collectors-before.properties"
python=/opt/qcrl-stream/venv/bin/python
script="$source_root/infra/stream/encoding_confirmation.py"
common=(--working-directory="$source_root" --property=User=qcrl --property=Group=qcrl
 --property=MemoryMax=512M --property=TasksMax=32 --property=RuntimeMaxSec=120
 --property=RemainAfterExit=yes --property=NoNewPrivileges=yes --property=PrivateTmp=yes
 --property=ProtectSystem=strict --property=ProtectHome=yes --property="ReadWritePaths=$evidence")
finish() {
 local unit=$1 prefix=$2
 for attempt in $(seq 1 260); do
   state=$(systemctl show "$unit.service" -p SubState --value)
   if test "$state" = exited || test "$state" = failed; then break; fi
   sleep .5
 done
 systemctl show "$unit.service" > "$prefix-unit.properties"
 journalctl -u "$unit.service" --no-pager > "$prefix-journal.txt"
 test "$(systemctl show "$unit.service" -p SubState --value)" = exited
 test "$(systemctl show "$unit.service" -p Result --value)" = success
 test "$(systemctl show "$unit.service" -p ExecMainStatus --value)" = 0
 systemctl stop "$unit.service"
}
test_unit="qcrl-encoding-confirm-$(basename "$stage_root")-tests"
systemd-run --unit="$test_unit" "${common[@]}" --property=CPUQuota=75% "$python" -m unittest discover -s tests -q
finish "$test_unit" "$evidence/tests"
sudo -u qcrl "$python" "$script" declare --root "$evidence" --corpus /var/lib/qcrl-stream/reader-comparison-linux-20261007-vDV2YH/input-corpus.json
for round in 0 1 2; do
 if test "$round" = 1; then encoders=(reference single_pass); else encoders=(single_pass reference); fi
 for encoder in "${encoders[@]}"; do
  case_root="$evidence/$encoder/$round"
  install -d -o qcrl -g qcrl -m 750 "$case_root"
  tag="qcrl-encoding-confirm-$(basename "$stage_root")-$round-$encoder"
  systemd-run --unit="$tag-producer" "${common[@]}" --property=CPUQuota=100% "$python" "$script" produce --root "$evidence/$encoder" --case "$case_root" --encoder "$encoder"
  "$python" - "$case_root/ready.json" <<'PY'
import json,pathlib,sys,time
p=pathlib.Path(sys.argv[1]); deadline=time.monotonic()+15
while time.monotonic()<deadline:
    try: json.loads(p.read_text()); break
    except (FileNotFoundError,json.JSONDecodeError): time.sleep(.05)
else: raise SystemExit('producer did not become ready')
PY
  systemd-run --unit="$tag-consumer" "${common[@]}" --property=CPUQuota=75% "$python" "$script" consume --root "$evidence/$encoder" --case "$case_root" --encoder "$encoder"
  finish "$tag-consumer" "$case_root/consumer"
  finish "$tag-producer" "$case_root/producer"
  printf 'MEASURED %s\n' "$case_root"
 done
done
sha256sum /etc/qcrl-stream.env > "$evidence/environment-after.sha256"
git -C /opt/qcrl-stream rev-parse HEAD > "$evidence/public-head-after.txt"
cmp "$evidence/environment-before.sha256" "$evidence/environment-after.sha256"
cmp "$evidence/public-head-before.txt" "$evidence/public-head-after.txt"
printf 'timer=%s\nstream=%s\n' "$(systemctl is-active qcrl-collector.timer)" "$(systemctl is-active qcrl-stream-pilot.service || true)" > "$evidence/collectors-after-status.txt"
(cd "$evidence"; find . -type f -exec sha256sum {} + | LC_ALL=C sort) > "$stage_root/origin-inventory.sha256"
printf 'FINITE_ENCODING_CONFIRMATION_MEASURED %s\n' "$stage_root"
