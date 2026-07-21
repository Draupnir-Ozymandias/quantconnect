# Research Tools v2
# =================
# Researcher-facing query and inspection layer for QCRL experiment records.
#
# This file intentionally depends on ExperimentStore, not directly on the
# QuantConnect ObjectStore layout. Discovery Layer code can also build on the
# same normalized records returned here.

import csv
import json

from experiment_store import ExperimentStore


class ResearchTools:
    DEFAULT_COLUMNS = [
        "rank",
        "run_id",
        "record_source",
        "coin",
        "timeframe",
        "entry_model",
        "filter_model",
        "stake_mode",
        "net_profit",
        "win_rate",
        "trades",
        "ruined",
        "max_drawdown",
        "max_loss_streak",
        "max_recovery_depth",
        "risk_adjusted_score",
        "tail_risk_score"
    ]

    SUMMARY_NUMERIC_FIELDS = [
        "net_profit",
        "win_rate",
        "trades",
        "max_drawdown",
        "max_loss_streak",
        "max_recovery_depth",
        "max_single_wager",
        "risk_adjusted_score",
        "tail_risk_score",
        "execution_rate",
        "filter_rate",
        "executed_win_rate"
    ]

    CONFIG_SIGNATURE_FIELDS = [
        "coin",
        "timeframe",
        "entry_model",
        "filter_model",
        "stake_mode",
        "streak_length",
        "streak_mode",
        "ema_fast",
        "ema_slow",
        "base_wager",
        "bankroll",
        "multiplier",
        "max_steps",
        "start",
        "end"
    ]

    def __init__(self, object_store=None, store=None):
        if store is not None:
            self.store = store
        elif object_store is not None:
            self.store = ExperimentStore(object_store)
        else:
            raise ValueError("Pass either object_store or store")

        self.records = []

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def load(self, refresh=False, include_legacy=True):
        """
        Load normalized experiment records.

        Usage:
            tools = ResearchTools(qb.object_store)
            records = tools.load()
            records = tools.load(refresh=True)
        """
        if refresh:
            self.store.clear_cache()

        self.records = self.store.load_all(include_legacy=include_legacy)
        return list(self.records)

    def count(self, records=None):
        return len(self._records(records))

    def get(self, run_id):
        """
        Return one normalized experiment record by run_id.
        """
        return self.store.get(run_id)

    def load_report(self, run_id):
        """
        Return the full nested ResearchReport JSON for one run_id.
        """
        return self.store.load_report(run_id)

    # ------------------------------------------------------------------
    # Selection / filtering
    # ------------------------------------------------------------------
    def select(self, records=None, **filters):
        """
        Return records matching filters.

        Exact match:
            tools.select(coin="BTCUSD", timeframe="1h")

        One-of match:
            tools.select(timeframe=["5m", "15m", "1h"])

        Numeric comparisons:
            tools.select(net_profit__gt=0, max_drawdown__lte=5000)

        Text/list containment:
            tools.select(experiment_tags__contains="baseline")
        """
        selected = []

        for record in self._records(records):
            if self._matches(record, filters):
                selected.append(record)

        return selected

    def survivors(self, records=None):
        return self.select(records, ruined=False)

    def ruined(self, records=None):
        return self.select(records, ruined=True)

    def v2(self, records=None):
        """
        Return only normalized v2 records.
        """
        return self.select(records, record_source="v2")

    def legacy(self, records=None):
        """
        Return only legacy imported records.
        """
        return self.select(records, record_source="legacy")

    # ------------------------------------------------------------------
    # Ranking
    # ------------------------------------------------------------------
    def sort(self, records=None, sort_by="risk_adjusted_score", reverse=True):
        records = self._records(records)

        def sort_value(record):
            value = record.get(sort_by)
            if value is None:
                return float("-inf") if reverse else float("inf")
            return value

        return sorted(records, key=sort_value, reverse=reverse)

    def top(
        self,
        records=None,
        sort_by="risk_adjusted_score",
        n=10,
        reverse=True,
        require_survival=False
    ):
        """
        Return top N records sorted by a metric.
        """
        records = self._records(records)

        if require_survival:
            records = self.survivors(records)

        return self.sort(records, sort_by=sort_by, reverse=reverse)[:n]

    def bottom(self, records=None, sort_by="risk_adjusted_score", n=10):
        """
        Return bottom N records sorted by a metric.
        """
        return self.top(records, sort_by=sort_by, n=n, reverse=False)

    def best_survivors(self, records=None, sort_by="risk_adjusted_score", n=10):
        return self.top(
            records,
            sort_by=sort_by,
            n=n,
            reverse=True,
            require_survival=True
        )

    def latest(self, records=None, n=10):
        """
        Return the most recently generated records.
        """
        records = self._records(records)

        def generated_value(record):
            value = record.get("generated_at_utc")
            if value is None:
                value = ""
            return str(value)

        return sorted(records, key=generated_value, reverse=True)[:n]

    def latest_v2(self, n=10):
        """
        Return the most recent v2 records.
        """
        return self.latest(self.v2(), n=n)

    # ------------------------------------------------------------------
    # De-duplication
    # ------------------------------------------------------------------
    def config_signature(self, record):
        """
        Return a tuple that identifies the experimental configuration.
        """
        return tuple(record.get(field) for field in self.CONFIG_SIGNATURE_FIELDS)

    def dedupe(self, records=None, prefer_source="v2"):
        """
        Collapse duplicate configurations into one record.
        """
        records = self._records(records)
        selected = {}

        for record in records:
            signature = self.config_signature(record)
            current = selected.get(signature)

            if current is None:
                selected[signature] = record
                continue

            if self._prefer_record(record, current, prefer_source=prefer_source):
                selected[signature] = record

        out = list(selected.values())
        out.sort(key=lambda r: str(r.get("generated_at_utc") or ""))
        return out

    def duplicates(self, records=None):
        """
        Return duplicate configuration groups.
        """
        records = self._records(records)
        groups = {}

        for record in records:
            signature = self.config_signature(record)
            if signature not in groups:
                groups[signature] = []
            groups[signature].append(record)

        dupes = []

        for signature, group_records in groups.items():
            if len(group_records) > 1:
                dupes.append({
                    "signature": signature,
                    "count": len(group_records),
                    "records": group_records
                })

        dupes.sort(key=lambda item: item["count"], reverse=True)
        return dupes

    # ------------------------------------------------------------------
    # Comparison / summaries
    # ------------------------------------------------------------------
    def compare(self, run_ids_or_records, fields=None):
        """
        Compare a list of run_ids or record dictionaries.

        Usage:
            tools.compare(["run_id_1", "run_id_2"])
            tools.compare([record1, record2])
        """
        if fields is None:
            fields = [
                "run_id",
                "record_source",
                "coin",
                "timeframe",
                "entry_model",
                "filter_model",
                "stake_mode",
                "net_profit",
                "win_rate",
                "trades",
                "ruined",
                "max_drawdown",
                "max_loss_streak",
                "max_recovery_depth",
                "risk_adjusted_score",
                "tail_risk_score"
            ]

        records = []

        for item in run_ids_or_records:
            if isinstance(item, dict):
                records.append(item)
            else:
                record = self.get(item)
                if record is not None:
                    records.append(record)

        return self.project(records, fields)

    def cohort_summary(self, records=None, group_by=None):
        """
        Summarize a cohort of records.

        Usage:
            tools.cohort_summary()
            tools.cohort_summary(btc_1h)
            tools.cohort_summary(group_by="timeframe")
            tools.cohort_summary(group_by=["timeframe", "entry_model"])
        """
        records = self._records(records)

        if group_by is None:
            return self._summarize_records(records)

        if isinstance(group_by, str):
            group_by = [group_by]

        groups = {}

        for record in records:
            key = tuple(record.get(field) for field in group_by)
            if key not in groups:
                groups[key] = []
            groups[key].append(record)

        summaries = []

        for key in sorted(groups.keys(), key=lambda x: str(x)):
            summary = self._summarize_records(groups[key])

            for index, field in enumerate(group_by):
                summary[field] = key[index]

            summaries.append(summary)

        return summaries

    def project(self, records=None, fields=None):
        """
        Return records narrowed to selected fields.
        """
        records = self._records(records)

        if fields is None:
            fields = self.DEFAULT_COLUMNS

        rows = []

        for index, record in enumerate(records, start=1):
            row = {}

            for field in fields:
                if field == "rank":
                    row[field] = index
                else:
                    row[field] = record.get(field)

            rows.append(row)

        return rows

    def unique(self, field, records=None):
        values = []
        seen = set()

        for record in self._records(records):
            value = record.get(field)
            if value not in seen:
                values.append(value)
                seen.add(value)

        return values

    # ------------------------------------------------------------------
    # Dashboard / exports
    # ------------------------------------------------------------------
    def dashboard(self, records=None, top_n=10):
        """
        Return a dictionary of useful ResearchTools views.
        """
        records = self._records(records)
        deduped = self.dedupe(records)

        return {
            "all_summary": self.cohort_summary(records),
            "deduped_summary": self.cohort_summary(deduped),
            "source_summary": self.cohort_summary(records, group_by="record_source"),
            "timeframe_summary": self.cohort_summary(deduped, group_by="timeframe"),
            "top_runs": self.top(deduped, n=top_n),
            "best_survivors": self.best_survivors(deduped, n=top_n),
            "latest_runs": self.latest(records, n=top_n),
            "duplicates": self.duplicates(records)
        }

    def dashboard_text(self, records=None, top_n=10):
        """
        Return a printable dashboard string.
        """
        data = self.dashboard(records=records, top_n=top_n)

        lines = []
        lines.append("========== QCRL RESEARCHTOOLS DASHBOARD ==========")
        lines.append("")

        lines.append("SOURCE SUMMARY")
        lines.append(self.format_table(data["source_summary"]))
        lines.append("")

        lines.append("DEDUPED SUMMARY")
        lines.append(self.format_table([data["deduped_summary"]]))
        lines.append("")

        lines.append("SUMMARY BY TIMEFRAME")
        lines.append(self.format_table(data["timeframe_summary"]))
        lines.append("")

        lines.append("TOP RUNS")
        lines.append(self.show(data["top_runs"], n=top_n))
        lines.append("")

        lines.append("BEST SURVIVORS")
        lines.append(self.show(data["best_survivors"], n=top_n))
        lines.append("")

        lines.append("LATEST RUNS")
        lines.append(self.show(data["latest_runs"], n=top_n))
        lines.append("")

        lines.append(f"DUPLICATE CONFIG GROUPS: {len(data['duplicates'])}")

        return "\n".join(lines)

    def export_csv(self, path, records=None, fields=None):
        """
        Export records to CSV. Returns the path.
        """
        records = self._records(records)

        if fields is None:
            fields = self._all_fields(records)

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()

            for record in records:
                row = {}
                for field in fields:
                    value = record.get(field)
                    if isinstance(value, (dict, list, tuple, set)):
                        value = json.dumps(value, sort_keys=True)
                    row[field] = value
                writer.writerow(row)

        return path

    def export_json(self, path, records=None):
        """
        Export records to JSON. Returns the path.
        """
        records = self._records(records)

        with open(path, "w") as f:
            json.dump(records, f, indent=2, sort_keys=True)

        return path

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------
    def show(self, records=None, fields=None, n=20, sort_by=None, reverse=True):
        """
        Return a small printable table string.

        In QuantConnect notebooks, use:
            print(tools.show(tools.top(n=10)))
        """
        records = self._records(records)

        if sort_by is not None:
            records = self.sort(records, sort_by=sort_by, reverse=reverse)

        records = records[:n]
        rows = self.project(records, fields=fields)
        return self.format_table(rows)

    def to_dataframe(self, records=None):
        """
        Return a pandas DataFrame when pandas is available.
        """
        import pandas as pd
        return pd.DataFrame(self._records(records))

    def format_table(self, rows):
        if rows is None or len(rows) == 0:
            return "No records."

        columns = list(rows[0].keys())
        formatted_rows = []

        for row in rows:
            formatted = []
            for column in columns:
                formatted.append(self._format_value(row.get(column)))
            formatted_rows.append(formatted)

        widths = []
        for index, column in enumerate(columns):
            max_width = len(str(column))
            for row in formatted_rows:
                max_width = max(max_width, len(row[index]))
            widths.append(max_width)

        header = " | ".join(
            str(column).ljust(widths[index])
            for index, column in enumerate(columns)
        )

        divider = "-+-".join("-" * width for width in widths)

        lines = [header, divider]

        for row in formatted_rows:
            line = " | ".join(
                row[index].ljust(widths[index])
                for index in range(len(columns))
            )
            lines.append(line)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _records(self, records=None):
        if records is not None:
            return list(records)

        if len(self.records) == 0:
            self.load()

        return list(self.records)

    def _matches(self, record, filters):
        for field_expr, expected in filters.items():
            field, op = self._parse_filter_expr(field_expr)
            actual = record.get(field)

            if not self._match_value(actual, expected, op):
                return False

        return True

    def _parse_filter_expr(self, field_expr):
        parts = field_expr.rsplit("__", 1)

        if len(parts) == 2:
            field = parts[0]
            op = parts[1]

            if op in [
                "gt",
                "gte",
                "lt",
                "lte",
                "ne",
                "contains",
                "in"
            ]:
                return field, op

        return field_expr, "eq"

    def _match_value(self, actual, expected, op):
        if callable(expected):
            return bool(expected(actual))

        if op == "eq":
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return actual == expected

        if op == "ne":
            return actual != expected

        if op == "in":
            return actual in expected

        if op == "contains":
            if actual is None:
                return False
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            return str(expected) in str(actual)

        try:
            actual_value = float(actual)
            expected_value = float(expected)
        except Exception:
            return False

        if op == "gt":
            return actual_value > expected_value
        if op == "gte":
            return actual_value >= expected_value
        if op == "lt":
            return actual_value < expected_value
        if op == "lte":
            return actual_value <= expected_value

        return False

    def _summarize_records(self, records):
        count = len(records)

        summary = {
            "runs": count,
            "survivors": 0,
            "ruined": 0,
            "survival_rate": 0.0
        }

        if count == 0:
            return summary

        survivors = [r for r in records if r.get("ruined") is False]
        ruined = [r for r in records if r.get("ruined") is True]

        summary["survivors"] = len(survivors)
        summary["ruined"] = len(ruined)
        summary["survival_rate"] = len(survivors) / count

        for field in self.SUMMARY_NUMERIC_FIELDS:
            values = []
            for record in records:
                value = record.get(field)
                if isinstance(value, (int, float)):
                    values.append(value)

            if len(values) == 0:
                continue

            summary[f"avg_{field}"] = sum(values) / len(values)
            summary[f"min_{field}"] = min(values)
            summary[f"max_{field}"] = max(values)

        best = self.top(records, sort_by="risk_adjusted_score", n=1)
        if len(best) > 0:
            summary["best_run_id"] = best[0].get("run_id")
            summary["best_risk_adjusted_score"] = best[0].get(
                "risk_adjusted_score"
            )

        return summary

    def _prefer_record(self, candidate, current, prefer_source="v2"):
        candidate_source = candidate.get("record_source")
        current_source = current.get("record_source")

        if candidate_source == prefer_source and current_source != prefer_source:
            return True

        if candidate_source != prefer_source and current_source == prefer_source:
            return False

        candidate_time = str(candidate.get("generated_at_utc") or "")
        current_time = str(current.get("generated_at_utc") or "")

        if candidate_time != current_time:
            return candidate_time > current_time

        candidate_score = candidate.get("risk_adjusted_score")
        current_score = current.get("risk_adjusted_score")

        try:
            return float(candidate_score) > float(current_score)
        except Exception:
            return False

    def _all_fields(self, records):
        fields = []
        seen = set()

        for field in self.DEFAULT_COLUMNS:
            if field != "rank":
                fields.append(field)
                seen.add(field)

        for record in records:
            for field in sorted(record.keys()):
                if field not in seen:
                    fields.append(field)
                    seen.add(field)

        return fields

    def _format_value(self, value):
        if value is None:
            return ""

        if isinstance(value, bool):
            return str(value)

        if isinstance(value, float):
            # Percent-like fields are handled by caller via field names only in
            # projected data. Keep value compact and readable here.
            return f"{value:.6g}"

        text = str(value)

        if len(text) > 36:
            return text[:33] + "..."

        return text
