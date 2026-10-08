"""Verified offline receive-phase/gap diagnostics; no network or fill interfaces."""

import argparse
from array import array
from collections import Counter
from copy import deepcopy
import gzip
import json
import math
from pathlib import Path

from .contracts import ContractError, payload_hash, verify_artifact_hash
from .market_stream import stream_plan, verify_stream_log
from .receive_path import policy_version
from .rolling_stream import check_market, persist, validate_plan
from .stream_cross_site import resource_summary
from .stream_freshness import epoch, statistics


SCHEMA = "qcrl.receive_phase_analysis.v1"
POLICY = {"schema_version": "qcrl.receive_phase_analysis_policy.v1",
          "accepted_stream_schemas": ["qcrl.public_market_stream_spec.v4", "qcrl.public_market_stream_spec.v5"],
          "phase_unit": "application_delivered_message_not_exchange_event",
          "timing_population": "available_and_locally_timing_eligible_only_keep_missing_denominators",
          "eligibility_rule": "both_first_and_last_observation_intervals_locally_eligible",
          "quantiles": "linear_interpolation_at_(count-1)*q",
          "gap_reference": "connection_gap_log_monotonic_not_wire_disconnect",
          "clock_correction": "none", "max_messages": 1000000, "max_classifications": 1000000,
          "library_depth_bins": [0, 16, 32, 64, 128, 1024],
          "max_profiles": 10000, "max_counter_keys": 128, "max_source_file_bytes": 16 * 1024**2}
POLICY_V2 = deepcopy(POLICY)
POLICY_V2["schema_version"] = "qcrl.receive_phase_analysis_policy.v2"
POLICY_V2["accepted_stream_schemas"].append("qcrl.public_market_stream_spec.v6")
POLICY_V2["freshness_samples"] = "raw_replayed_bounded_connection_snapshots_not_state_validity"
POLICY_V3=deepcopy(POLICY_V2)
POLICY_V3['schema_version']='qcrl.receive_phase_analysis_policy.v3'
POLICY_V3['accepted_stream_schemas'].append('qcrl.public_market_stream_spec.v7')
POLICY_V3['recovery']='verified_complete_occurrence_fences_keep_unknown_and_recovered_populations_separate'


def _load(path, hash_field):
    with Path(path).open("rb") as handle:
        raw = handle.read(POLICY["max_source_file_bytes"] + 1)
    if len(raw) > POLICY["max_source_file_bytes"]:
        raise ContractError("receive analysis source file exceeds budget")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ContractError("receive analysis source must be an object")
    verify_artifact_hash(value, hash_field, "receive analysis source")
    import hashlib
    return value, hashlib.sha256(raw).hexdigest()


def _sealed_rows(root, verified):
    """Recheck bounded rows/chain on the analysis pass against the verified anchor."""
    previous, ordinal, total = None, 0, 0
    for index in range(verified["segments"]):
        with gzip.open(root / ("segment-%06d.gz" % index), "rb") as handle:
            while True:
                line = handle.readline(4 * 1024**2 + 1)
                if not line:
                    break
                total += len(line)
                if len(line) > 4 * 1024**2 or total > verified["uncompressed_bytes"] or not line.endswith(b"\n"):
                    raise ContractError("analysis pass exceeds verified sealed byte budget")
                row = json.loads(line)
                verify_artifact_hash(row, "record_sha256", "analysis-pass stream row")
                if row["ordinal"] != ordinal or row["previous_sha256"] != previous:
                    raise ContractError("analysis-pass stream chain mismatch")
                previous, ordinal = row["record_sha256"], ordinal + 1
                yield row
    if (ordinal != verified["records"] or previous != verified["final_record_sha256"]
            or total != verified["uncompressed_bytes"]):
        raise ContractError("analysis pass differs from verified stream anchor")


def _number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ContractError("receive analysis requires finite nonnegative monotonic log clocks")
    return value


def _bucket():
    return {"counts": Counter(), "reasons": Counter(), "warnings": Counter(),
            "values": {key: array("d") for key in ("lower", "upper", "reader", "delivery_width", "receive_width")},
            "queue": Counter(), "pending": Counter(), "backpressure": Counter(), "max_queue": None}


def _count(counter, key):
    if not isinstance(key, str) or len(key) > 128 or (key not in counter and len(counter) >= POLICY["max_counter_keys"]):
        raise ContractError("receive analysis counter budget exceeded")
    counter[key] += 1


def _add(bucket, record, selected):
    counts = bucket["counts"]
    counts["messages"] += 1
    counts["selected_market_messages"] += int(selected)
    marker = record.get("receive_marker")
    counts["available"] += int(marker is not None)
    counts["unknown"] += int(marker is None)
    if marker is None:
        _count(bucket["reasons"], record["unavailable_reason"])
    else:
        bounds = record["last_observation_to_delivery"]
        eligible = bounds["timing_eligible"] and record["first_observation_to_delivery"]["timing_eligible"]
        counts["timing_eligible"] += int(eligible)
        counts["available_but_timing_ineligible"] += int(not eligible)
        for warning in set(bounds["warnings"] + record["first_observation_to_delivery"]["warnings"]):
            _count(bucket["warnings"], warning)
        if eligible:
            bucket["values"]["lower"].append(bounds["lower_seconds"])
            bucket["values"]["upper"].append(bounds["upper_seconds"])
        stamp = marker["last_receive_observation"]
        bucket["values"]["receive_width"].append(stamp["monotonic_after"] - stamp["monotonic_before"])
    stamp = record.get("application_delivery")
    counts["delivery_stamp_missing"] += int(stamp is None)
    if stamp:
        bucket["values"]["delivery_width"].append(stamp["monotonic_after"] - stamp["monotonic_before"])
    if record.get("reader_loop_stall_seconds") is not None:
        bucket["values"]["reader"].append(record["reader_loop_stall_seconds"])
    for field, name in (("library_queue_depth", "queue"), ("pending_marker_depth", "pending")):
        value = record.get(field)
        label = "unknown" if value is None else str(value)
        if name == "queue" and value is not None:
            bucket["max_queue"] = max(value, bucket["max_queue"] or 0)
            label = next(("at_most_" + str(boundary) for boundary in POLICY["library_depth_bins"] if value <= boundary), "above_1024")
        _count(bucket[name], label)
    pressure = record.get("library_backpressure_active")
    _count(bucket["backpressure"], "unknown" if pressure is None else "true" if pressure else "false")


def _summary(bucket):
    counts = {key: bucket["counts"][key] for key in ("messages", "selected_market_messages", "available", "unknown",
              "timing_eligible", "available_but_timing_ineligible", "delivery_stamp_missing")}
    return {**counts, "timing_population": "retained_application_delivered_messages_only",
            "coverage_denominator": counts["messages"],
            "timing_coverage_fraction": counts["timing_eligible"] / counts["messages"] if counts["messages"] else None,
            "unavailable_reasons": dict(bucket["reasons"]), "timing_warnings": dict(bucket["warnings"]),
            "conditional_callback_to_delivery_lower": statistics(bucket["values"]["lower"]),
            "conditional_callback_to_delivery_upper": statistics(bucket["values"]["upper"]),
            "reader_time_outside_recv": statistics(bucket["values"]["reader"]),
            "application_clock_bracket_width": statistics(bucket["values"]["delivery_width"]),
            "last_receiver_clock_bracket_width": statistics(bucket["values"]["receive_width"]),
            "library_queue_depth_binned_samples": dict(bucket["queue"]), "max_sampled_library_queue_depth": bucket["max_queue"],
            "pending_marker_depth_samples": dict(bucket["pending"]),
            "backpressure_samples": dict(bucket["backpressure"]),
            "tail_population_is_censored": counts["unknown"] > 0 or counts["available_but_timing_ineligible"] > 0}


def _recovery(row, stamp, gap):
    mono = row["local_monotonic_seconds"]
    return {"record_ordinal": row["ordinal"], "connection": row["payload"]["connection"], "logged_at_utc": row["received_at_utc"],
            "gap_log_to_recovery_log_seconds": round(mono - gap["monotonic"], 6),
            "application_delivery_at_utc": stamp["utc"] if stamp else None,
            "gap_log_to_delivery_lower_seconds": round(stamp["monotonic_before"] - gap["monotonic"], 6) if stamp else None,
            "gap_log_to_delivery_upper_seconds": round(stamp["monotonic_after"] - gap["monotonic"], 6) if stamp else None}


def analyze_rows(rows, spec, contract):
    """Internal scan; public entry verifies sealed rows and source bindings first."""
    total, phases, connections = _bucket(), {p: _bucket() for p in ("normal", "draining", "unknown")}, {}
    gaps, profiles, resets, saturations = [], [], [], {}
    freshness_samples = []
    recovery=spec.get('schema_version')=='qcrl.public_market_stream_spec.v7'
    recovery_generations={}
    if recovery:
        phases['recovered']=_bucket()
    previous_mono, previous_wall, initial_offset = None, None, None
    offset_separation, wall_regressions, classification_count = 0.0, 0, 0
    for row in rows:
        mono = _number(row["local_monotonic_seconds"])
        epoch(row["received_at_utc"])
        if previous_mono is not None and mono < previous_mono:
            raise ContractError("receive analysis log clock regressed")
        previous_mono = mono
        kind, payload = row["kind"], row["payload"]
        if kind == "connect_attempt":
            number = payload["connection"]
            if type(number) is not int or number != len(connections) + 1 or number > spec["max_connections"]:
                raise ContractError("receive analysis connection order/limit mismatch")
            connections[number] = {"bucket": _bucket(), "books": {}, "subscribed": None}
        elif kind == "subscribed":
            number = payload["connection"]
            if number not in connections or connections[number]["subscribed"] is not None:
                raise ContractError("invalid duplicate/unattempted subscription")
            connections[number]["subscribed"] = {"logged_at_utc": row["received_at_utc"], "record_ordinal": row["ordinal"]}
            for gap in gaps:
                if number > gap["connection"] and gap["subscribed"] is None:
                    gap["subscribed"] = _recovery(row, None, gap)
        elif kind == "receive_path_reset":
            resets.append({"record_ordinal": row["ordinal"], **payload})
        elif kind == "connection_gap":
            if payload["connection"] not in connections:
                raise ContractError("gap without attempted connection")
            gaps.append({"connection": payload["connection"], "reason": payload["reason"], "monotonic": mono,
                         "logged_at_utc": row["received_at_utc"], "record_ordinal": row["ordinal"],
                         "subscribed": None, "first_selected_message": None, "both_token_books": None})
            if "freshness_telemetry" in spec:
                gaps[-1]["close_diagnostics"] = deepcopy(payload["close_diagnostics"])
        elif kind == "connection_freshness" and "freshness_telemetry" in spec:
            if len(freshness_samples) >= spec["max_connections"] * spec["freshness_telemetry"]["max_samples_per_connection"]:
                raise ContractError("freshness analysis sample budget exceeded")
            freshness_samples.append(deepcopy(payload))
        elif kind == "profiling_sample":
            if len(profiles) >= POLICY["max_profiles"]:
                raise ContractError("receive analysis profiling budget exceeded")
            resources = payload.get("resources", {})
            if not isinstance(resources, dict):
                raise ContractError("profiling resources must be an object or omitted")
            profiles.append({"resources": {"rss_bytes": resources.get("rss_bytes"),
                                            "cgroup_cpu_stat": resources.get("cgroup_cpu_stat")}})
        elif kind == "frame":
            if total["counts"]["messages"] >= POLICY["max_messages"]:
                raise ContractError("receive analysis message budget exceeded")
            number, record = payload["connection"], payload["receive_path"]
            if number not in connections or connections[number]["subscribed"] is None:
                raise ContractError("message before valid subscription")
            classes = payload["classification"]
            classification_count += len(classes)
            if classification_count > POLICY["max_classifications"]:
                raise ContractError("receive analysis classification budget exceeded")
            selected = any(c["scope"] == "selected_market" for c in classes)
            phase = "unknown" if record.get("receive_marker") is None else "draining" if record.get("saturation") else "normal"
            if recovery:
                a=record['alignment']
                recovery_generations[str(number)]=a['generation']
                phase=('unknown' if record.get('receive_marker') is None else
                       'draining' if a['state']=='draining' else 'recovered' if a['generation'] else 'normal')
            for bucket in (total, phases[phase], connections[number]["bucket"]):
                _add(bucket, record, selected)
            saturation = record.get("saturation")
            if saturation and number not in saturations:
                saturations[number] = {"first_reported_record_ordinal": row["ordinal"], "observation": saturation}
            stamp = record.get("application_delivery")
            if stamp:
                if stamp["clock_domain"] != contract["clock_domain"] or stamp["monotonic_after"] > mono:
                    raise ContractError("delivery domain/time differs from owning log clock")
                wall = epoch(stamp["utc"])
                wall_regressions += int(previous_wall is not None and wall < previous_wall)
                previous_wall = wall
                offset = (wall - stamp["monotonic_after"], wall - stamp["monotonic_before"])
                initial_offset = initial_offset or offset
                offset_separation = max(offset_separation, offset[0] - initial_offset[1], initial_offset[0] - offset[1])
            for c in classes:
                if c["scope"] == "selected_market" and c["event_type"] == "book":
                    for asset in c["asset_ids"]:
                        connections[number]["books"].setdefault(asset, {"record_ordinal": row["ordinal"],
                            "logged_at_utc": row["received_at_utc"], "application_delivery_at_utc": stamp["utc"] if stamp else None})
            for gap in gaps:
                if number > gap["connection"] and selected:
                    if gap["first_selected_message"] is None:
                        gap["first_selected_message"] = _recovery(row, stamp, gap)
                    if gap["both_token_books"] is None and set(spec["asset_ids"]) <= set(connections[number]["books"]):
                        gap["both_token_books"] = _recovery(row, stamp, gap)
    for gap in gaps:
        gap["recovered_book_baselines"] = gap["both_token_books"] is not None
    return {"total": _summary(total), "phases": {p: _summary(b) for p, b in phases.items()},
            "connections": {str(n): {"coverage": _summary(c["bucket"]), "subscription": c["subscribed"],
                                      "initial_book_observations": c["books"]} for n, c in connections.items()},
            "gaps": gaps, "resets": resets, "saturations": {str(n): s for n, s in saturations.items()},
            "clock": {"domain": contract["clock_domain"], "application_utc_regressions": wall_regressions,
                      "max_application_wall_minus_monotonic_interval_separation_seconds": round(offset_separation, 6),
                      "clock_correction_applied": False, "cross_host_accuracy_proven": False},
            "resources": resource_summary(profiles),
            **({'verified_recovery_generations_by_connection':recovery_generations} if recovery else {}),
            **({"connection_freshness_samples": freshness_samples} if "freshness_telemetry" in spec else {})}


def analyze_capture(root, *, pilot_root=None, burst_root=None):
    root = Path(root)
    stream = root / "stream"
    verified = verify_stream_log(stream)
    if (not verified["manifest_present"] or not verified["session_end_present"]
            or verified["header_spec"].get("schema_version") not in POLICY_V3["accepted_stream_schemas"]):
        raise ContractError("receive analysis requires finalized receive-path stream v4/v5/v6")
    cohort = pilot_root is not None
    if burst_root is not None:
        burst_root=Path(burst_root)
        if cohort or root.parent.resolve()!=burst_root.resolve():
            raise ContractError('matched burst case must belong directly to explicit declaration root')
    if cohort:
        pilot_root = Path(pilot_root)
        if root.parent.resolve() != pilot_root.resolve():
            raise ContractError("window must belong directly to the explicit pilot root")
    declaration, declaration_bytes = _load(pilot_root / "pilot.json" if cohort else
        burst_root/'declaration.json' if burst_root is not None else root / "declaration.json", "plan_sha256")
    if cohort:
        validate_plan(declaration)
    spec = verified["header_spec"]
    if declaration["plan_sha256"] != spec["source_plan_sha256"]:
        raise ContractError("source declaration does not bind the stream")
    public = declaration.get("schema_version") == "qcrl.receive_path_smoke_declaration.v1"
    synthetic = declaration.get("schema_version") == "qcrl.synthetic_receive_burst_schedule.v1"
    burst=declaration.get('schema_version')=='qcrl.burst_reader_declaration.v1'
    if burst and (burst_root is None or declaration.get('policy',{}).get('schema_version')!='qcrl.burst_reader_policy.v3'
                  or spec['schema_version'] not in ('qcrl.public_market_stream_spec.v6','qcrl.public_market_stream_spec.v7')
                  or declaration.get('public_network_capture') is not False):
        raise ContractError('unsupported recovery burst declaration')
    if not (public or synthetic or cohort or burst):
        raise ContractError("unsupported source declaration role; do not infer campaign provenance")
    if declaration.get("orders_authorized") is not False:
        raise ContractError("source declaration is not explicitly non-trading")
    if public and (declaration.get("max_seconds") != 35 or declaration.get("receive_path") != spec["receive_path"]
                   or declaration.get("max_seconds") != spec["max_seconds"]
                   or declaration.get("market_start") != epoch(spec["event_start_at_utc"])):
        raise ContractError("public smoke declaration differs from its recorded policy/window")
    if synthetic and (declaration.get("network_access") is not False
                      or declaration.get("policy_sha256") != payload_hash(spec["receive_path"])):
        raise ContractError("synthetic schedule role/policy differs from its stream")
    report_path = root / ("result.json" if cohort else "smoke-report.json" if public else "report.json")
    report_field = "result_sha256" if cohort else "report_sha256"
    report, report_bytes = _load(report_path, report_field)
    if burst:
        from infra.stream.burst_reader_comparison import context
        _,corpus,expected_burst=context(burst_root,'recorder',report.get('receive_policy'))
        if report.get('mode')!='recorder' or expected_burst!=spec:
            raise ContractError('burst result differs from locked recorder lane')
    capture_sha, capture_bytes = None, None
    if cohort:
        start = report.get("market_start")
        if type(start) is not int or start not in declaration["market_starts"] or root.name != str(start):
            raise ContractError("window result differs from locked pilot membership")
        capture, capture_bytes = _load(root / "capture_result.json", "result_sha256")
        capture_sha = capture["result_sha256"]
        derived = {k: v for k, v in report.items() if k not in
                   ("verification", "verification_error_type", "verified_at_utc", "capture_result_sha256", "result_sha256")}
        if report.get("capture_result_sha256") != capture_sha or derived != {k: v for k, v in capture.items() if k != "result_sha256"}:
            raise ContractError("final window result differs from immutable capture result")
    if (report["verification"] != verified or ((public or cohort) and
            report["stream_summary" if cohort else "summary"] != verified["terminal_summary"])):
        raise ContractError("source result differs from independently verified stream")
    if public and type(report.get("passed")) is not bool:
        raise ContractError("smoke acceptance must remain explicit boolean")
    bundles = list(root.glob("market-[0-9]*.json"))
    raw_bundle_sha, bundle_bytes = None, None
    if bundles:
        if len(bundles) != 1:
            raise ContractError("ambiguous raw bundle provenance")
        bundle, bundle_bytes = _load(bundles[0], "bundle_sha256")
        expected = stream_plan(bundle, max_seconds=spec["max_seconds"], max_frames=spec["max_frames"], segmented=True,
            profiling="profiling" in spec, resilient="resilience" in spec, receive_path=True,
            source_plan_sha256=declaration["plan_sha256"], receive_policy=policy_version(spec["receive_path"]),
            freshness_telemetry="freshness_telemetry" in spec)
        if expected != spec:
            raise ContractError("stream specification differs from raw source bundle")
        raw_bundle_sha = bundle["bundle_sha256"]
        if public:
            expected_smoke = check_market(bundle, declaration["market_start"], declaration)
            expected_smoke["max_seconds"] = declaration["max_seconds"]
            if expected_smoke != spec:
                raise ContractError("public smoke differs from its exact locked BTC terms")
        if cohort and (check_market(bundle, start, declaration) != spec or report.get("raw_bundle_sha256") != raw_bundle_sha):
            raise ContractError("pilot window differs from locked raw source/terms")
    elif public or cohort or burst:
        raise ContractError("public smoke analysis requires its raw source bundle")
    manifest, manifest_bytes = _load(stream / "manifest.json", "manifest_sha256")
    if any(manifest[key] != verified[key] for key in ("final_record_sha256", "records", "segments",
                                                    "compressed_bytes", "uncompressed_bytes", "session_end_present")):
        raise ContractError("manifest changed after independent verification")
    rows = _sealed_rows(stream, verified)
    first = next(rows)
    scanned = analyze_rows(_prepend(first, rows), spec, first["payload"]["receive_path_contract"])
    if scanned["total"]["messages"] != verified["frames"]:
        raise ContractError("analysis message counts differ from verified footer")
    recovering=spec['schema_version']=='qcrl.public_market_stream_spec.v7'
    selected_policy = POLICY_V3 if recovering or burst else POLICY_V2 if "freshness_telemetry" in spec else POLICY
    result = {"schema_version": "qcrl.receive_phase_analysis.v3" if recovering or burst else "qcrl.receive_phase_analysis.v2" if "freshness_telemetry" in spec else SCHEMA,
              "policy": deepcopy(selected_policy), "policy_sha256": payload_hash(selected_policy),
              "source": {"manifest_sha256": manifest["manifest_sha256"], "manifest_file_sha256": manifest_bytes,
                         "final_record_sha256": verified["final_record_sha256"], "spec_sha256": payload_hash(spec),
                         "contract_sha256": first["payload"]["receive_path_contract"]["contract_sha256"],
                         "declaration_sha256": declaration["plan_sha256"], "declaration_file_sha256": declaration_bytes,
                         "result_sha256": report[report_field], "result_file_sha256": report_bytes,
                         "capture_result_sha256": capture_sha, "capture_result_file_sha256": capture_bytes,
                         "raw_bundle_sha256": raw_bundle_sha, "raw_bundle_file_sha256": bundle_bytes,
                         "raw_bundle_verification": "verified" if raw_bundle_sha else "not_available_in_synthetic_evidence",
                         "role": "locked_pilot_window_not_cohort_verdict" if cohort else
                                 "public_partial_lifecycle_smoke" if public else "synthetic_schedule_not_live",
                         "source_result_status": report.get("status"),
                         "source_acceptance_passed": report["passed"] if public else None},
              "artifact_verification_complete": True, "transport_gap_free": not scanned["gaps"],
              "transport_gap_missing_message_count": None,
              "unobserved_transport_messages_excluded_from_denominators": True,
              "full_locally_eligible_timing_coverage": scanned["total"]["timing_eligible"] == scanned["total"]["messages"],
              "terminal_status": verified["terminal_summary"]["status"], **scanned,
              "limitations": ["conditional_tails_do_not_describe_unknown_or_ineligible_messages",
                  "saturation_context_is_not_wire_arrival_or_exact_recv_return_state", "gap_log_times_are_not_disconnect_instants",
                  "resource_samples_are_whole_service_context_not_event_causes",
                  "verified_records_are_not_exchange_authentication_or_delivery_completeness"],
              "continuous_coverage_proven": False, "wire_arrival_measured": False, "orders_authorized": False}
    result["analysis_sha256"] = payload_hash(result)
    return result


def _prepend(first, rows):
    yield first
    yield from rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pilot-root")
    parser.add_argument('--burst-root')
    args = parser.parse_args()
    report = analyze_capture(args.capture, pilot_root=args.pilot_root,burst_root=args.burst_root)
    persist(args.output, report)
    print(json.dumps({"analysis_sha256": report["analysis_sha256"], "total": report["total"],
                      "transport_gap_free": report["transport_gap_free"]}, indent=2))


if __name__ == "__main__":
    main()
