# region imports
from AlgorithmImports import *
# endregion

# Experiment Store
# ================
# Persistent experiment retrieval abstraction for QCRL.

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
        self.report_prefix = (
            report_prefix
            or self.REPORT_PREFIX
        )
        self.record_prefix = (
            record_prefix
            or self.RECORD_PREFIX
        )
        self.legacy_report_prefix = (
            legacy_report_prefix
            or self.LEGACY_REPORT_PREFIX
        )

        self._records_cache = None
        self._records_by_run_id = None

    # ------------------------------------------------------------------
    # ObjectStore compatibility helpers
    # ------------------------------------------------------------------

    def _keys(self):
        return [
            str(key)
            for key in self.object_store.keys
        ]


    def _contains_key(self, key):
        return bool(
            self.object_store.contains_key(key)
        )


    def _read_text(self, key):
        if not self._contains_key(key):
            raise KeyError(
                f"ObjectStore key not found: {key}"
        )

        return self.object_store.read(key)


    def _save_text(self, key, value):
        return self.object_store.save(
            key,
            value
        )

    def _read_json(self, key):
        value = self._read_text(key)

        if isinstance(value, bytes):
            value = value.decode("utf-8")

        return json.loads(value)

    def _save_json(self, key, value):
        text = json.dumps(
            value,
            indent=2,
            sort_keys=True
        )

        return self._save_text(key, text)

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

        return [
            key
            for key in keys
            if key.startswith(prefix)
        ]

    def load_all(self, include_legacy=True):
        """
        Return all normalized experiment records.

        Retrieval priority:
        1. Existing normalized v2 record files.
        2. Canonical v2 reports normalized in memory.
        3. Legacy reports normalized in memory.

        New runs use single-report persistence, so step 2 is the normal
        path going forward.
        """
        if self._records_cache is not None:
            return list(self._records_cache)

        from report_models import ResearchReport

        records_by_run_id = {}

        # 1. Existing normalized v2 records.
        for key in self.list_keys(self.record_prefix):
            try:
                record = self._read_json(key)
            except Exception:
                continue

            record.setdefault("record_source", "v2")

            run_id = record.get("run_id")

            if run_id:
                records_by_run_id[run_id] = record

        # 2. Canonical v2 reports.
        for key in self.list_keys(self.report_prefix):
            try:
                report = self._read_json(key)
                record = ResearchReport.normalized_record(
                    report
                )
            except Exception:
                continue

            record["record_source"] = "v2"
            run_id = record.get("run_id")

            if (
                run_id
                and run_id not in records_by_run_id
            ):
                records_by_run_id[run_id] = record

        # 3. Legacy reports.
        if include_legacy:
            for key in self.list_keys(
                self.legacy_report_prefix
            ):
                try:
                    report = self._read_json(key)
                    record = ResearchReport.normalized_record(
                        report
                    )
                except Exception:
                    continue

                record["record_source"] = "legacy"
                run_id = record.get("run_id")

                if (
                    run_id
                    and run_id not in records_by_run_id
                ):
                    record["legacy_objectstore_key"] = key
                    records_by_run_id[run_id] = record

        records = list(records_by_run_id.values())
        records.sort(
            key=lambda record: str(
                record.get("generated_at_utc")
                or ""
            )
        )

        self._records_cache = records
        self._records_by_run_id = records_by_run_id

        return list(records)

    def select(self, **filters):
        records = self.load_all()
        selected = []

        for record in records:
            keep = True

            for field, expected in filters.items():
                actual = record.get(field)

                if isinstance(
                    expected,
                    (list, tuple, set)
                ):
                    if actual not in expected:
                        keep = False
                        break
                elif actual != expected:
                    keep = False
                    break

            if keep:
                selected.append(record)

        return selected

    def get(self, run_id):
        if self._records_by_run_id is None:
            self.load_all()

        return self._records_by_run_id.get(run_id)

    def load_report(self, run_id):
        record = self.get(run_id)

        if record is None:
            return None

        report_key = record.get(
            "objectstore_report_key"
        )

        if (
            report_key
            and self._contains_key(report_key)
        ):
            return self._read_json(report_key)

        legacy_key = record.get(
            "legacy_objectstore_key"
        )

        if (
            legacy_key
            and self._contains_key(legacy_key)
        ):
            return self._read_json(legacy_key)

        return None

    def save_report_and_record(self, report):
        """
        Backward-compatible method name.

        Saves one canonical full report. The normalized record is
        reconstructed in memory during retrieval.
        """
        from report_models import ResearchReport

        record = ResearchReport.normalized_record(report)
        report_key = record["objectstore_report_key"]

        report_saved = False
        persistence_error = None

        try:
            save_result = self._save_json(
                report_key,
                report
            )

            # QuantConnect returns False on a failed save. Some compatible
            # stores return None on success, so only explicit False fails.
            report_saved = save_result is not False

        except Exception as error:
            persistence_error = str(error)
            report_saved = False

        record["_persistence"] = {
            "storage_mode": "single_report",
            "report_saved": report_saved,
            "record_saved_separately": False,
            "report_key": report_key,
            "error": persistence_error
        }

        if report_saved:
            self.clear_cache()

        return record

    def top(
        self,
        records=None,
        sort_by="risk_adjusted_score",
        n=10,
        reverse=True
    ):
        if records is None:
            records = self.load_all()

        def sort_value(record):
            value = record.get(sort_by)

            if value is None:
                return (
                    float("-inf")
                    if reverse
                    else float("inf")
                )

            return value

        return sorted(
            records,
            key=sort_value,
            reverse=reverse
        )[:n]
