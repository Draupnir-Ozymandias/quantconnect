"""Read-only Polymarket execution-truth contracts."""

from .contracts import (
    ContractError,
    MARKET_CONTRACT_SCHEMA,
    ORDER_BOOK_SCHEMA,
    normalize_market_contract,
    normalize_order_book,
)
from .acquisition import AcquisitionError, PublicPolymarketAcquirer
from .bundle import normalize_bundle, store_raw_bundle
from .discovery import normalize_discovery
from .binding import bind_signal_to_market

__all__ = [
    "ContractError",
    "AcquisitionError",
    "MARKET_CONTRACT_SCHEMA",
    "ORDER_BOOK_SCHEMA",
    "normalize_market_contract",
    "normalize_order_book",
    "normalize_bundle",
    "normalize_discovery",
    "bind_signal_to_market",
    "store_raw_bundle",
    "PublicPolymarketAcquirer",
]
