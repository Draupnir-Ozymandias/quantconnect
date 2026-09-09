"""Operator CLI for public Polymarket evidence capture and promotion."""

import argparse
import json
from pathlib import Path

from execution_truth import (
    PublicPolymarketAcquirer,
    capture_protocol_status,
    evaluate_latency_sensitivity,
    execute_protocol_capture,
    load_capture_state,
    normalize_bundle,
    normalize_book_sequence,
    promote_raw_evidence,
    replay_taker_buy,
    store_raw_bundle,
    store_raw_book_sequence,
    store_raw_discovery,
    store_raw_slug_resolution,
    verify_live_evidence_inventory,
)


PROJECT_DIR = Path(__file__).resolve().parent
LOCAL_RAW_DIR = PROJECT_DIR / ".qcrl" / "execution_truth" / "raw"
DURABLE_DIR = PROJECT_DIR / "evidence" / "polymarket" / "live"
DURABLE_RAW_DIR = DURABLE_DIR / "raw"
PROTOCOL_STATE_DIR = PROJECT_DIR / ".qcrl" / "execution_truth" / "capture_protocols"


def capture_discovery(args):
    artifact = PublicPolymarketAcquirer().acquire_series_event(
        args.series_id, args.target_at_utc
    )
    path = store_raw_discovery(artifact, LOCAL_RAW_DIR)
    print(path)


def capture_market(args):
    artifact = PublicPolymarketAcquirer().acquire_market_bundle(args.market_id)
    path = store_raw_bundle(artifact, LOCAL_RAW_DIR)
    normalized = normalize_bundle(artifact)
    print(path)
    print(f"normalized_sha256={normalized['bundle_sha256']}")


def capture_sequence(args):
    artifact = PublicPolymarketAcquirer().acquire_book_sequence(
        args.market_id, args.samples, args.interval_seconds
    )
    path = store_raw_book_sequence(artifact, LOCAL_RAW_DIR)
    normalized = normalize_book_sequence(artifact)
    print(path)
    print(f"normalized_sha256={normalized['sequence_sha256']}")


def resolve_slug(args):
    artifact = PublicPolymarketAcquirer().resolve_market_slug(args.slug, args.kind)
    path = store_raw_slug_resolution(artifact, LOCAL_RAW_DIR)
    print(path)
    print(f"market_id={artifact['resolved_market_id']}")


def capture_sequence_slug(args):
    acquirer = PublicPolymarketAcquirer()
    resolution = acquirer.resolve_market_slug(args.slug, args.kind)
    resolution_path = store_raw_slug_resolution(resolution, LOCAL_RAW_DIR)
    print(resolution_path)
    print(f"market_id={resolution['resolved_market_id']}")
    artifact = acquirer.acquire_book_sequence(
        resolution["resolved_market_id"], args.samples, args.interval_seconds
    )
    path = store_raw_book_sequence(artifact, LOCAL_RAW_DIR)
    normalized = normalize_book_sequence(artifact)
    print(path)
    print(f"normalized_sha256={normalized['sequence_sha256']}")


def inspect_sequence(args):
    raw = json.loads(Path(args.source).read_text(encoding="utf-8"))
    print(json.dumps(normalize_book_sequence(raw), indent=2, sort_keys=True))


def promote(args):
    path = promote_raw_evidence(args.source, DURABLE_RAW_DIR)
    print(path)


def verify(args):
    root = Path(args.directory)
    count = verify_live_evidence_inventory(root)
    print(f"Verified {count} live evidence artifact(s).")


def replay(args):
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != "qcrl.taker_replay_example.v1":
        raise ValueError("unsupported replay example schema")
    raw_path = spec_path.parent / spec["raw_bundle_path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    results = [replay_taker_buy(raw, request, spec["policy"])
               for request in spec["requests"]]
    print(json.dumps(results, indent=2, sort_keys=True))


def latency(args):
    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != "qcrl.latency_sensitivity_example.v1":
        raise ValueError("unsupported latency sensitivity example schema")
    raw_path = spec_path.parent / spec["raw_sequence_path"]
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    result = evaluate_latency_sensitivity(
        raw, spec["request"], spec["replay_policy"], spec["latency_policy"]
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def _protocol_inputs(spec_value):
    spec_path = Path(spec_value).resolve()
    protocol = json.loads(spec_path.read_text(encoding="utf-8"))
    state_path = PROTOCOL_STATE_DIR / protocol.get("protocol_id", "invalid") / "state.json"
    return protocol, state_path


def protocol_status(args):
    protocol, state_path = _protocol_inputs(args.spec)
    state = load_capture_state(protocol, state_path)
    result = capture_protocol_status(protocol, state)
    print(json.dumps(result, indent=2, sort_keys=True))


def protocol_capture(args):
    protocol, state_path = _protocol_inputs(args.spec)
    state = load_capture_state(protocol, state_path)
    status = capture_protocol_status(protocol, state)
    selected = next((item for item in status["captures"]
                     if item["capture_id"] == args.capture_id), None)
    if selected is None:
        raise ValueError(f"capture_id is not declared: {args.capture_id}")
    if not args.execute:
        print(json.dumps(selected, indent=2, sort_keys=True))
        print("Dry run only. No public requests made; add --execute to capture.")
        return
    result = execute_protocol_capture(
        protocol, args.capture_id, LOCAL_RAW_DIR, state_path
    )
    print(json.dumps(result, indent=2, sort_keys=True))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    discovery = commands.add_parser("capture-discovery")
    discovery.add_argument("series_id")
    discovery.add_argument("target_at_utc")
    discovery.set_defaults(handler=capture_discovery)

    market = commands.add_parser("capture-market")
    market.add_argument("market_id")
    market.set_defaults(handler=capture_market)

    sequence = commands.add_parser("capture-sequence")
    sequence.add_argument("market_id")
    sequence.add_argument("--samples", type=int, default=5)
    sequence.add_argument("--interval-seconds", type=int, default=5)
    sequence.set_defaults(handler=capture_sequence)

    slug = commands.add_parser("resolve-slug")
    slug.add_argument("slug")
    slug.add_argument("--kind", choices=("event", "market"), default="event")
    slug.set_defaults(handler=resolve_slug)

    slug_sequence = commands.add_parser("capture-sequence-slug")
    slug_sequence.add_argument("slug")
    slug_sequence.add_argument("--kind", choices=("event", "market"), default="event")
    slug_sequence.add_argument("--samples", type=int, default=5)
    slug_sequence.add_argument("--interval-seconds", type=int, default=5)
    slug_sequence.set_defaults(handler=capture_sequence_slug)

    inspect = commands.add_parser("inspect-sequence")
    inspect.add_argument("source")
    inspect.set_defaults(handler=inspect_sequence)

    promote_parser = commands.add_parser("promote")
    promote_parser.add_argument("source")
    promote_parser.set_defaults(handler=promote)

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("directory", nargs="?", default=DURABLE_DIR)
    verify_parser.set_defaults(handler=verify)

    replay_parser = commands.add_parser("replay", help="Replay local snapshot mechanics; no network")
    replay_parser.add_argument("spec")
    replay_parser.set_defaults(handler=replay)

    latency_parser = commands.add_parser(
        "latency", help="Evaluate assumed latency against observed sequence books"
    )
    latency_parser.add_argument("spec")
    latency_parser.set_defaults(handler=latency)

    protocol_status_parser = commands.add_parser(
        "protocol-status", help="Inspect a predeclared sequence-capture protocol"
    )
    protocol_status_parser.add_argument("spec")
    protocol_status_parser.set_defaults(handler=protocol_status)

    protocol_capture_parser = commands.add_parser(
        "protocol-capture", help="Run one eligible predeclared public capture"
    )
    protocol_capture_parser.add_argument("spec")
    protocol_capture_parser.add_argument("capture_id")
    protocol_capture_parser.add_argument("--execute", action="store_true")
    protocol_capture_parser.set_defaults(handler=protocol_capture)
    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
