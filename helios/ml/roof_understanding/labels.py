"""Frozen RID2 label semantics.

RID2 assigns background the largest value (5), unlike many segmentation
datasets. Keeping the source encoding avoids accidental label corruption.
"""

from __future__ import annotations

RID2_LABEL_SCHEMA_VERSION = "rid2.simple-v1"
RID2_BACKGROUND_ID = 5

ROOF_SEGMENT_CLASSES = {
    0: "north",
    1: "east",
    2: "south",
    3: "west",
    4: "flat",
    5: "background",
}

ROOF_SUPERSTRUCTURE_CLASSES = {
    0: "pv_module",
    1: "dormer",
    2: "window",
    3: "balcony",
    4: "other",
    5: "background",
}

NUM_RID2_CLASSES = 6


def validate_mask_values(values: set[int], *, kind: str) -> None:
    allowed = set(range(NUM_RID2_CLASSES))
    unexpected = values - allowed
    if unexpected:
        raise ValueError(f"RID2 {kind} mask contains unexpected values: {sorted(unexpected)}")
