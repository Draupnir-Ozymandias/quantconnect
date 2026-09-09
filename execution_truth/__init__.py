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
from .signal_adapter import (
    materialize_boundary_signal,
    normalize_source_bar,
    normalize_source_contract,
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
    "materialize_boundary_signal",
    "normalize_source_bar",
    "normalize_source_contract",
    "promote_raw_evidence",
    "store_raw_bundle",
    "store_raw_book_sequence",
    "store_raw_discovery",
    "store_raw_slug_resolution",
    "verify_live_evidence_inventory",
    "PublicPolymarketAcquirer",
]
