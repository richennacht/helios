"""Validate RID2 and compute reproducible pixel-frequency statistics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    import numpy as np
    from PIL import Image

    from helios.ml.roof_understanding.dataset import RID2Dataset
    from helios.ml.roof_understanding.labels import (
        NUM_RID2_CLASSES,
        RID2_LABEL_SCHEMA_VERSION,
        validate_mask_values,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report: dict[str, object] = {
        "dataset": "RID2 10.5281/zenodo.14062580",
        "label_schema": RID2_LABEL_SCHEMA_VERSION,
        "splits": {},
    }
    for split in ("training", "test"):
        dataset = RID2Dataset(args.data_root, split)
        segment_counts = np.zeros(NUM_RID2_CLASSES, dtype=np.int64)
        superstructure_counts = np.zeros(NUM_RID2_CLASSES, dtype=np.int64)
        shapes: set[tuple[int, int]] = set()
        for name in dataset.names:
            segment = np.asarray(Image.open(dataset.segment_masks / name), dtype=np.int64)
            superstructure = np.asarray(
                Image.open(dataset.superstructure_masks / name), dtype=np.int64
            )
            validate_mask_values(set(np.unique(segment).tolist()), kind="segment")
            validate_mask_values(
                set(np.unique(superstructure).tolist()), kind="superstructure"
            )
            shapes.add(segment.shape)
            segment_counts += np.bincount(
                segment.ravel(), minlength=NUM_RID2_CLASSES
            )
            superstructure_counts += np.bincount(
                superstructure.ravel(), minlength=NUM_RID2_CLASSES
            )
        report["splits"][split] = {
            "images": len(dataset),
            "mask_shapes": sorted([list(shape) for shape in shapes]),
            "segment_pixel_counts": segment_counts.tolist(),
            "superstructure_pixel_counts": superstructure_counts.tolist(),
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
