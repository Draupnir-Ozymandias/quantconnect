"""Deterministic callback/delivery schedules, not a real library or feed model."""

import json
from pathlib import Path

from execution_truth.contracts import payload_hash
from execution_truth.market_stream import collect_market_stream, stream_plan, verify_stream_log, StreamTransportError
from execution_truth.receive_path import POLICY, policy_for, sample_clock
from execution_truth.rolling_stream import persist
from tests.test_market_stream import Clock
from tests.test_receive_capture import rows
from tests.test_taker_replay import raw_bundle


SCENARIOS = [
    {"name": "size%d-burst%d" % (size, count), "payload_bytes": size,
     "connections": [{"burst": count}]}
    for size in (543, 2079) for count in (1, 16, 64, 65, 300)
] + [
    {"name": "prefix25-then65", "payload_bytes": 543, "connections": [{"prefix": 25, "burst": 65}]},
    {"name": "overflow-then-natural-reconnect", "payload_bytes": 543,
     "connections": [{"prefix": 25, "burst": 65}, {"burst": 3}]},
    {"name": "fragmented64-with-controls", "payload_bytes": 543,
     "connections": [{"burst": 64, "fragmented": True, "controls": True}]},
    {"name": "fragmented65-with-controls", "payload_bytes": 543,
     "connections": [{"burst": 65, "fragmented": True, "controls": True}]},
    {"name": "undrained-markers-and-fragment-reconnect", "payload_bytes": 543,
     "connections": [{"burst": 64, "deliver_burst": 1, "incomplete_fragment": True}, {"burst": 3}]},
]


def run_scenario(scenario, root, *, receive_policy="v1"):
    """Run real recorder/verifier with an explicitly synthetic transport fixture.

    Prefix callbacks/deliveries alternate; all burst callbacks happen before any
    burst delivery. Queue/backpressure/stall diagnostics stay unknown: this fixture
    does not measure a real library queue. Identical raw messages retain distinct
    occurrence IDs. A fixture transport close, not metadata overflow, reconnects.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    declaration = {"schema_version": "qcrl.synthetic_receive_burst_schedule.v1", **scenario,
                   "policy_sha256": payload_hash(policy_for(receive_policy)), "network_access": False,
                   "wire_arrival_measured": False, "orders_authorized": False}
    declaration["plan_sha256"] = payload_hash(declaration)
    persist(root / "declaration.json", declaration)
    clock, bundle = Clock(), raw_bundle()
    maximum = sum(c.get("prefix", 0) + c.get("deliver_burst", c["burst"]) for c in scenario["connections"])
    plan = stream_plan(bundle, segmented=True, profiling=True, receive_path=True,
                       source_plan_sha256=declaration["plan_sha256"], max_seconds=20, max_frames=maximum,
                       receive_policy=receive_policy)
    value = {"event_type": "fixture", "market": plan["condition_id"], "asset_id": plan["asset_ids"][0],
             "tag": "€", "padding": ""}
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    value["padding"] = "x" * (scenario["payload_bytes"] - len(encoded.encode()))
    message = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    assert len(message.encode()) == scenario["payload_bytes"]
    delivered, observation = [], {"max_pending_markers": 0, "overflow_callback_message": {}}

    def connector(tracker, number, **kwargs):
        settings = scenario["connections"][number - 1]
        prefix = settings.get("prefix", 0)
        length = prefix + settings.get("deliver_burst", settings["burst"])
        class SyntheticSocket:
            def __init__(self):
                self.reset = tracker.begin_connection(number)
                self.index = self.callback_message = 0

            def send(self, data):
                pass

            def close(self):
                pass

            def frame(self, opcode, final, data):
                clock.pause(.00001)
                accepted = tracker.observe_frame(number, opcode, final, data,
                                                  sample_clock(clock.utc, clock.mono, tracker.domain))
                observation["max_pending_markers"] = max(observation["max_pending_markers"], len(tracker.pending))
                if not accepted and tracker.disabled_reason == "pending_marker_budget":
                    observation["overflow_callback_message"].setdefault(str(number), self.callback_message)

            def observe(self):
                self.callback_message += 1
                raw = message.encode()
                if settings.get("fragmented"):
                    split = raw.index("€".encode()) + 1  # Split inside multibyte UTF-8.
                    self.frame(1, False, raw[:split])
                    if settings.get("controls"):
                        self.frame(9, True, b"protocol-ping")
                    self.frame(0, True, raw[split:])
                else:
                    self.frame(1, True, raw)
                    if settings.get("controls"):
                        self.frame(9, True, b"protocol-ping")

            def recv(self, timeout):
                if self.index == length:
                    if settings.get("incomplete_fragment"):
                        self.frame(1, False, b"unfinished")
                    raise StreamTransportError("synthetic_transport_close")
                if self.index < prefix:
                    self.observe()
                elif self.index == prefix:
                    for _ in range(settings["burst"]):
                        self.observe()
                clock.pause(.00001)
                record = tracker.deliver(number, message, sample_clock(clock.utc, clock.mono, tracker.domain))
                delivered.append(message)
                self.index += 1
                return message, record
        return SyntheticSocket()

    summary = collect_market_stream(bundle, plan, root / "stream", connector=connector,
                                    clock=clock.utc, monotonic=clock.mono, pause=clock.pause,
                                    clock_domain="synthetic.burst." + scenario["name"] + (".v2" if receive_policy == "v2" else ""))
    verified = verify_stream_log(root / "stream")
    archived = rows(root / "stream")
    frames = [row["payload"] for row in archived if row["kind"] == "frame"]
    assert [frame["raw_text"] for frame in frames] == delivered
    assert summary == verified["terminal_summary"]
    assert len(frames) == maximum == verified["frames"]
    details = {}
    for number in range(1, len(scenario["connections"]) + 1):
        records = [frame["receive_path"] for frame in frames if frame["connection"] == number]
        available = [r for r in records if r["telemetry_available"]]
        details[str(number)] = {"delivered": len(records), "available": len(available),
            "unavailable": len(records) - len(available),
            "available_message_sequences": [r["receive_marker"]["message_sequence"] for r in available],
            "unavailable_reasons": sorted({r["unavailable_reason"] for r in records if r["unavailable_reason"]}),
            "library_diagnostics_unknown": all(r["library_queue_depth"] is None and
                r["library_backpressure_active"] is None and r["reader_loop_stall_seconds"] is None for r in records)}
    report = {"schema_version": "qcrl.synthetic_receive_burst_result.v1", "scenario": scenario["name"],
              "source_plan_sha256": declaration["plan_sha256"], "delivered_raw_unchanged": True,
              "delivered_raw_messages_sha256": payload_hash(delivered), "connections": details,
              "resets": [row["payload"] for row in archived if row["kind"] == "receive_path_reset"],
              "observation": observation, "verification": verified,
              "synthetic_not_library_or_network_timing": True, "orders_authorized": False}
    report["report_sha256"] = payload_hash(report)
    persist(root / "report.json", report)
    return report
