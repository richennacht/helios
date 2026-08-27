"""Stable identity helpers for source building records."""

from __future__ import annotations

import hashlib


def normalized_source_wkt(value: str) -> str:
    """Return a whitespace-stable representation for source-record hashing."""
    return " ".join(value.strip().split())


def source_record_digest(tile: str, plus_code: str, geometry_wkt: str) -> str:
    """Create a surrogate key when a source row has no stable identifier."""
    payload = "|".join((tile, plus_code, normalized_source_wkt(geometry_wkt)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def candidate_id(tile: str, plus_code: str, geometry_wkt: str) -> str:
    """Create a row-order-independent Helios candidate identifier."""
    return f"KHAR_{source_record_digest(tile, plus_code, geometry_wkt)[:16].upper()}"
