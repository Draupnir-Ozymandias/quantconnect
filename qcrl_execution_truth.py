"""Operator CLI for public Polymarket evidence capture and promotion."""

import argparse
from pathlib import Path

from execution_truth import (
    PublicPolymarketAcquirer,
    normalize_bundle,
    promote_raw_evidence,
    store_raw_bundle,
    store_raw_discovery,
    verify_live_evidence_inventory,
)


PROJECT_DIR = Path(__file__).resolve().parent
LOCAL_RAW_DIR = PROJECT_DIR / ".qcrl" / "execution_truth" / "raw"
DURABLE_DIR = PROJECT_DIR / "evidence" / "polymarket" / "live"
DURABLE_RAW_DIR = DURABLE_DIR / "raw"


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


def promote(args):
    path = promote_raw_evidence(args.source, DURABLE_RAW_DIR)
    print(path)


def verify(args):
    root = Path(args.directory)
    count = verify_live_evidence_inventory(root)
    print(f"Verified {count} live evidence artifact(s).")


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

    promote_parser = commands.add_parser("promote")
    promote_parser.add_argument("source")
    promote_parser.set_defaults(handler=promote)

    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("directory", nargs="?", default=DURABLE_DIR)
    verify_parser.set_defaults(handler=verify)
    return parser


def main():
    args = build_parser().parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
