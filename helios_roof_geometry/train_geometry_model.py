"""Training pipeline for Helios Roof Geometry ResNet-18 Model."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import random
import time

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split

from dataset import RoofGeometryDataset, ROOF_CLASSES
from geometry_engine import RoofGeometryNet


def parse_args():
    parser = argparse.ArgumentParser(description="Train Roof Geometry ResNet-18 Model")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=1e-3, help="Learning rate")
    parser.add_argument("--samples", type=int, default=1200, help="Total synthetic dataset samples")
    parser.add_argument("--in-channels", type=int, default=4, help="Input channels (4: RGB+DSM)")
    parser.add_argument("--output-dir", type=str, default="models", help="Output weights directory")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    return parser.parse_args()


def compute_azimuth_error(pred_sin_cos: torch.Tensor, target_deg: torch.Tensor) -> float:
    """Compute mean absolute angular error in degrees on the circle [0, 360)."""
    sin_p = pred_sin_cos[:, 0].detach().cpu().numpy()
    cos_p = pred_sin_cos[:, 1].detach().cpu().numpy()
    pred_deg = (np.degrees(np.arctan2(sin_p, cos_p)) + 360.0) % 360.0
    targ_deg = target_deg.detach().cpu().numpy()
    
    # Angular difference on circle
    diff = np.abs(pred_deg - targ_deg)
    diff = np.minimum(diff, 360.0 - diff)
    return float(np.mean(diff))


def main():
    args = parse_args()
    
    # Set seeds
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
        
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create dataset
    full_dataset = RoofGeometryDataset(
        num_samples=args.samples,
        patch_size=128,
        in_channels=args.in_channels,
        seed=args.seed
    )
    
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size],
        generator=torch.Generator().manual_seed(args.seed)
    )
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)
    
    # Model
    model = RoofGeometryNet(in_channels=args.in_channels, num_classes=4).to(device)
    
    # Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    # Losses
    criterion_cls = nn.CrossEntropyLoss()
    criterion_pitch = nn.SmoothL1Loss()
    criterion_azimuth = nn.MSELoss()
    
    # Weights for multi-task loss
    w_cls = 1.0
    w_pitch = 0.2
    w_azimuth = 2.0
    
    best_val_loss = float("inf")
    best_metrics = {}
    history = []
    
    start_time = time.time()
    print(f"Starting training for {args.epochs} epochs on {train_size} train / {val_size} val samples...")
    
    for epoch in range(1, args.epochs + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for batch in train_loader:
            inputs = batch["input"].to(device)
            target_cls = batch["class_idx"].to(device)
            target_pitch = batch["pitch_deg"].to(device)
            target_az_sc = batch["azimuth_sin_cos"].to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            
            loss_cls = criterion_cls(outputs["class_logits"], target_cls)
            loss_pitch = criterion_pitch(outputs["pitch_deg"], target_pitch)
            loss_az = criterion_azimuth(outputs["azimuth_sin_cos"], target_az_sc)
            
            total_loss = w_cls * loss_cls + w_pitch * loss_pitch + w_azimuth * loss_az
            total_loss.backward()
            optimizer.step()
            
            train_loss += total_loss.item() * inputs.size(0)
            preds = torch.argmax(outputs["class_logits"], dim=1)
            train_correct += (preds == target_cls).sum().item()
            train_total += inputs.size(0)
            
        scheduler.step()
        train_epoch_loss = train_loss / train_total
        train_acc = (train_correct / train_total) * 100.0
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        pitch_errors = []
        azimuth_errors = []
        
        with torch.no_grad():
            for batch in val_loader:
                inputs = batch["input"].to(device)
                target_cls = batch["class_idx"].to(device)
                target_pitch = batch["pitch_deg"].to(device)
                target_az_sc = batch["azimuth_sin_cos"].to(device)
                target_az_deg = batch["azimuth_deg"].to(device)
                
                outputs = model(inputs)
                
                loss_cls = criterion_cls(outputs["class_logits"], target_cls)
                loss_pitch = criterion_pitch(outputs["pitch_deg"], target_pitch)
                loss_az = criterion_azimuth(outputs["azimuth_sin_cos"], target_az_sc)
                total_loss = w_cls * loss_cls + w_pitch * loss_pitch + w_azimuth * loss_az
                
                val_loss += total_loss.item() * inputs.size(0)
                preds = torch.argmax(outputs["class_logits"], dim=1)
                val_correct += (preds == target_cls).sum().item()
                val_total += inputs.size(0)
                
                p_err = torch.abs(outputs["pitch_deg"] - target_pitch).cpu().numpy()
                pitch_errors.extend(p_err.tolist())
                az_err = compute_azimuth_error(outputs["azimuth_sin_cos"], target_az_deg)
                azimuth_errors.append(az_err)
                
        val_epoch_loss = val_loss / val_total
        val_acc = (val_correct / val_total) * 100.0
        val_pitch_mae = float(np.mean(pitch_errors))
        val_az_mae = float(np.mean(azimuth_errors))
        
        record = {
            "epoch": epoch,
            "train_loss": round(train_epoch_loss, 4),
            "train_acc_pct": round(train_acc, 2),
            "val_loss": round(val_epoch_loss, 4),
            "val_acc_pct": round(val_acc, 2),
            "val_pitch_mae_deg": round(val_pitch_mae, 2),
            "val_azimuth_mae_deg": round(val_az_mae, 2),
        }
        history.append(record)
        
        print(
            f"Epoch [{epoch:02d}/{args.epochs:02d}] "
            f"Train Loss: {train_epoch_loss:.4f} (Acc: {train_acc:.1f}%) | "
            f"Val Loss: {val_epoch_loss:.4f} (Acc: {val_acc:.1f}%, Pitch MAE: {val_pitch_mae:.2f}°, Azimuth MAE: {val_az_mae:.2f}°)"
        )
        
        if val_epoch_loss < best_val_loss:
            best_val_loss = val_epoch_loss
            best_metrics = record
            save_path = output_dir / "roof_geometry_resnet18.pt"
            torch.save({
                "epoch": epoch,
                "state_dict": model.state_dict(),
                "in_channels": args.in_channels,
                "classes": ROOF_CLASSES,
                "metrics": record,
            }, save_path)
            
    elapsed = time.time() - start_time
    print(f"\nTraining completed in {elapsed:.1f}s.")
    print(f"Best model saved to {output_dir / 'roof_geometry_resnet18.pt'}")
    print(f"Best Metrics: {best_metrics}")
    
    # Save training report
    summary = {
        "model_architecture": "ResNet-18 Multi-Task",
        "num_classes": 4,
        "classes": ROOF_CLASSES,
        "pitch_range_deg": [0.0, 45.0],
        "azimuth_range_deg": [0.0, 360.0],
        "training_time_sec": round(elapsed, 2),
        "best_epoch": best_metrics.get("epoch", args.epochs),
        "best_val_accuracy_pct": best_metrics.get("val_acc_pct", 0.0),
        "best_val_pitch_mae_deg": best_metrics.get("val_pitch_mae_deg", 0.0),
        "best_val_azimuth_mae_deg": best_metrics.get("val_azimuth_mae_deg", 0.0),
        "history": history
    }
    with open(output_dir / "training_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


if __name__ == "__main__":
    main()
