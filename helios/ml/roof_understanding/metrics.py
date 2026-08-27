"""Segmentation metrics with explicit handling of RID2 background."""

from __future__ import annotations


def class_weights_from_counts(counts: list[int], *, maximum: float = 20.0) -> list[float]:
    """Return normalized inverse-square-root weights for imbalanced RID2 masks."""

    import numpy as np

    values = np.asarray(counts, dtype=float)
    if values.shape != (6,) or (values < 0).any() or values.sum() <= 0:
        raise ValueError("counts must contain six non-negative class totals")
    present = values > 0
    weights = np.zeros_like(values)
    weights[present] = 1.0 / np.sqrt(values[present])
    weights[present] /= weights[present].mean()
    weights = np.clip(weights, 0.0, maximum)
    return weights.tolist()


def confusion_matrix(prediction, target, num_classes: int = 6):
    import torch

    valid = (target >= 0) & (target < num_classes)
    bins = target[valid] * num_classes + prediction[valid]
    return torch.bincount(bins, minlength=num_classes**2).reshape(num_classes, num_classes)


def mean_iou(matrix, *, exclude_class: int | None = 5) -> float:
    diagonal = matrix.diag().float()
    union = matrix.sum(0).float() + matrix.sum(1).float() - diagonal
    valid = union > 0
    if exclude_class is not None:
        valid[exclude_class] = False
    if not valid.any():
        return 0.0
    return float((diagonal[valid] / union[valid]).mean().item())
