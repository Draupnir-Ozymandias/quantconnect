"""Coverage-aware descriptive aggregation of locked market-phase sequences."""

from datetime import datetime, timezone
from decimal import Decimal

from .bundle import normalize_bundle
from .contracts import ContractError, payload_hash
from .phase_stability import PHASES, _phase_summary


CROSS_MARKET_PHASE_SCHEMA = "qcrl.cross_market_phase_stability.v1"


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _decimal_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _decimal_range(values):
    values = [Decimal(value) for value in values if value is not None]
    if not values:
        return None
    return {"min": _decimal_text(min(values)), "max": _decimal_text(max(values))}


def _phase_contract(raw_sequence, phase):
    if not raw_sequence.get("samples"):
        raise ContractError("cross-market phase sequence has no samples")
    contract = normalize_bundle(raw_sequence["samples"][0])["market_contract"]
    terms = contract["terms"]
    start = _time(terms["event_start_at_utc"])
    end = _time(terms["end_at_utc"])
    captured = _time(raw_sequence["capture_started_at_utc"])
    duration = Decimal(str((end - start).total_seconds()))
    elapsed = Decimal(str((captured - start).total_seconds()))
    third = duration / Decimal(3)
    ranges = {
        "early": (Decimal(0), third),
        "middle": (third, third * Decimal(2)),
        "late": (third * Decimal(2), duration),
    }
    lower, upper = ranges[phase]
    if not lower <= elapsed < upper:
        raise ContractError(f"sequence does not fall in declared {phase} phase")
    return contract, {
        "event_start_at_utc": terms["event_start_at_utc"],
        "event_end_at_utc": terms["end_at_utc"],
        "duration_seconds": int(duration),
        "resolution_source": terms["resolution_source"],
        "outcomes": sorted(item["label"] for item in contract["outcomes"]),
    }


def _outcome_aggregate(summaries, label):
    outcomes = []
    for summary in summaries:
        outcomes.append(next(
            value for value in summary["outcomes"].values()
            if value["outcome"] == label
        ))
    two_sided = [item for item in outcomes if item["two_sided_sample_count"] > 0]
    return {
        "market_count": len(outcomes),
        "two_sided_market_count": len(two_sided),
        "one_sided_market_count": len(outcomes) - len(two_sided),
        "first_observed_midpoint": _decimal_range(
            item["first_observed_midpoint"] for item in outcomes
        ),
        "last_observed_midpoint": _decimal_range(
            item["last_observed_midpoint"] for item in outcomes
        ),
        "within_sequence_midpoint_displacement": _decimal_range(
            item["first_to_last_observed_midpoint_displacement"] for item in outcomes
        ),
        "spread": _decimal_range(
            bound
            for item in outcomes if item["spread"]
            for bound in item["spread"].values()
        ),
        "displayed_bid_depth": _decimal_range(
            bound
            for item in outcomes if item["displayed_bid_depth"]
            for bound in item["displayed_bid_depth"].values()
        ),
        "displayed_ask_depth": _decimal_range(
            bound
            for item in outcomes if item["displayed_ask_depth"]
            for bound in item["displayed_ask_depth"].values()
        ),
    }


def _phase_aggregate(items, outcome_labels):
    summaries = [item["summary"] for item in items]
    cadence_warnings = []
    metadata_values = []
    for item in items:
        summary = item["summary"]
        maximum_gap = Decimal(summary["observed_polling_gap_seconds"]["max"])
        requested = Decimal(summary["requested_interval_seconds"])
        if maximum_gap > requested * Decimal(2):
            cadence_warnings.append(item["market_label"])
        for value in summary["execution_metadata_values"]:
            if value not in metadata_values:
                metadata_values.append(value)
    return {
        "market_count": len(items),
        "market_labels": [item["market_label"] for item in items],
        "cadence_warning_market_count": len(cadence_warnings),
        "cadence_warning_markets": cadence_warnings,
        "observed_polling_gap_seconds": _decimal_range(
            bound
            for summary in summaries
            for bound in summary["observed_polling_gap_seconds"].values()
        ),
        "maximum_polling_gap_excess_seconds": _decimal_range(
            summary["maximum_polling_gap_excess_seconds"] for summary in summaries
        ),
        "execution_metadata_stable_within_all_sequences": all(
            summary["execution_metadata_stable"] for summary in summaries
        ),
        "distinct_execution_metadata_values": metadata_values,
        "outcomes": {
            label: _outcome_aggregate(summaries, label)
            for label in outcome_labels
        },
    }


def _complete_path(phases, outcome_labels):
    outcomes = {}
    for label in outcome_labels:
        anchors = {}
        for phase in PHASES:
            outcome = next(
                value for value in phases[phase]["outcomes"].values()
                if value["outcome"] == label
            )
            anchors[phase] = outcome["first_observed_midpoint"]
        early = anchors["early"]
        outcomes[label] = {
            "first_observed_midpoint_by_phase": anchors,
            "displacement_from_early": {
                phase: (
                    _decimal_text(Decimal(value) - Decimal(early))
                    if value is not None and early is not None else None
                )
                for phase, value in anchors.items()
            },
        }
    return outcomes


def analyze_cross_market_phases(markets):
    """Aggregate aligned phase evidence while retaining explicit missing cells."""
    if not isinstance(markets, dict) or len(markets) < 2:
        raise ContractError("cross-market analysis requires at least two markets")

    market_results = {}
    phase_items = {phase: [] for phase in PHASES}
    seen_market_ids = set()
    cohort_shape = None
    outcome_labels = None

    for market_label in sorted(markets):
        sequences = markets[market_label]
        if not isinstance(market_label, str) or not market_label.strip():
            raise ContractError("cross-market market label is required")
        if not isinstance(sequences, dict) or set(sequences) != set(PHASES):
            raise ContractError("each market requires exact early, middle, and late keys")

        phases = {}
        identity = None
        market_shape = None
        for phase in PHASES:
            raw = sequences[phase]
            if raw is None:
                continue
            current_identity, summary = _phase_summary(raw)
            _, current_shape = _phase_contract(raw, phase)
            if identity is None:
                identity = current_identity
                market_shape = current_shape
            elif current_identity != identity or current_shape != market_shape:
                raise ContractError("phase sequences do not share one market contract")
            phases[phase] = summary
            phase_items[phase].append({"market_label": market_label, "summary": summary})

        if identity is None:
            raise ContractError("each market requires at least one observed phase")
        market_id = identity["market_id"]
        if market_id in seen_market_ids:
            raise ContractError("cross-market analysis contains a duplicate market")
        seen_market_ids.add(market_id)

        shape = {
            "duration_seconds": market_shape["duration_seconds"],
            "resolution_source": market_shape["resolution_source"],
            "outcomes": market_shape["outcomes"],
        }
        if cohort_shape is None:
            cohort_shape = shape
            outcome_labels = shape["outcomes"]
        elif shape != cohort_shape:
            raise ContractError("cross-market contracts do not share one cohort shape")

        missing = [phase for phase in PHASES if phase not in phases]
        market_results[market_label] = {
            "market_identity": identity,
            "event_start_at_utc": market_shape["event_start_at_utc"],
            "event_end_at_utc": market_shape["event_end_at_utc"],
            "coverage": "complete" if not missing else "partial",
            "missing_phases": missing,
            "phases": phases,
        }

    complete_labels = [
        label for label, result in market_results.items()
        if result["coverage"] == "complete"
    ]
    if len(complete_labels) < 2:
        raise ContractError("cross-market analysis requires at least two complete markets")

    complete_paths = {
        label: _complete_path(market_results[label]["phases"], outcome_labels)
        for label in complete_labels
    }
    late_extremes = []
    for item in phase_items["late"]:
        summary = item["summary"]
        values = [
            outcome["first_observed_midpoint"]
            for outcome in summary["outcomes"].values()
        ]
        if any(value is None for value in values) or any(
            Decimal(value) <= Decimal("0.05") or Decimal(value) >= Decimal("0.95")
            for value in values if value is not None
        ):
            late_extremes.append(item["market_label"])

    phase_aggregates = {
        phase: _phase_aggregate(phase_items[phase], outcome_labels)
        for phase in PHASES
    }
    result = {
        "schema_version": CROSS_MARKET_PHASE_SCHEMA,
        "evidence_role": "cross_market_descriptive_execution_truth",
        "coverage": {
            "market_count": len(market_results),
            "complete_market_count": len(complete_labels),
            "partial_market_count": len(market_results) - len(complete_labels),
            "available_sequence_count": sum(len(items) for items in phase_items.values()),
            "phase_market_counts": {
                phase: len(phase_items[phase]) for phase in PHASES
            },
            "missing_phases_by_market": {
                label: value["missing_phases"]
                for label, value in market_results.items() if value["missing_phases"]
            },
        },
        "cohort_contract_shape": cohort_shape,
        "markets": market_results,
        "phase_aggregates": phase_aggregates,
        "complete_market_paths": complete_paths,
        "descriptive_findings": {
            "late_directional_extreme_market_count": len(late_extremes),
            "late_directional_extreme_markets": late_extremes,
            "late_observed_market_count": len(phase_items["late"]),
            "cadence_warning_sequence_count": sum(
                value["cadence_warning_market_count"] for value in phase_aggregates.values()
            ),
        },
        "limitations": [
            "partial markets contribute only observed phases and no missing value is imputed",
            "two complete markets are insufficient for a stability or execution verdict",
            "directional extremes describe contract price state, not signal accuracy",
            "displayed depth is public snapshot depth, not executable fill evidence",
            "polling gaps include request and network duration and are not latency measurements",
            "Binance noon-Eastern terms are incompatible with the Coinbase midnight-UTC QCRL signal",
            "the analysis does not establish queue position, fills, settlement, or profitability",
        ],
    }
    result["analysis_sha256"] = payload_hash(result)
    return result
