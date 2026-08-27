# RID2 roof-understanding baseline

## Scope

The first Helios model produces two semantic maps from a 512 x 512 RGB aerial
tile:

1. roof segment orientation: north, east, south, west, flat, background;
2. roof superstructure: PV module, dormer, window, balcony, other, background.

The shared-encoder, two-head U-Net is a reproducible baseline. It is not yet a
promoted production model. Promotion requires held-out metrics, Kharghar domain
validation and a comparison with the fixed usable-area baseline.

## Dataset contract

- Dataset: RID2, DOI `10.5281/zenodo.14062580`.
- Source imagery: Beeldmateriaal Nederland, CC BY 4.0.
- Image resolution: 0.08 m; tile size: 512 x 512.
- Use the supplied `training_split_512.csv` and `test_split_512.csv`.
- Preserve source mask values. Background is value `5`, not `0`.
- No rotations or flips are allowed unless orientation labels are remapped.

## Training

```powershell
python scripts/ml/train_roof_understanding.py `
  --data-root data/raw/rid2/dataset `
  --class-stats data/processed/rid2-audit.json `
  --output-dir models/weights/roof-understanding/rid2-unet-v1
```

Generate the class statistics first with `scripts/ml/audit_rid2.py`. The
training loss applies capped inverse-square-root weights because roof
superstructures occupy far fewer pixels than background.

For a pipeline smoke test, add `--epochs 1 --limit-train 8 --limit-test 4`.

## Promotion gates

- report per-class IoU and macro mIoU without background;
- demonstrate obstruction-area error, not pixel accuracy alone;
- validate on separately sourced Indian imagery;
- retain an `uncertain` output for imagery below the required ground resolution;
- show improvement in panel-count error over the fixed 70% usable-area baseline;
- keep structural suitability, legal clearances and final engineering outside the model claim.
