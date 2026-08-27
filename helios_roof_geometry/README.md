# Helios Roof-Plane & Geometry Model

Production-ready standalone Python geometry inference module for the **Helios Solar Scouting Platform** (referencing [helios-solar-scouting.vercel.app](https://helios-solar-scouting.vercel.app/) and [github.com/richennacht/helios](https://github.com/richennacht/helios)).

---

## 1. Role and Mathematical Formulation

The **Roof-Plane & Geometry Model** treats rooftop surfaces as 3D physical planes. It takes dual-view optical patches or DSM (Digital Surface Model) elevation crops and polygon boundaries from Person 1 (or standalone bounding boxes), predicts roof type classification and pitch angle $\theta$, and converts 2D horizontal footprint area to true 3D surface area:

$$A_{\text{surface}} = \frac{A_{\text{horizontal}}}{\cos\theta}$$

where $\theta \in [0^\circ, 45^\circ]$ is the pitch angle in degrees.

---

## 2. Dataset Provenance & Sources

Based on the datasets identified in `richennacht/helios` and the Helios live platform:

| Modality | Source / Dataset | Role in Helios |
|---|---|---|
| **Elevation / DSM** | Copernicus GLO-30 DEM (`kharghar_terrain.tif`) | Terrain context, base elevation, and macro slope |
| **Elevation / DSM** | AWS Terrarium Elevation Tiles (`terrarium/{z}/{x}/{y}.png`) | High-resolution raster DEM tiles for 3D elevation maps |
| **Elevation / Height**| Google Open Buildings 3D Temporal (2016–2023) | Annual building presence and heights |
| **Elevation / Height**| DLR WSF3D (World Settlement Footprint 3D) | 90m mean building height, volume, and area |
| **Optical Imagery** | RID2 (TUM, DOI: `10.5281/zenodo.14062580`) | 0.08m ground-resolution aerial tiles with orientation & superstructure masks |
| **Optical Imagery** | Esri World Imagery & Sentinel-2 Cloudless | High-resolution satellite and aerial optical imagery |
| **Building Vectors** | Google Open Buildings v3 & Overture Maps Buildings | Fused building footprints and candidate polygons |

---

## 3. Architecture Overview

### Multi-Task ResNet-18 (`RoofGeometryNet`)
- **Input**: 4-channel tensor (RGB optical imagery + normalized DSM elevation crop) or single-channel DSM / 3-channel RGB.
- **Backbone**: ResNet-18 feature extractor.
- **Head 1 (Classification)**: 4-class logits for `['flat', 'gable', 'hip', 'single-slant']`.
- **Head 2 (Pitch Regression)**: Pitch angle $\theta \in [0^\circ, 45^\circ]$ with Sigmoid scaling.
- **Head 3 (Azimuth Circular Regression)**: Normalized $(\sin\phi, \cos\phi)$ vectors yielding continuous compass bearing $\phi \in [0^\circ, 360^\circ]$.

---

## 4. Standalone Module API (`geometry_engine.py`)

### Python API

```python
from geometry_engine import GeometryEngine, calculate_surface_area

# 1. Standalone 3D surface area calculation
polygon_geojson = {
    "type": "Polygon",
    "coordinates": [[[73.0685, 19.0450], [73.0690, 19.0450], [73.0690, 19.0455], [73.0685, 19.0455], [73.0685, 19.0450]]]
}
surface_area_sqm = calculate_surface_area(polygon_geojson, pitch_angle=18.5)

# 2. End-to-end model inference
engine = GeometryEngine(model_weights_path="models/roof_geometry_resnet18.pt")
result = engine.predict(elevation_or_image_crop=crop_array, polygon_geojson=polygon_geojson)

print(result)
```

### JSON Output Contract

```json
{
  "pitch_deg": 15.26,
  "azimuth_deg": 182.09,
  "surface_area_sqm": 3020.08,
  "roof_type": "gable",
  "horizontal_area_sqm": 2913.62,
  "confidence": 0.9979
}
```

---

## 5. Execution & Testing

### Running Tests
```powershell
& .venv\Scripts\pytest.exe test_geometry_engine.py -v
```

### Running Model Training
```powershell
& .venv\Scripts\python.exe train_geometry_model.py --epochs 15 --samples 1200 --batch-size 16 --output-dir models
```

### Running CLI Inference
```powershell
& .venv\Scripts\python.exe geometry_engine.py --sample-kharghar --weights models/roof_geometry_resnet18.pt
```
