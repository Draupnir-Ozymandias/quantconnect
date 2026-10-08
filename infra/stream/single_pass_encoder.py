"""Diagnostic-only writer candidate; never selected by public collector code."""
import hashlib

from execution_truth.acquisition import utc_text
from execution_truth.contracts import ContractError, canonical_json
from execution_truth.stream_segments import SegmentedStreamLog, StreamQuotaError


def encode_row(row):
    if not isinstance(row, dict) or "record_sha256" in row:
        raise ContractError("single-pass encoder requires an unhashed row object")
    base = canonical_json(row).encode("utf-8")
    digest = hashlib.sha256(base).hexdigest()
    # The canonical root is an object. Appending its hash changes physical
    # key order/spacing, not the decoded fields or canonical unhashed digest.
    separator = b"," if base != b"{}" else b""
    content = base[:-1] + separator + b'"record_sha256":"' + digest.encode("ascii") + b'"}\n'
    return digest, content


class SinglePassStreamLog(SegmentedStreamLog):
    def append(self, kind, payload):
        started = self.monotonic() if self.profiler else None
        row = {"schema_version": "qcrl.public_market_stream_record.v1", "ordinal": self.ordinal,
               "previous_sha256": self.previous, "received_at_utc": utc_text(self.clock()),
               "local_monotonic_seconds": self.monotonic(), "kind": kind, "payload": payload}
        row["record_sha256"], content = encode_row(row)
        if self.profiler:
            self.profiler.record("encode_hash", self.monotonic() - started)
        if len(content) > 4 * 1024**2:
            raise StreamQuotaError("encoded stream record exceeds bounded reserve")
        # Reserve room for a terminal failure/quota summary, even at the data cap.
        if kind != "session_end" and (
                self.size + len(content) > self.policy["max_uncompressed_bytes"]
                or self.compressed_size + self.raw.tell() + len(content) > self.policy["max_compressed_bytes"] - 4 * 1024**2):
            raise StreamQuotaError("segmented stream total-byte budget reached")
        if self.segment_records and self.segment_bytes + len(content) > self.policy["segment_uncompressed_bytes"]:
            self._seal()
            self._open()
        write_started = self.monotonic() if self.profiler else None
        self.writer.write(content)
        if self.profiler:
            self.profiler.record("compress_write", self.monotonic() - write_started)
        self.pending += 1
        self.size += len(content)
        self.segment_bytes += len(content)
        self.segment_records += 1
        self.ordinal += 1
        self.previous = row["record_sha256"]
        self.final = kind == "session_end"
        if kind != "frame" or self.pending >= 64 or self.monotonic() - self.last_sync >= 1:
            self.sync()
        if self.profiler:
            self.profiler.record("append", self.monotonic() - started)
