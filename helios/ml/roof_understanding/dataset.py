"""Strict RID2 data loading for multi-head semantic segmentation."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from helios.ml.roof_understanding.labels import validate_mask_values


def _read_split(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    names: list[str] = []
    for row in rows:
        if not row:
            continue
        candidate = Path(row[0].strip()).name
        if candidate.lower().endswith(".png"):
            names.append(candidate)
    if not names:
        raise ValueError(f"No PNG filenames found in RID2 split file {path}")
    return names


class RID2Dataset:
    """Return RGB image, roof-segment mask, superstructure mask and filename."""

    def __init__(self, root: str | Path, split: str = "training") -> None:
        import torch

        self._torch = torch
        self.root = Path(root)
        split_names = {
            "training": "training_split_512.csv",
            "test": "test_split_512.csv",
        }
        if split not in split_names:
            raise ValueError(f"split must be one of {sorted(split_names)}, got {split!r}")
        self.names = _read_split(self.root / split_names[split])
        self.images = self.root / "images"
        self.segment_masks = self.root / "masks" / "masks_segments"
        self.superstructure_masks = self.root / "masks" / "masks_superstructures"
        missing = [
            path
            for name in self.names
            for path in (
                self.images / name,
                self.segment_masks / name,
                self.superstructure_masks / name,
            )
            if not path.is_file()
        ]
        if missing:
            sample = ", ".join(str(path) for path in missing[:3])
            raise FileNotFoundError(
                f"RID2 split references {len(missing)} missing files; first: {sample}"
            )

    def __len__(self) -> int:
        return len(self.names)

    def __getitem__(self, index: int) -> dict[str, Any]:
        import numpy as np
        from PIL import Image

        name = self.names[index]
        image = np.asarray(Image.open(self.images / name).convert("RGB"), dtype=np.float32)
        segment = np.asarray(Image.open(self.segment_masks / name), dtype=np.int64)
        superstructure = np.asarray(
            Image.open(self.superstructure_masks / name), dtype=np.int64
        )
        validate_mask_values(set(np.unique(segment).tolist()), kind="segment")
        validate_mask_values(
            set(np.unique(superstructure).tolist()), kind="superstructure"
        )
        image_tensor = self._torch.from_numpy(image).permute(2, 0, 1).contiguous() / 255.0
        return {
            "image": image_tensor,
            "segment_mask": self._torch.from_numpy(segment.copy()).long(),
            "superstructure_mask": self._torch.from_numpy(superstructure.copy()).long(),
            "name": name,
        }
