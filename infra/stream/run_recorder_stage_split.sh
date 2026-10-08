#!/usr/bin/env bash
# Finite offline diagnostic only. Public collector checkouts are not advanced.
set -euo pipefail
test "$(id -u)" = 0
test "$#" = 1
stage_root=$1
case "$stage_root" in /var/lib/qcrl-stream/recorder-stage-split-*) ;; *) exit 2 ;; esac
test ! -L "$stage_root"
source_root="$stage_root/source"
test ! -L "$source_root"
test -z "$(git -c safe.directory="$source_root" -C "$source_root" status --porcelain)"
test "$(systemctl is-active qcrl-stream-pilot.service || true)" = inactive
test "$(df --output=avail -B1 /var/lib/qcrl-stream | tail -1)" -gt 4294967296
input=/var/lib/qcrl-stream/reader-burst-matched-20261008-GL20pl/0-recorder-v3/stream
evidence="$stage_root/evidence"
test ! -e "$evidence"
install -d -o qcrl -g qcrl -m 750 "$evidence"
git -C /opt/qcrl-stream rev-parse HEAD > "$evidence/public-head-before.txt"
sha256sum /etc/qcrl-stream.env > "$evidence/environment-before.sha256"
systemctl show qcrl-collector.timer qcrl-stream-pilot.service > "$evidence/collectors-before.properties"
git -c safe.directory="$source_root" -C "$source_root" rev-parse HEAD > "$evidence/source-commit.txt"
python=/opt/qcrl-stream/venv/bin/python
common=(--working-directory="$source_root" --property=User=qcrl --property=Group=qcrl
  --property=CPUQuota=75% --property=MemoryMax=512M --property=TasksMax=32
  --property=RuntimeMaxSec=120 --property=RemainAfterExit=yes --property=NoNewPrivileges=yes
  --property=PrivateTmp=yes --property=ProtectSystem=strict --property=ProtectHome=yes
  --property="ReadWritePaths=$evidence")
worker() {
  local name=$1
  shift
  local unit="qcrl-split-$(basename "$stage_root")-$name"
  systemd-run --unit="$unit" "${common[@]}" "$python" "$@"
  for attempt in $(seq 1 260); do
    state=$(systemctl show "$unit.service" -p SubState --value)
    if test "$state" = exited || test "$state" = failed; then break; fi
    sleep .5
  done
  systemctl show "$unit.service" > "$evidence/$name-unit.properties"
  journalctl -u "$unit.service" --no-pager > "$evidence/$name-journal.txt"
  test "$(systemctl show "$unit.service" -p SubState --value)" = exited
  test "$(systemctl show "$unit.service" -p Result --value)" = success
  test "$(systemctl show "$unit.service" -p ExecMainStatus --value)" = 0
  systemctl stop "$unit.service"
  printf 'VERIFIED_WORKER %s\n' "$name"
}
worker tests -m unittest discover -s tests -q
script="$source_root/infra/stream/recorder_stage_split.py"
worker prepare "$script" prepare "$input" "$evidence/replay"
worker measure "$script" measure "$input" "$evidence/replay"
for round in 0 1 2; do
  for stage in encode_hash freshness gzip_write gzip_write_fsync durable_log; do
    worker "verify-$round-$stage" "$script" verify "$input" "$evidence/replay" --round "$round" --stage "$stage"
  done
done
worker finalize "$script" finalize "$input" "$evidence/replay"
git -C /opt/qcrl-stream rev-parse HEAD > "$evidence/public-head-after.txt"
sha256sum /etc/qcrl-stream.env > "$evidence/environment-after.sha256"
cmp "$evidence/public-head-before.txt" "$evidence/public-head-after.txt"
cmp "$evidence/environment-before.sha256" "$evidence/environment-after.sha256"
printf 'timer=%s\nstream=%s\n' "$(systemctl is-active qcrl-collector.timer)" "$(systemctl is-active qcrl-stream-pilot.service || true)" > "$evidence/collectors-after-status.txt"
systemctl show qcrl-collector.timer qcrl-stream-pilot.service > "$evidence/collectors-after.properties"
(cd "$evidence"; find . -type f -exec sha256sum {} + | LC_ALL=C sort) > "$stage_root/origin-inventory.sha256"
printf 'FINITE_SPLIT_COMPLETE %s\n' "$stage_root"
