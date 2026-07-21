# region imports
from AlgorithmImports import *
# endregion
# Experiment Store
# ================
# Persistent experiment retrieval abstraction for QCRL.
#
# This class is intentionally thin: Discovery Layer code should depend on
# ExperimentStore.load_all(), select(), get(), and load_report(), not on the
# QuantConnect ObjectStore layout.

import json


class ExperimentStore:
    REPORT_PREFIX = "qcrl/v2/experiments/"
    RECORD_PREFIX = "qcrl/v2/records/"
    LEGACY_REPORT_PREFIX = "qcrl/results/"

    def __init__(
        self,
        object_store,
        report_prefix=None,
        record_prefix=None,
        legacy_report_prefix=None
    ):
        self.object_store = object_store
        self.report_prefix = report_prefix or self.REPORT_PREFIX
        self.record_prefix = record_prefix or self.RECORD_PREFIX
        self.legacy_report_prefix = legacy_report_prefix or self.LEGACY_REPORT_PREFIX
        self._records_cache = None
        self._records_by_run_id = None

    # ------------------------------------------------------------------
    # ObjectStore compatibility helpers
    # ------------------------------------------------------------------
    def _method(self, *names):
        for name in names:
            fn = getattr(self.object_store, name, None)
            if callable(fn):
                return fn

        return None

    def _keys(self):
        keys = getattr(self.object_store, "keys", None)

        if keys is None:
            keys = getattr(self.object_store, "Keys", None)

        if callable(keys):
            keys = keys()

        if keys is not None:
            return [str(key) for key in keys]

        # Fallback: QuantConnect ObjectStore is iterable as key-value pairs.
        out = []
        for kvp in self.object_store:
            key = getattr(kvp, "key", None)
            if key is None:
                key = getattr(kvp, "Key", None)
            if key is not None:
                out.append(str(key))

        return out

    def _contains_key(self, key):
        contains = self._method("contains_key", "ContainsKey")

        if contains is None:
            return key in self._keys()

        return bool(contains(key))

    def _read_text(self, key):
        read = self._method("read", "Read", "read_string", "ReadString")

        if read is None:
            raise AttributeError("ObjectStore does not expose read/Read")

        if not self._contains_key(key):
            raise KeyError(f"ObjectStore key not found: {key}")

        return read(key)

    def _save_text(self, key, value):
        save = self._method("save", "Save", "save_string", "SaveString")

        if save is None:
            raise AttributeError("ObjectStore does not expose save/Save")

        return save(key, value)

    def _read_json(self, key):
        value = self._read_text(key)

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return json.loads(value)

    def _save_json(self, key, value):
        return self._save_text(key, json.dumps(value, indent=2, sort_keys=True))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def clear_cache(self):
        self._records_cache = None
        self._records_by_run_id = None

    def list_keys(self, prefix=None):
        keys = self._keys()

        if prefix is None:
            return keys

        return [key for key in keys if key.startswith(prefix)]

    def load_all(self, include_legacy=True):
        """
        Return all normalized experiment records.

        New records are loaded from qcrl/v2/records/. If full reports exist
        without corresponding normalized records, they are normalized on load.
        Legacy qcrl/results/ reports are also normalized when include_legacy=True.
        """
        if self._records_cache is not None:
            return list(self._records_cache)

        from report_models import ResearchReport

        records_by_run_id = {}

        # 1. Preferred source: normalized records.
        for key in self.list_keys(self.record_prefix):
            try:
                record = self._read_json(key)
            except Exception:
                continue

            record.setdefault("record_source", "v2")

            run_id = record.get("run_id")
        if run_id:
            records_by_run_id[run_id] = record

        # 2. Backfill from v2 full reports if a record is missing.
        for key in self.list_keys(self.report_prefix):
            try:
                report = self._read_json(key)
                record = ResearchReport.normalized_record(report)
            except Exception:
                continue

            record["record_source"] = "v2"

            run_id = record.get("run_id")
            if run_id and run_id not in records_by_run_id:
                records_by_run_id[run_id] = record

        # 3. Legacy support for qcrl/results/ config-keyed reports.
        if include_legacy:
            for key in self.list_keys(self.legacy_report_prefix):
                try:
                    report = self._read_json(key)
                    record = ResearchReport.normalized_record(report)
                except Exception:
                    continue

                record["record_source"] = "legacy"

                run_id = record.get("run_id")
                if run_id and run_id not in records_by_run_id:
                    record["legacy_objectstore_key"] = key
                    records_by_run_id[run_id] = record

        records = list(records_by_run_id.values())
        records.sort(key=lambda r: str(r.get("generated_at_utc") or ""))

        self._records_cache = records
        self._records_by_run_id = records_by_run_id

        return list(records)

    def select(self, **filters):
        """
        Return normalized experiment records matching exact field filters.

        Examples:
            store.select(coin="BTCUSD", timeframe="1h")
            store.select(ruined=False, stake_mode="martingale")
            store.select(timeframe=["5m", "15m", "1h"])
        """
        records = self.load_all()
        selected = []

        for record in records:
            keep = True

            for field, expected in filters.items():
                actual = record.get(field)

                if isinstance(expected, (list, tuple, set)):
                    if actual not in expected:
                        keep = False
                        break
                else:
                    if actual != expected:
                        keep = False
                        break

            if keep:
                selected.append(record)

        return selected

    def get(self, run_id):
        """
        Return one normalized experiment record by run_id, or None.
        """
        if self._records_by_run_id is None:
            self.load_all()

        return self._records_by_run_id.get(run_id)

    def load_report(self, run_id):
        """
        Return the full nested ResearchReport JSON for a run_id, or None.
        """
        record = self.get(run_id)

        if record is None:
            return None

        report_key = record.get("objectstore_report_key")

        if report_key and self._contains_key(report_key):
            return self._read_json(report_key)

        legacy_key = record.get("legacy_objectstore_key")

        if legacy_key and self._contains_key(legacy_key):
            return self._read_json(legacy_key)

        return None

    def save_report_and_record(self, report):
        """
        Save a full report and its normalized record.

        Returns the normalized record that was saved.
        """
        from report_models import ResearchReport

        record = ResearchReport.normalized_record(report)
        report_key = record["objectstore_report_key"]
        record_key = record["objectstore_record_key"]

        self._save_json(report_key, report)
        self._save_json(record_key, record)

        self.clear_cache()

        return record

    def top(self, records=None, sort_by="risk_adjusted_score", n=10, reverse=True):
        """
        Convenience helper for ResearchTools v2 notebooks.
        """
        if records is None:
            records = self.load_all()

        def sort_value(record):
            value = record.get(sort_by)
            if value is None:
                return float("-inf") if reverse else float("inf")
            return value

        return sorted(records, key=sort_value, reverse=reverse)[:n]
