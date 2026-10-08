"""Order-reversed confirmation; unchanged candidate, workload and limits."""
import argparse
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth.stream_segments import file_hash
from infra.stream import encoding_pair as original

POLICY = dict(original.POLICY, schema_version="qcrl.encoding_pair_policy.v2",
              encoder_order="candidate_reference_then_reference_candidate_then_candidate_reference",
              confirmation_of_source="faeef8e18d205863e9987c64979c4f2059755c78")


def declare_run(corpus_path, root):
    corpus = original.burst.load_corpus(corpus_path)
    repo = Path(__file__).resolve().parents[2]
    files = ["infra/stream/encoding_pair.py", "infra/stream/single_pass_encoder.py",
             "infra/stream/run_encoding_pair.sh", "infra/stream/burst_reader_comparison.py",
             "infra/stream/reader_comparison.py", "infra/stream/encoding_confirmation.py",
             "infra/stream/run_encoding_confirmation.sh"] + sorted(
                 str(p.relative_to(repo)) for p in (repo/"execution_truth").glob("*.py"))
    with patch.object(original, "POLICY", POLICY):
        for encoder in POLICY["encoders"]:
            with original.lane(encoder):
                target = Path(root)/encoder
                original.burst.signed(target/"declaration.json", {
                    "schema_version": "qcrl.encoding_pair_declaration.v2", "policy": original.burst.POLICY,
                    "corpus_sha256": corpus["corpus_sha256"],
                    "sources": {name: file_hash(repo/name) for name in files},
                    "orders_authorized": False, "public_network_capture": False}, "plan_sha256")
                original.burst.persist(target/"corpus.json", corpus)


def execute(role, root, case, encoder, require_isolation=False):
    with patch.object(original, "POLICY", POLICY):
        return original.execute(role, root, case, encoder, require_isolation)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("role", choices=("declare", "produce", "consume", "verify"))
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--case", type=Path)
    parser.add_argument("--encoder", choices=POLICY["encoders"])
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--require-isolation", action="store_true")
    args = parser.parse_args()
    if args.role == "declare":
        declare_run(args.corpus, args.root)
    else:
        result = execute(args.role, args.root, args.case, args.encoder, args.require_isolation)
        if result is not None:
            print(json.dumps(result, sort_keys=True))
