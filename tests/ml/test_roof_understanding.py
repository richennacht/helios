import pytest

torch = pytest.importorskip("torch")

from helios.ml.roof_understanding.labels import (  # noqa: E402
    RID2_BACKGROUND_ID,
    validate_mask_values,
)
from helios.ml.roof_understanding.metrics import (  # noqa: E402
    class_weights_from_counts,
    confusion_matrix,
    mean_iou,
)
from helios.ml.roof_understanding.model import build_model  # noqa: E402


def test_rid2_background_value_is_frozen() -> None:
    assert RID2_BACKGROUND_ID == 5
    validate_mask_values({0, 1, 2, 3, 4, 5}, kind="segment")
    with pytest.raises(ValueError, match="unexpected values"):
        validate_mask_values({6}, kind="segment")


def test_model_preserves_spatial_shape_for_both_heads() -> None:
    model = build_model(base_channels=4)
    outputs = model(torch.rand(2, 3, 64, 64))
    assert outputs["segment_logits"].shape == (2, 6, 64, 64)
    assert outputs["superstructure_logits"].shape == (2, 6, 64, 64)


def test_mean_iou_excludes_background() -> None:
    target = torch.tensor([[0, 0, 5, 5]])
    prediction = torch.tensor([[0, 1, 5, 5]])
    matrix = confusion_matrix(prediction, target)
    assert mean_iou(matrix) == pytest.approx(0.25)


def test_class_weights_upweight_rare_obstructions() -> None:
    weights = class_weights_from_counts([100, 25, 4, 1, 16, 10_000])
    assert weights[3] > weights[2] > weights[1] > weights[0] > weights[5]
