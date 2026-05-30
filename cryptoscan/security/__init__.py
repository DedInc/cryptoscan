"""Security utilities for CryptoScan (backward-compat shim).

The URL validation logic lives in :mod:`security.urls` and the
masking/sanitization logic lives in :mod:`security.masking`.
This module re-exports the public surface so that
``from cryptoscan.security import ...`` continues to work.
"""

from __future__ import annotations

from .masking import (
    MIN_ADDRESS_LENGTH_FOR_MASKING,
    mask_address,
    mask_transaction_id,
    mask_url,
    sanitize_log_data,
)
from .urls import VALID_RPC_SCHEMES, validate_rpc_url, validate_ws_url

__all__ = [
    "validate_rpc_url",
    "validate_ws_url",
    "mask_address",
    "mask_transaction_id",
    "mask_url",
    "VALID_RPC_SCHEMES",
    "MIN_ADDRESS_LENGTH_FOR_MASKING",
    "sanitize_log_data",
]
