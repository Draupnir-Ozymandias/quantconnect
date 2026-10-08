"""Finite paired single-pass encoding trial; numeric localhost only."""
import argparse
from contextlib import contextmanager
import gzip
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from execution_truth import market_stream
from execution_truth.contracts import ContractError, payload_hash
from execution_truth.stream_segments import file_hash
from infra.stream import burst_reader_comparison as burst
from infra.stream.single_pass_encoder import SinglePassStreamLog

POLICY = dict(burst.POLICY, schema_version="qcrl.encoding_pair_policy.v1", modes=["recorder"],
              receive_policies=["v3"], encoders=["reference", "single_pass"],
              encoder_order="reference_candidate_then_candidate_reference_then_reference_candidate",
              representation="reference_sorted_spaced_json_vs_candidate_compact_json_hash_field_last",
              preserves_logical_row_hashes=True, public_rollout_authorized=False)


@contextmanager
def lane(encoder):
    if encoder not in POLICY["encoders"]:
        raise ContractError("unknown fixed encoder")
    with patch.object(burst, "POLICY", dict(POLICY, encoder=encoder)):
        yield


def declare_run(corpus_path, root):
    corpus = burst.load_corpus(corpus_path)
    repo = Path(__file__).resolve().parents[2]
    files = ["infra/stream/encoding_pair.py", "infra/stream/single_pass_encoder.py",
             "infra/stream/run_encoding_pair.sh", "infra/stream/burst_reader_comparison.py",
             "infra/stream/reader_comparison.py"] + sorted(
                 str(p.relative_to(repo)) for p in (repo/"execution_truth").glob("*.py"))
    for encoder in POLICY["encoders"]:
        with lane(encoder):
            target = Path(root)/encoder
            burst.signed(target/"declaration.json", {"schema_version": "qcrl.encoding_pair_declaration.v1",
                "policy": burst.POLICY, "corpus_sha256": corpus["corpus_sha256"],
                "sources": {name: file_hash(repo/name) for name in files},
                "orders_authorized": False, "public_network_capture": False}, "plan_sha256")
            burst.persist(target/"corpus.json", corpus)


def execute(role, root, case, encoder, require_isolation=False):
    with lane(encoder):
        if role == "produce":
            return burst.produce(root, case, "recorder", "v3")
        if role == "consume":
            # The borrowed consumer validates the signed ready binding and
            # numeric loopback URI before invoking the collector. This patch
            # exists ONLY inside the isolated diagnostic consumer process.
            selected = SinglePassStreamLog if encoder == "single_pass" else market_stream.SegmentedStreamLog
            with patch.object(market_stream, "SegmentedStreamLog", selected):
                return burst.consume(root, case, "recorder", "v3")
        if role != "verify":
            raise ContractError("unknown diagnostic role")
        result = burst.verify_case(root, case, "recorder", require_isolation=require_isolation, receive_policy="v3")
        # Prove physical representation and decoded logical identity on every
        # row, not merely that the generic stream verifier accepted the file.
        rows, encoded_bytes = 0, 0
        for path in sorted((Path(case)/"stream").glob("segment-*.gz")):
            with gzip.open(path, "rb") as handle:
                for line in handle:
                    row = json.loads(line)
                    supplied = row.pop("record_sha256")
                    if payload_hash(row) != supplied:
                        raise ContractError("candidate logical hash mismatch")
                    if encoder == "single_pass":
                        from infra.stream.single_pass_encoder import encode_row
                        digest, expected = encode_row(row)
                    else:
                        row["record_sha256"] = supplied
                        expected = (json.dumps(row, sort_keys=True)+"\n").encode("utf-8")
                    if expected != line:
                        raise ContractError("declared row representation mismatch")
                    rows += 1; encoded_bytes += len(line)
        return burst.signed(Path(case)/"encoding-verification.json", {
            "schema_version": "qcrl.encoding_pair_verification.v1", "encoder": encoder,
            "report_sha256": result["report_sha256"], "rows": rows,
            "uncompressed_bytes": encoded_bytes, "logical_hashes_and_representation_verified": True,
            "orders_authorized": False}, "encoding_verification_sha256")


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
