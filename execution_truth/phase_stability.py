"""Deterministic descriptive comparison of predeclared market-phase sequences."""

from datetime import datetime, timezone
from decimal import Decimal

from .book_sequence import normalize_book_sequence
from .bundle import normalize_bundle
from .contracts import ContractError, payload_hash


PHASE_STABILITY_SCHEMA = "qcrl.phase_sequence_stability.v1"
PHASES = ("early", "middle", "late")


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _decimal_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _seconds_decimal(delta):
    micros = delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds
    return Decimal(micros) / Decimal(1_000_000)


def _range(values):
    if not values:
        return None
    return {"min": _decimal_text(min(values)), "max": _decimal_text(max(values))}


def _phase_summary(raw_sequence):
    normalized_sequence = normalize_book_sequence(raw_sequence)
    bundles = [normalize_bundle(sample) for sample in raw_sequence["samples"]]
    acquired = [_time(sample["acquired_at_utc"]) for sample in raw_sequence["samples"]]
    gaps = [_seconds_decimal(later - earlier) for earlier, later in zip(acquired, acquired[1:])]
    requested = Decimal(raw_sequence["requested_interval_seconds"])

    outcomes = {}
    for identity in normalized_sequence["market_identity"]["outcomes"]:
        token_id = identity["token_id"]
        books = [
            next(book for book in bundle["order_books"] if book["token_id"] == token_id)
            for bundle in bundles
        ]
        bid_prices = [Decimal(book["best_bid"]["price"]) for book in books if book["best_bid"]]
        ask_prices = [Decimal(book["best_ask"]["price"]) for book in books if book["best_ask"]]
        two_sided = [book for book in books if book["best_bid"] and book["best_ask"]]
        spreads = [
            Decimal(book["best_ask"]["price"]) - Decimal(book["best_bid"]["price"])
            for book in two_sided
        ]
        midpoints = [
            (Decimal(book["best_bid"]["price"]) + Decimal(book["best_ask"]["price"]))
            / Decimal(2)
            for book in two_sided
        ]
        bid_top_sizes = [Decimal(book["best_bid"]["size"]) for book in books if book["best_bid"]]
        ask_top_sizes = [Decimal(book["best_ask"]["size"]) for book in books if book["best_ask"]]
        bid_depth = [sum(Decimal(level["size"]) for level in book["bids"]) for book in books]
        ask_depth = [sum(Decimal(level["size"]) for level in book["asks"]) for book in books]
        outcomes[token_id] = {
            "outcome": identity["label"],
            "best_bid_price": _range(bid_prices),
            "best_ask_price": _range(ask_prices),
            "spread": _range(spreads),
            "midpoint": _range(midpoints),
            "first_observed_midpoint": _decimal_text(midpoints[0]) if midpoints else None,
            "last_observed_midpoint": _decimal_text(midpoints[-1]) if midpoints else None,
            "first_to_last_observed_midpoint_displacement": (
                _decimal_text(midpoints[-1] - midpoints[0]) if midpoints else None
            ),
            "two_sided_sample_count": len(two_sided),
            "missing_best_bid_count": sum(book["best_bid"] is None for book in books),
            "missing_best_ask_count": sum(book["best_ask"] is None for book in books),
            "best_bid_size": _range(bid_top_sizes),
            "best_ask_size": _range(ask_top_sizes),
            "displayed_bid_depth": _range(bid_depth),
            "displayed_ask_depth": _range(ask_depth),
            "distinct_exchange_book_hashes": len({book["exchange_book_hash"] for book in books}),
            "distinct_snapshots": len({book["snapshot_sha256"] for book in books}),
        }

    metadata_values = []
    for bundle in bundles:
        contract = bundle["market_contract"]
        value = {
            "accepting_orders": contract["state"]["accepting_orders"],
            "fees_enabled": contract["state"]["fees_enabled"],
            "taker_order_delay_enabled": contract["constraints"]["taker_order_delay_enabled"],
            "minimum_order_age_seconds": contract["constraints"]["minimum_order_age_seconds"],
        }
        if value not in metadata_values:
            metadata_values.append(value)

    return normalized_sequence["market_identity"], {
        "raw_sequence_sha256": raw_sequence["sequence_sha256"],
        "normalized_sequence_sha256": normalized_sequence["sequence_sha256"],
        "capture_started_at_utc": raw_sequence["capture_started_at_utc"],
        "capture_completed_at_utc": raw_sequence["capture_completed_at_utc"],
        "sample_count": len(bundles),
        "requested_interval_seconds": raw_sequence["requested_interval_seconds"],
        "observed_polling_gap_seconds": _range(gaps),
        "maximum_polling_gap_excess_seconds": _decimal_text(max(gaps) - requested),
        "execution_metadata_stable": len(metadata_values) == 1,
        "execution_metadata_values": metadata_values,
        "outcomes": outcomes,
    }


def analyze_phase_sequences(sequences):
    """Compare exact early/middle/late sequences without inferring missing phases."""
    if not isinstance(sequences, dict) or set(sequences) != set(PHASES):
        raise ContractError("phase stability requires exact early, middle, and late sequences")

    identity = None
    summaries = {}
    for phase in PHASES:
        current_identity, summary = _phase_summary(sequences[phase])
        if identity is None:
            identity = current_identity
        elif current_identity != identity:
            raise ContractError("phase sequences do not share one market identity")
        summaries[phase] = summary

    cross_phase_outcomes = {}
    for outcome in identity["outcomes"]:
        token_id = outcome["token_id"]
        anchors = {
            phase: summaries[phase]["outcomes"][token_id]["first_observed_midpoint"]
            for phase in PHASES
        }
        early_anchor = anchors["early"]
        cross_phase_outcomes[token_id] = {
            "outcome": outcome["label"],
            "first_observed_midpoint_by_phase": anchors,
            "displacement_from_early": {
                phase: (
                    _decimal_text(Decimal(anchor) - Decimal(early_anchor))
                    if anchor is not None and early_anchor is not None else None
                )
                for phase, anchor in anchors.items()
            },
        }

    result = {
        "schema_version": PHASE_STABILITY_SCHEMA,
        "market_identity": identity,
        "phases": summaries,
        "cross_phase_outcomes": cross_phase_outcomes,
        "limitations": [
            "three phases from one market do not establish cross-market stability",
            "displayed depth is public snapshot depth, not executable fill evidence",
            "spread and midpoint ranges exclude observations without both best sides",
            "polling gaps include request and network duration and are not latency measurements",
            "Binance noon-Eastern terms are incompatible with the Coinbase midnight-UTC QCRL signal",
            "the analysis does not establish queue position, fills, settlement, or profitability",
        ],
    }
    result["analysis_sha256"] = payload_hash(result)
    return result
