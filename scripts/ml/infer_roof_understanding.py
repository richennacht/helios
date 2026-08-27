"""Run a trained Helios roof-understanding checkpoint on one RGB image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    import numpy as np
    import torch
    from PIL import Image

    from helios.ml.roof_understanding.labels import (
        RID2_BACKGROUND_ID,
        RID2_LABEL_SCHEMA_VERSION,
    )
    from helios.ml.roof_understanding.model import build_model

    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    if checkpoint["label_schema"] != RID2_LABEL_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported label schema {checkpoint['label_schema']!r}; "
            f"expected {RID2_LABEL_SCHEMA_VERSION!r}"
        )
    model = build_model(checkpoint["base_channels"]).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    model.eval()
    image = Image.open(args.image).convert("RGB")
    if image.size != (512, 512):
        raise ValueError(f"RID2 baseline expects 512x512 input, got {image.size}")
    array = np.asarray(image, dtype=np.float32)
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0) / 255.0
    with torch.inference_mode():
        output = model(tensor.to(device))
    segment = output["segment_logits"].argmax(1)[0].byte().cpu().numpy()
    superstructure = output["superstructure_logits"].argmax(1)[0].byte().cpu().numpy()
    roof_pixels = int((segment != RID2_BACKGROUND_ID).sum())
    blocked_pixels = int(
        ((superstructure != RID2_BACKGROUND_ID) & (segment != RID2_BACKGROUND_ID)).sum()
    )
    usable_fraction = max(roof_pixels - blocked_pixels, 0) / max(roof_pixels, 1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    Image.fromarray(segment).save(args.output_dir / "roof-segments.png")
    Image.fromarray(superstructure).save(args.output_dir / "roof-superstructures.png")
    summary = {
        "model_id": "helios-roof-understanding-rid2-unet-v1",
        "label_schema": RID2_LABEL_SCHEMA_VERSION,
        "source_image": str(args.image),
        "roof_pixels": roof_pixels,
        "detected_superstructure_pixels_on_roof": blocked_pixels,
        "visual_clear_fraction_before_setbacks_and_shading": usable_fraction,
        "limitations": [
            "RID2 does not label tree overhang or shadow as a superstructure.",
            "This fraction excludes neither access corridors nor regulatory setbacks.",
            "Indian-domain validation is required before production promotion.",
        ],
    }
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
