# Research Tools v2
# =================
# Researcher-facing query and inspection layer for QCRL experiment records.
#
# This file intentionally depends on ExperimentStore, not directly on the
# QuantConnect ObjectStore layout. Discovery Layer code can also build on the
# same normalized records returned here.

from experiment_store import ExperimentStore


class ResearchTools:
    DEFAULT_COLUMNS = [
        "rank",
        "run_id",
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
            "survival_rate": 0
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
