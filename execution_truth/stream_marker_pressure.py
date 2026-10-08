"""Bounded offline v3 marker-pressure diagnostics; no transport-batch inference."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path

from .contracts import ContractError, payload_hash
from .market_stream import verify_stream_log
from .receive_path import validate_contract, policy_version
from .receive_recovery import RecoveryConnectionAudit
from .stream_receive_analysis import _sealed_rows

POLICY = {"schema_version": "qcrl.marker_pressure_policy.v1",
          "max_deliveries": 1000000, "max_episodes": 10000,
          "max_connections": 100, "max_joint_cells": 512,
          "population": "all_archived_application_deliveries",
          "counter_interval": "between_delivery_snapshots_not_socket_read_batch",
          "queue_sample": "after_delivery_bracket_before_marker_consumption",
          "causal_attribution": "none", "clock_correction": "none"}


class PressureScan:
    def __init__(self, contract):
        validate_contract(contract)
        if policy_version(contract["policy"]) != "v3":
            raise ContractError("marker pressure requires explicit v3")
        self.contract = deepcopy(contract)
        self.audits, self.previous, self.episodes = {}, {}, {}
        self.counts, self.joint, self.transitions = Counter(), Counter(), Counter()
        self.maxima = {"observed_message_increment": 0, "observed_frame_increment": 0,
                       "observed_minus_delivered": 0, "library_queue_depth": None,
                       "pending_marker_depth": 0}

    def consume(self, record, raw):
        if self.counts["deliveries"] >= POLICY["max_deliveries"]:
            raise ContractError("pressure delivery budget exceeded")
        connection = record["connection"]
        if connection not in self.audits:
            if len(self.audits) >= POLICY["max_connections"]:
                raise ContractError("pressure connection budget exceeded")
            self.audits[connection] = RecoveryConnectionAudit(self.contract, connection)
        self.audits[connection].consume(record, raw)
        a = record["alignment"]
        prev = self.previous.get(connection)
        known = record["receive_marker"] is not None
        label = "known" if known else "unknown"
        self.counts["deliveries"] += 1
        self.counts[label] += 1
        if prev:
            self.transitions[("known" if prev["known"] else "unknown")+"_to_"+label] += 1
        for field, key in (("observed_messages", "observed_message_increment"),
                           ("observed_frames", "observed_frame_increment")):
            # First snapshot includes observations before the first delivery.
            delta = a[field] - (prev["alignment"][field] if prev else 0)
            self.maxima[key] = max(self.maxima[key], delta)
        self.maxima["observed_minus_delivered"] = max(self.maxima["observed_minus_delivered"],
                                                     a["observed_messages"]-a["delivered_messages"])
        depth = record["library_queue_depth"]
        limit = self.contract["policy"]["max_pending_message_markers"]
        band = ("missing" if depth is None else "above_marker_limit" if depth > limit else
                "above_library_high_water" if depth > self.contract["policy"]["library_queue_high_water_frames"]
                else "at_or_below_library_high_water")
        if depth is not None:
            self.maxima["library_queue_depth"] = max(depth, self.maxima["library_queue_depth"] or 0)
        self.maxima["pending_marker_depth"] = max(self.maxima["pending_marker_depth"], record["pending_marker_depth"])
        key = "|".join((label, a["state"], str(record["unavailable_reason"]), band,
                        str(record["library_backpressure_active"])))
        if key not in self.joint and len(self.joint) >= POLICY["max_joint_cells"]:
            raise ContractError("pressure joint-cell budget exceeded")
        self.joint[key] += 1
        if known:
            self.counts["known_fragmented"] += record["receive_marker"]["fragment_count"] > 1
            # A fresh overflow may already have replaced the provenance by
            # the first retained delivery of the recovered generation.
            prior_episode = self.episodes.get((connection, a["generation"]-1))
            if (prior_episode and prior_episode["fence"] is not None
                    and prior_episode["first_known_after_fence"] is None):
                prior_episode["first_known_after_fence"] = a["delivered_messages"]
        overflow = a["overflow"]
        episode_key = None if overflow is None else (connection, overflow["generation_before"])
        if episode_key is not None:
            if episode_key not in self.episodes:
                if len(self.episodes) >= POLICY["max_episodes"]:
                    raise ContractError("pressure episode budget exceeded")
                self.episodes[episode_key] = {"connection": connection, "overflow": deepcopy(overflow),
                    "first_seen_delivery": a["delivered_messages"], "retained_prefix_deliveries": 0,
                    "unknown_deliveries": 0, "fence": None, "first_known_after_fence": None,
                    "unknown_library_depth_missing": 0, "unknown_library_depth_above_marker_limit": 0}
            episode = self.episodes[episode_key]
            # Overflow provenance persists after recovery: do not count later
            # aligned known deliveries as part of the saturated prefix.
            if a["state"] == "draining" and known:
                episode["retained_prefix_deliveries"] += 1
            if not known and record["unavailable_reason"] == "pending_marker_budget":
                episode["unknown_deliveries"] += 1
                episode["unknown_library_depth_missing"] += depth is None
                episode["unknown_library_depth_above_marker_limit"] += depth is not None and depth > limit
            fence = a["recovery_fence"]
            if fence and fence["generation"] == overflow["generation_before"]+1:
                episode["fence"] = deepcopy(fence)
        self.previous[connection] = {"alignment": deepcopy(a), "known": known}

    def summary(self):
        episodes = list(self.episodes.values())
        return {"counts": dict(self.counts), "maxima": self.maxima,
                "joint_cells_key": "availability|state|reason|library_depth_band|backpressure",
                "joint_cells": dict(sorted(self.joint.items())),
                "availability_transitions": dict(self.transitions), "episodes": episodes,
                "closed_episodes": sum(e["fence"] is not None for e in episodes),
                "open_episodes": sum(e["fence"] is None for e in episodes),
                "connection_audits": [v.summary() for v in self.audits.values()]}


def analyze(stream):
    stream = Path(stream)
    verified = verify_stream_log(stream)
    if verified["frames"] > POLICY["max_deliveries"]:
        raise ContractError("pressure source exceeds delivery budget")
    rows = _sealed_rows(stream, verified)
    first = next(rows)
    contract = first["payload"].get("receive_path_contract")
    if not isinstance(contract, dict):
        raise ContractError("pressure source has no receive contract")
    scan = PressureScan(contract)
    for row in rows:
        if row["kind"] == "frame":
            payload = row["payload"]
            record = payload.get("receive_path")
            if not isinstance(record, dict) or record.get("schema_version") != "qcrl.receive_path_delivery.v3":
                raise ContractError("pressure source has missing or unsupported telemetry")
            scan.consume(record, payload["raw_text"])
    if scan.counts["deliveries"] != verified["frames"]:
        raise ContractError("pressure scan differs from verified frame count")
    result = {"schema_version": "qcrl.marker_pressure_analysis.v1", "policy": deepcopy(POLICY),
              "policy_sha256": payload_hash(POLICY),
              "source": {"contract_sha256": contract["contract_sha256"],
                         "final_record_sha256": verified["final_record_sha256"],
                         "records": verified["records"], "frames": verified["frames"]},
              **scan.summary(), "artifact_verification_complete": True,
              "cohort_provenance_verified": False, "wire_arrival_measured": False,
              "orders_authorized": False, "public_rollout_authorized": False,
              "limitations": ["counter_jumps_are_not_transport_read_batches",
                  "unknown_message_fragment_counts_are_not_retained",
                  "queue_samples_and_marker_counters_are_not_simultaneous",
                  "overflow_reason_identifies_marker_loss_not_the_cause_of_backlog",
                  "callback_completeness_relies_on_pinned_adapter_invariant",
                  "complete_archive_does_not_prove_complete_exchange_delivery"]}
    result["analysis_sha256"] = payload_hash(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stream", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.stream)
    # Never overwrite evidence or previous analysis.
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps({"analysis_sha256": result["analysis_sha256"], "counts": result["counts"],
                      "closed_episodes": result["closed_episodes"], "open_episodes": result["open_episodes"]}))


if __name__ == "__main__":
    main()
