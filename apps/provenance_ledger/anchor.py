"""Merkle anchor helpers."""
from __future__ import annotations

import hashlib


def build_daily_merkle_root() -> str:
    """Return a deterministic placeholder merkle root."""

    return hashlib.sha256(b"merkle-root").hexdigest()


def anchor_to_chain(root: str, chain: str = "testnet") -> str:
    """Mock anchoring by hashing the root and chain name."""

    payload = f"{root}:{chain}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
