"""Bounded public application-receipt smoke; no wire-arrival or order claims."""
import json
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.acquisition import PublicPolymarketAcquirer, utc_now
from execution_truth.bundle import store_raw_bundle, store_raw_slug_resolution
from execution_truth.contracts import payload_hash
from execution_truth.market_stream import collect_market_stream, verify_stream_log
from execution_truth.rolling_stream import SOURCE, DESCRIPTION, check_market
from execution_truth.rolling_stream import persist


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--receive-path", action="store_true")
    parser.add_argument("--receive-policy", choices=("v1", "v2"), default="v1")
    parser.add_argument("--root", type=Path)
    args = parser.parse_args()
    if args.receive_path and not args.profile:
        parser.error("receive-path smoke requires --profile")
    if not args.receive_path and args.receive_policy != "v1":
        parser.error("receive policy requires --receive-path")
    start = int(utc_now().timestamp()) // 300 * 300
    # Allow two heartbeat replies on the lower-throughput EC2 runtime too.
    if utc_now().timestamp() > start + 250:
        raise SystemExit("Too close to rollover; run again in the next window")
    root = args.root or Path(".qcrl/execution_truth/streams") / ("smoke-" + str(int(utc_now().timestamp())))
    if root.exists():
        raise SystemExit("Refuse to reuse a smoke evidence directory")
    acquirer = PublicPolymarketAcquirer()
    resolution = acquirer.resolve_market_slug("btc-updown-5m-" + str(start), "market")
    store_raw_slug_resolution(resolution, root)
    bundle = acquirer.acquire_market_bundle(resolution["resolved_market_id"])
    store_raw_bundle(bundle, root)
    plan = {"resolution_source": SOURCE, "description_sha256": payload_hash(DESCRIPTION)}
    if args.profile:
        from execution_truth.stream_profiling import POLICY
        plan["profiling"] = POLICY
    if args.receive_path:
        from execution_truth.receive_path import policy_for
        plan.update(schema_version="qcrl.receive_path_smoke_declaration.v1",
                    declared_at_utc=utc_now().isoformat(), market_start=start,
                    max_seconds=35, receive_path=policy_for(args.receive_policy), orders_authorized=False,
                    evidence_role="partial_lifecycle_connectivity_not_cross_site_comparison")
        plan["plan_sha256"] = payload_hash(plan)
        persist(root / "declaration.json", plan)
    spec = check_market(bundle, start, plan)
    spec["max_seconds"] = 35
    log = root / "stream"
    summary = collect_market_stream(bundle, spec, log)
    verification = verify_stream_log(log)
    passed = (summary["connections"] == 1
              and summary["event_counts"].get("heartbeat:PONG", 0) >= 2
              and set(summary["book_snapshot_assets_by_connection"].get("1", [])) == set(spec["asset_ids"])
              and verification["session_end_present"])
    if args.receive_path:
        received = verification["receive_path_verification"]
        passed = passed and received["available"] == summary["frames"] and received["unavailable"] == 0
    report = {"passed": passed, "path": str(log), "summary": summary,
              "verification": verification, "orders_authorized": False, "wire_arrival_measured": False}
    if args.receive_path:
        report["report_sha256"] = payload_hash(report)
        persist(root / "smoke-report.json", report)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
