"""Offline cross-site public-stream diagnostics. No trading or latency proof."""

import argparse
from collections import defaultdict
import gzip
import json
import math
from pathlib import Path

from .contracts import ContractError, payload_hash, verify_artifact_hash
from .rolling_stream import check_market, cohort_health, persist, validate_plan
from .stream_freshness import analyze_rows, epoch, statistics
from .stream_segments import verify_segments


SCHEMA = "qcrl.stream_cross_site.v1"
POLICY = {
    "schema_version": SCHEMA,
    "fingerprint": "sha256_canonical_json_selected_event",
    "timing_pairs": "exact_payload_unique_in_each_entire_stream",
    "interval": "intersection_of_selected_socket_receipt_ranges_inclusive",
    "delta": "left_socket_utc_minus_right_socket_utc",
    "quantiles": "linear_interpolation_at_(count-1)*q",
    "max_selected_events_per_stream": 1000000,
    "resource_scope": "whole_service_not_one_market_do_not_sum_overlapping_windows",
    "clock_correction": "none",
}


def resource_summary(samples):
    resources = [s.get("resources", {}) for s in samples]
    cpu = [r.get("cgroup_cpu_stat") for r in resources]
    changes = {}
    for key in ("nr_periods", "nr_throttled", "throttled_usec"):
        values = [c.get(key) if isinstance(c, dict) else None for c in cpu]
        valid = (len(values) >= 2 and all(type(v) is int and v >= 0 for v in values)
                 and all(a <= b for a, b in zip(values, values[1:])))
        changes[key] = values[-1] - values[0] if valid else None
    rss = [r.get("rss_bytes") for r in resources]
    rss = [v for v in rss if type(v) is int and v >= 0]
    return {"profiling_samples": len(samples), "cgroup_counter_change": changes,
            "max_process_rss_bytes": max(rss, default=None),
            "resource_scope": POLICY["resource_scope"]}


def scan_rows(rows):
    """Internal scan; callers must verify raw evidence before using this result."""
    events, profiles = defaultdict(list), []
    count = 0

    def socket_rows():
        nonlocal count
        for row in rows:
            kind, payload = row["kind"], row["payload"]
            if kind == "profiling_sample":
                profiles.append(payload)
                if len(profiles) > 10000:
                    raise ContractError("cross-site profiling budget exceeded")
            if kind == "frame":
                try:
                    receipt = epoch(payload["socket_received_at_utc"])
                    mono = payload["socket_received_monotonic_seconds"]
                except (KeyError, TypeError, ValueError) as exc:
                    raise ContractError("cross-site comparison requires socket timestamps") from exc
                if (not math.isfinite(receipt) or type(mono) not in (int, float)
                        or not math.isfinite(mono)):
                    raise ContractError("socket timestamps must be finite numeric")
                row = {**row, "received_at_utc": payload["socket_received_at_utc"],
                       "local_monotonic_seconds": mono}
                try:
                    data = json.loads(payload["raw_text"])
                    parsed = True
                except ValueError:
                    data = []
                    parsed = False
                objects = data if isinstance(data, list) else [data]
                if parsed:
                    if len(objects) != len(payload["classification"]):
                        raise ContractError("classification/event count mismatch")
                    for event, classification in zip(objects, payload["classification"]):
                        if classification["scope"] == "selected_market":
                            count += 1
                            if count > POLICY["max_selected_events_per_stream"]:
                                raise ContractError("cross-site event budget exceeded")
                            events[payload_hash(event)].append(receipt)
            yield row

    analysis = analyze_rows(socket_rows())
    summary = {"socket_receipt_age": analysis["receipt_age"], "counts": analysis["counts"],
               "gaps": analysis["reconnect_gaps"], "by": analysis["by"],
               "timestamp_regressions": analysis["timestamp_regressions_within_connection_type_assets"],
               "max_wall_minus_monotonic_offset_change_seconds":
                   analysis["max_wall_minus_monotonic_offset_change_seconds"],
               **resource_summary(profiles)}
    return summary, dict(events)


def scan_stream(root):
    root = Path(root)
    verified = verify_segments(root)
    if (not verified["manifest_present"] or not verified["session_end_present"]
            or verified["header_spec"].get("schema_version") != "qcrl.public_market_stream_spec.v3"):
        raise ContractError("cross-site analysis requires finalized raw-reclassified v3 streams")

    def rows():
        for segment in sorted(root.glob("segment-*.gz")):
            with gzip.open(segment, "rt", encoding="utf-8") as handle:
                for line in handle:
                    yield json.loads(line)

    summary, events = scan_rows(rows())
    summary["source"] = {
        "manifest_sha256": json.loads((root / "manifest.json").read_text())["manifest_sha256"],
        "final_record_sha256": verified["final_record_sha256"],
        "header_spec_sha256": payload_hash(verified["header_spec"]),
    }
    return summary, events, verified


def compare_events(left, right):
    """Count overlaps without assuming a feed sequence number or pairing duplicates."""
    flags = {"duplicate_pairing_used_for_timing": False,
             "unmatched_does_not_prove_message_loss": True,
             "one_way_network_latency_proven": False}
    if not left or not right:
        return {"eligible": False, "reason": "no_selected_events", **flags}
    bounds = [(min(min(ts) for ts in m.values()), max(max(ts) for ts in m.values()))
              for m in (left, right)]
    low, high = max(b[0] for b in bounds), min(b[1] for b in bounds)
    if low > high:
        return {"eligible": False, "reason": "no_common_receipt_interval", **flags}
    filtered = [{k: inside for k, ts in m.items() if (inside := [t for t in ts if low <= t <= high])}
                for m in (left, right)]
    shared = sorted(set(filtered[0]) & set(filtered[1]))
    matches = sum(min(len(filtered[0][k]), len(filtered[1][k])) for k in shared)
    unique = [k for k in shared if len(left[k]) == len(right[k]) == 1]
    totals = [sum(map(len, m.values())) for m in filtered]
    return {"eligible": True, "common_selected_receipt_interval_epoch": [low, high],
            "selected_events_in_interval": dict(zip(("left", "right"), totals)),
            "events_outside_interval": {s: sum(map(len, m.values())) - n
                                        for s, m, n in zip(("left", "right"), (left, right), totals)},
            "exact_payload_shared_fingerprints": len(shared),
            "multiplicity_matched_events": matches,
            "unmatched_event_occurrences": dict(zip(("left", "right"), (n - matches for n in totals))),
            "duplicate_shared_fingerprints_excluded_from_timing": len(shared) - len(unique),
            "unique_in_both_entire_streams_payload_matches": len(unique),
            "left_minus_right_socket_receipt_seconds": statistics([left[k][0] - right[k][0] for k in unique]),
            **flags}


def _load_site(root):
    plan = validate_plan(json.loads((root / "pilot.json").read_text()))
    stored = json.loads((root / "health.json").read_text())
    verify_artifact_hash(stored, "health_sha256", "cohort health")
    actual = cohort_health(plan, root)
    if actual != stored:
        raise ContractError("independent cohort verification differs from stored health")
    preflight = json.loads((root / "observer_preflight.json").read_text())
    verify_artifact_hash(preflight, "preflight_sha256", "observer preflight")
    if (preflight.get("schema_version") != "qcrl.observer_preflight.v1"
            or preflight.get("plan_sha256") != plan["plan_sha256"]
            or preflight.get("orders_authorized") is not False):
        raise ContractError("preflight is not bound to this public-only plan")
    for key in ("observer_label", "region", "instance_id", "source_commit",
                "systemd_unit_sha256", "systemd_resource_settings", "common_input_file_sha256"):
        if not preflight.get(key):
            raise ContractError("missing preflight comparability field: " + key)
    return plan, {"health": actual, "preflight": preflight, "cases": {}}


def analyze_cohort(left_root, right_root):
    roots = {"left": Path(left_root), "right": Path(right_root)}
    loaded = {s: _load_site(r) for s, r in roots.items()}
    plans = {s: v[0] for s, v in loaded.items()}
    sites = {s: v[1] for s, v in loaded.items()}
    if plans["left"] != plans["right"]:
        raise ContractError("sites did not use the same locked plan")
    preflights = [sites[s]["preflight"] for s in ("left", "right")]
    for field in ("source_commit", "systemd_unit_sha256", "systemd_resource_settings", "common_input_file_sha256"):
        if preflights[0][field] != preflights[1][field]:
            raise ContractError("site policy differs: " + field)
    if preflights[0]["instance_id"] == preflights[1]["instance_id"]:
        raise ContractError("cross-site comparison requires distinct observers")
    comparisons = []
    for start in plans["left"]["market_starts"]:
        maps, specs = {}, {}
        for site, root in roots.items():
            directory = root / str(start)
            if not (directory / "stream/manifest.json").exists():
                sites[site]["cases"][str(start)] = {"eligible": False, "reason": "missing_finalized_stream"}
                continue
            summary, maps[site], verified = scan_stream(directory / "stream")
            specs[site] = verified["header_spec"]
            result = json.loads((directory / "result.json").read_text())
            verify_artifact_hash(result, "result_sha256", "pilot result")
            raw = json.loads(next(directory.glob("market-[0-9]*.json")).read_text())
            if (result.get("verification") != verified
                    or raw["bundle_sha256"] != result.get("raw_bundle_sha256")
                    or check_market(raw, start, plans[site]) != specs[site]):
                raise ContractError("stream is not bound to pinned source/result")
            summary["source"]["result_sha256"] = result["result_sha256"]
            summary["lifecycle_completed"] = next(c["lifecycle_completed"]
                for c in sites[site]["health"]["cases"] if c["market_start"] == start)
            sites[site]["cases"][str(start)] = summary
        if len(maps) != 2:
            comparisons.append({"start": start, "eligible": False, "reason": "missing_finalized_stream"})
            continue
        for field in ("market_id", "condition_id", "asset_ids", "event_start_at_utc", "event_end_at_utc"):
            if specs["left"][field] != specs["right"][field]:
                raise ContractError("market binding differs: " + field)
        comparisons.append({"start": start, "market_id": specs["left"]["market_id"],
                            **compare_events(maps["left"], maps["right"])})
    report = {"schema_version": SCHEMA, "policy": POLICY, "policy_sha256": payload_hash(POLICY),
              "plan_sha256": plans["left"]["plan_sha256"], "sites": sites, "comparisons": comparisons,
              "measurement": "socket receipt age and exact-event cross-observer UTC difference",
              "geographical_causality_proven": False, "cross_host_clock_accuracy_proven": False,
              "continuous_coverage_proven": False, "orders_authorized": False,
              "event_observations_are_not_independent_market_trials": True}
    report["report_sha256"] = payload_hash(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("left", type=Path)
    parser.add_argument("right", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = analyze_cohort(args.left, args.right)
    persist(args.output, report)
    print(json.dumps({"report": str(args.output), "report_sha256": report["report_sha256"],
                      "comparisons": report["comparisons"]}, sort_keys=True))


if __name__ == "__main__":
    main()
