"""Diagnostic-only 64/128 marker-cap comparison; fixed single-pass encoder."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth import receive_path
from execution_truth.contracts import ContractError
from execution_truth.stream_segments import file_hash
from infra.stream import encoding_pair as original

LANES = ["cap64", "cap128"]
POLICY = dict(original.POLICY, schema_version="qcrl.marker_cap_pair_policy.v1",
              encoders=["single_pass"], marker_caps=[64, 128],
              encoder_order="fixed_single_pass_both_lanes",
              cap_order="64_128_then_128_64_then_64_128",
              receiver_variant="scoped_v3_marker_cap_only_not_public_contract_upgrade",
              acceptance="coverage_reproduces_without_tail_or_resource_regression_required_before_rollout")


def lane_policy(lane):
    if lane not in LANES:
        raise ContractError("unsupported fixed marker-cap lane")
    return dict(POLICY, marker_cap=int(lane[3:]), encoder="single_pass")


@contextmanager
def scope(lane):
    selected = lane_policy(lane)
    variant = dict(receive_path.POLICY_V3, max_pending_message_markers=selected["marker_cap"])
    # v3's common-shape validator constructs a legacy helper contract. Give
    # that helper the SAME cap; otherwise valid >64 pending depths fail there.
    helper = dict(receive_path.POLICY, max_pending_message_markers=selected["marker_cap"])
    with patch.object(receive_path, "POLICY_V3", variant), patch.object(
            receive_path, "POLICY", helper), patch.object(
            original, "POLICY", {k: v for k, v in selected.items() if k != "encoder"}):
        yield


def declare_run(corpus_path, root):
    corpus = original.burst.load_corpus(corpus_path)
    repo = Path(__file__).resolve().parents[2]
    files = ["infra/stream/encoding_pair.py", "infra/stream/single_pass_encoder.py",
             "infra/stream/burst_reader_comparison.py", "infra/stream/reader_comparison.py",
             "infra/stream/marker_cap_pair.py", "infra/stream/run_marker_cap_pair.sh"] + sorted(
                 str(p.relative_to(repo)) for p in (repo/"execution_truth").glob("*.py"))
    for lane in LANES:
        with scope(lane), original.lane("single_pass"):
            target = Path(root)/lane
            if (target/"declaration.json").exists() or (target/"corpus.json").exists():
                raise ContractError("do not overwrite marker-cap evidence")
            original.burst.signed(target/"declaration.json", {
                "schema_version": "qcrl.marker_cap_pair_declaration.v1",
                "policy": deepcopy(original.burst.POLICY), "corpus_sha256": corpus["corpus_sha256"],
                "sources": {name: file_hash(repo/name) for name in files},
                "orders_authorized": False, "public_network_capture": False,
                "public_receive_contract_upgrade": False}, "plan_sha256")
            original.burst.persist(target/"corpus.json", corpus)


def execute(role, root, case, lane, require_isolation=False):
    with scope(lane):
        return original.execute(role, root, case, "single_pass", require_isolation)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("declare", "produce", "consume", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--lane", choices=LANES)
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--require-isolation", action="store_true")
    args = parser.parse_args()
    if args.role == "declare":
        declare_run(args.corpus, args.root)
    else:
        result = execute(args.role, args.root, args.case, args.lane, args.require_isolation)
        if result is not None:
            print(json.dumps(result, sort_keys=True))
