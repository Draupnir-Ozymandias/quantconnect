"""Bounded public wire smoke: current BTC 5m market, no credentials/orders."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.acquisition import PublicPolymarketAcquirer, utc_now
from execution_truth.bundle import store_raw_bundle, store_raw_slug_resolution
from execution_truth.contracts import payload_hash
from execution_truth.market_stream import collect_market_stream, verify_stream_log
from execution_truth.rolling_stream import SOURCE, DESCRIPTION, check_market


def main():
    start = int(utc_now().timestamp()) // 300 * 300
    # Allow two heartbeat replies on the lower-throughput EC2 runtime too.
    if utc_now().timestamp() > start + 250:
        raise SystemExit("Too close to rollover; run again in the next window")
    root = Path(".qcrl/execution_truth/streams") / ("smoke-" + str(int(utc_now().timestamp())))
    acquirer = PublicPolymarketAcquirer()
    resolution = acquirer.resolve_market_slug("btc-updown-5m-" + str(start), "market")
    store_raw_slug_resolution(resolution, root)
    bundle = acquirer.acquire_market_bundle(resolution["resolved_market_id"])
    store_raw_bundle(bundle, root)
    spec = check_market(bundle, start, {"resolution_source": SOURCE,
                                       "description_sha256": payload_hash(DESCRIPTION)})
    spec["max_seconds"] = 35
    log = root / "stream.ndjson"
    summary = collect_market_stream(bundle, spec, log)
    verification = verify_stream_log(log)
    passed = (summary["connections"] == 1
              and summary["event_counts"].get("heartbeat:PONG", 0) >= 2
              and set(summary["book_snapshot_assets_by_connection"].get("1", [])) == set(spec["asset_ids"])
              and verification["session_end_present"])
    print(json.dumps({"passed": passed, "path": str(log), "summary": summary,
                      "verification": verification}, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
