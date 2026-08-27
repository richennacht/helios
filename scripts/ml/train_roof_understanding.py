"""Train the reproducible RID2 multi-head roof-understanding baseline."""

from __future__ import annotations

import argparse
import json
import random
from datetime import UTC, datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, default=Path("models/weights/roof-understanding")
    )
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--base-channels", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--limit-train", type=int)
    parser.add_argument("--limit-test", type=int)
    parser.add_argument("--class-stats", type=Path)
    return parser.parse_args()


def main() -> None:
    import numpy as np
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, Subset

    from helios.ml.roof_understanding.dataset import RID2Dataset
    from helios.ml.roof_understanding.labels import RID2_LABEL_SCHEMA_VERSION
    from helios.ml.roof_understanding.metrics import (
        class_weights_from_counts,
        confusion_matrix,
        mean_iou,
    )
    from helios.ml.roof_understanding.model import build_model

    args = parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_data = RID2Dataset(args.data_root, "training")
    test_data = RID2Dataset(args.data_root, "test")
    if args.limit_train:
        train_data = Subset(train_data, range(min(args.limit_train, len(train_data))))
    if args.limit_test:
        test_data = Subset(test_data, range(min(args.limit_test, len(test_data))))
    train_loader = DataLoader(
        train_data, batch_size=args.batch_size, shuffle=True, num_workers=args.workers
    )
    test_loader = DataLoader(
        test_data, batch_size=args.batch_size, shuffle=False, num_workers=args.workers
    )

    model = build_model(args.base_channels).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    segment_weights = None
    superstructure_weights = None
    if args.class_stats:
        stats = json.loads(args.class_stats.read_text(encoding="utf-8"))
        training_stats = stats["splits"]["training"]
        segment_weights = torch.tensor(
            class_weights_from_counts(training_stats["segment_pixel_counts"]),
            dtype=torch.float32,
            device=device,
        )
        superstructure_weights = torch.tensor(
            class_weights_from_counts(training_stats["superstructure_pixel_counts"]),
            dtype=torch.float32,
            device=device,
        )
    segment_loss = nn.CrossEntropyLoss(weight=segment_weights)
    superstructure_loss = nn.CrossEntropyLoss(weight=superstructure_weights)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    history: list[dict[str, float | int]] = []
    best_score = -1.0

    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            images = batch["image"].to(device)
            segment = batch["segment_mask"].to(device)
            superstructure = batch["superstructure_mask"].to(device)
            optimizer.zero_grad(set_to_none=True)
            outputs = model(images)
            loss = segment_loss(outputs["segment_logits"], segment)
            loss += superstructure_loss(outputs["superstructure_logits"], superstructure)
            loss.backward()
            optimizer.step()
            train_loss += float(loss.item())

        model.eval()
        segment_matrix = torch.zeros((6, 6), dtype=torch.int64)
        superstructure_matrix = torch.zeros((6, 6), dtype=torch.int64)
        with torch.inference_mode():
            for batch in test_loader:
                outputs = model(batch["image"].to(device))
                segment_prediction = outputs["segment_logits"].argmax(1).cpu()
                superstructure_prediction = outputs["superstructure_logits"].argmax(1).cpu()
                segment_matrix += confusion_matrix(segment_prediction, batch["segment_mask"])
                superstructure_matrix += confusion_matrix(
                    superstructure_prediction, batch["superstructure_mask"]
                )
        segment_miou = mean_iou(segment_matrix)
        superstructure_miou = mean_iou(superstructure_matrix)
        mean_score = (segment_miou + superstructure_miou) / 2.0
        record = {
            "epoch": epoch,
            "train_loss": train_loss / max(len(train_loader), 1),
            "segment_miou_no_background": segment_miou,
            "superstructure_miou_no_background": superstructure_miou,
            "mean_miou_no_background": mean_score,
        }
        history.append(record)
        print(json.dumps(record))
        if mean_score > best_score:
            best_score = mean_score
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "base_channels": args.base_channels,
                    "label_schema": RID2_LABEL_SCHEMA_VERSION,
                    "epoch": epoch,
                    "metrics": record,
                },
                args.output_dir / "best.pt",
            )

    manifest = {
        "model_id": "helios-roof-understanding-rid2-unet-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "dataset": "RID2 10.5281/zenodo.14062580",
        "label_schema": RID2_LABEL_SCHEMA_VERSION,
        "seed": args.seed,
        "device": str(device),
        "arguments": vars(args)
        | {"data_root": str(args.data_root), "output_dir": str(args.output_dir)},
        "history": history,
        "best_mean_miou_no_background": best_score,
    }
    (args.output_dir / "training-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
