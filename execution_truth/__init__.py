"""Read-only Polymarket execution-truth contracts."""

from .contracts import (
    ContractError,
    MARKET_CONTRACT_SCHEMA,
    ORDER_BOOK_SCHEMA,
    normalize_market_contract,
    normalize_order_book,
)
from .acquisition import AcquisitionError, PublicPolymarketAcquirer
from .bundle import (
    normalize_bundle,
    promote_raw_evidence,
    store_raw_bundle,
    store_raw_book_sequence,
    store_raw_discovery,
    store_raw_slug_resolution,
    store_raw_settlement,
    verify_live_evidence_inventory,
)
from .discovery import (
    normalize_discovery,
    verify_raw_discovery,
    verify_raw_slug_resolution,
)
from .book_sequence import normalize_book_sequence
from .binding import bind_signal_to_market
from .taker_replay import replay_taker_buy
from .latency_sensitivity import evaluate_latency_sensitivity
from .latency_batch import evaluate_latency_phase_batch
from .phase_stability import analyze_phase_sequences
from .cross_market_phase import analyze_cross_market_phases
from .capture_protocol import (
    capture_protocol_status,
    execute_protocol_capture,
    load_capture_state,
    validate_capture_protocol,
)
from .signal_adapter import (
    materialize_boundary_signal,
    normalize_source_bar,
    normalize_source_contract,
)
from .settlement import (
    normalize_settlement,
    reconcile_settlement,
    reconcile_settlement_cohort,
)

__all__ = [
    "ContractError",
    "AcquisitionError",
    "MARKET_CONTRACT_SCHEMA",
    "ORDER_BOOK_SCHEMA",
    "normalize_market_contract",
    "normalize_order_book",
    "normalize_bundle",
    "normalize_book_sequence",
    "normalize_discovery",
    "verify_raw_discovery",
    "verify_raw_slug_resolution",
    "bind_signal_to_market",
    "replay_taker_buy",
    "evaluate_latency_sensitivity",
    "evaluate_latency_phase_batch",
    "analyze_phase_sequences",
    "analyze_cross_market_phases",
    "capture_protocol_status",
    "execute_protocol_capture",
    "load_capture_state",
    "validate_capture_protocol",
    "materialize_boundary_signal",
    "normalize_source_bar",
    "normalize_source_contract",
    "promote_raw_evidence",
    "store_raw_bundle",
    "store_raw_book_sequence",
    "store_raw_discovery",
    "store_raw_slug_resolution",
    "store_raw_settlement",
    "verify_live_evidence_inventory",
    "PublicPolymarketAcquirer",
    "normalize_settlement",
    "reconcile_settlement",
    "reconcile_settlement_cohort",
]
