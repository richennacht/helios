"""Helios Roof-Plane & Geometry Engine.

Standalone module for roof geometry inference and 3D surface area calculation.
Treats the roof as a 3D surface and computes:
- Roof plane classification ([flat, gable, hip, single-slant])
- Pitch angle (theta in degrees, 0 to 45 deg)
- Orientation (azimuth in degrees, 0 to 360 deg)
- Real 3D surface area from 2D polygon: A_surface = A_horizontal / cos(theta)

Returns JSON:
{'pitch_deg': float, 'azimuth_deg': float, 'surface_area_sqm': float}
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Optional, Union, Tuple, List

import numpy as np
import shapely
import shapely.geometry
import shapely.ops
import geopandas as gpd
import pyproj
import torch
import torch.nn as nn
import torchvision.models as models

ROOF_CLASSES = ["flat", "gable", "hip", "single-slant"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(ROOF_CLASSES)}
IDX_TO_CLASS = {idx: name for idx, name in enumerate(ROOF_CLASSES)}


def calculate_surface_area(
    polygon_geojson: Union[str, Dict[str, Any], shapely.geometry.base.BaseGeometry, gpd.GeoDataFrame, gpd.GeoSeries],
    pitch_angle: float,
    default_crs: Optional[str] = "EPSG:4326",
    target_metric_crs: Optional[str] = None,
) -> float:
    """Calculate real 3D rooftop surface area from 2D polygon geometry and pitch angle.
    
    Formula:
        A_surface = A_horizontal / cos(theta)
        
    Args:
        polygon_geojson: GeoJSON geometry dict, GeoJSON string, Shapely polygon, or GeoDataFrame/GeoSeries
        pitch_angle: Pitch angle theta in degrees (0 to 45 deg)
        default_crs: Source CRS if geometry is in geographic coordinates (default: EPSG:4326)
        target_metric_crs: Projected metric CRS (e.g., 'EPSG:32643' for UTM 43N / Mumbai).
                           If None, auto-computes optimal UTM zone based on geometry centroid.
                           
    Returns:
        float: Real 3D surface area in square meters (m^2)
    """
    src_crs = default_crs
    if isinstance(polygon_geojson, (gpd.GeoDataFrame, gpd.GeoSeries)):
        if polygon_geojson.empty:
            return 0.0
        geom = polygon_geojson.geometry.iloc[0]
        if polygon_geojson.crs:
            src_crs = polygon_geojson.crs.to_string()
    elif isinstance(polygon_geojson, str):
        data = json.loads(polygon_geojson)
        if data.get("type") == "FeatureCollection":
            geom = shapely.geometry.shape(data["features"][0]["geometry"])
        elif data.get("type") == "Feature":
            geom = shapely.geometry.shape(data["geometry"])
        elif "coordinates" in data:
            geom = shapely.geometry.shape(data)
        else:
            raise ValueError(f"Invalid GeoJSON string format: {polygon_geojson[:100]}")
    elif isinstance(polygon_geojson, dict):
        if polygon_geojson.get("type") == "FeatureCollection":
            geom = shapely.geometry.shape(polygon_geojson["features"][0]["geometry"])
        elif polygon_geojson.get("type") == "Feature":
            geom = shapely.geometry.shape(polygon_geojson["geometry"])
        elif "coordinates" in polygon_geojson:
            geom = shapely.geometry.shape(polygon_geojson)
        else:
            raise ValueError("Invalid GeoJSON dict structure")
    elif isinstance(polygon_geojson, shapely.geometry.base.BaseGeometry):
        geom = polygon_geojson
    else:
        raise TypeError(f"Unsupported geometry type: {type(polygon_geojson)}")

    if not geom.is_valid:
        geom = shapely.make_valid(geom)
        
    crs_obj = None
    if src_crs:
        try:
            crs_obj = pyproj.CRS(src_crs)
        except Exception:
            crs_obj = None

    if crs_obj is not None:
        is_geographic = crs_obj.is_geographic
    else:
        bounds = geom.bounds
        is_geographic = (abs(bounds[0]) <= 180 and abs(bounds[2]) <= 180 and abs(bounds[1]) <= 90 and abs(bounds[3]) <= 90)

    if is_geographic:
        if target_metric_crs:
            proj_crs = target_metric_crs
        else:
            centroid = geom.centroid
            lon, lat = centroid.x, centroid.y
            utm_zone = int(math.floor((lon + 180) / 6) + 1)
            hemisphere = "north" if lat >= 0 else "south"
            epsg_code = 32600 + utm_zone if hemisphere == "north" else 32700 + utm_zone
            proj_crs = f"EPSG:{epsg_code}"
            
        transformer = pyproj.Transformer.from_crs(src_crs or "EPSG:4326", proj_crs, always_xy=True)
        geom_projected = shapely.ops.transform(transformer.transform, geom)
        horizontal_area = float(geom_projected.area)
    else:
        horizontal_area = float(geom.area)
        
    # Clamp pitch angle between 0 and 45 degrees
    pitch_clamped = max(0.0, min(float(pitch_angle), 45.0))
    pitch_rad = math.radians(pitch_clamped)
    
    cos_theta = math.cos(pitch_rad)
    if cos_theta <= 1e-6:
        cos_theta = 1e-6
        
    surface_area = horizontal_area / cos_theta
    return float(surface_area)


class RoofGeometryNet(nn.Module):
    """Multi-task ResNet-18 for roof classification, pitch regression, and azimuth estimation."""
    
    def __init__(self, in_channels: int = 4, num_classes: int = 4, pretrained: bool = False):
        super().__init__()
        self.in_channels = in_channels
        self.num_classes = num_classes
        
        # Base ResNet-18
        backbone = models.resnet18(weights=models.ResNet18_Weights.DEFAULT if pretrained else None)
        
        if in_channels != 3:
            self.conv1 = nn.Conv2d(
                in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False
            )
            if pretrained and in_channels == 4:
                with torch.no_grad():
                    self.conv1.weight[:, :3, :, :] = backbone.conv1.weight
                    self.conv1.weight[:, 3:, :, :] = torch.mean(backbone.conv1.weight, dim=1, keepdim=True)
        else:
            self.conv1 = backbone.conv1
            
        self.bn1 = backbone.bn1
        self.relu = backbone.relu
        self.maxpool = backbone.maxpool
        self.layer1 = backbone.layer1
        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.layer4 = backbone.layer4
        self.avgpool = backbone.avgpool
        
        in_features = backbone.fc.in_features  # 512
        
        # Task 1: Classification Head (flat, gable, hip, single-slant)
        self.cls_head = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
        
        # Task 2: Pitch Angle Regression Head (0 to 45 degrees)
        self.pitch_head = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
            nn.Sigmoid()  # outputs in [0, 1] scaled by 45.0
        )
        
        # Task 3: Azimuth Circular Head (sin, cos) -> [0, 360 deg]
        self.azimuth_head = nn.Sequential(
            nn.Linear(in_features, 128),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(128, 2)  # [sin(phi), cos(phi)]
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        features = torch.flatten(x, 1)

        # Classification logits
        cls_logits = self.cls_head(features)
        
        # Pitch angle: [0, 1] * 45.0 degrees
        pitch_norm = self.pitch_head(features)
        pitch_deg = pitch_norm * 45.0
        
        # Azimuth angle sin/cos normalized
        azimuth_raw = self.azimuth_head(features)
        azimuth_sin_cos = nn.functional.normalize(azimuth_raw, p=2, dim=-1)
        
        return {
            "class_logits": cls_logits,
            "pitch_deg": pitch_deg.squeeze(-1),
            "azimuth_sin_cos": azimuth_sin_cos,
        }


class GeometryEngine:
    """Standalone Geometry Engine providing inference and 3D surface area calculation."""
    
    def __init__(
        self,
        model_weights_path: Optional[Union[str, Path]] = None,
        in_channels: int = 4,
        device: Optional[str] = None,
    ):
        if device is None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
            
        self.model = RoofGeometryNet(in_channels=in_channels, num_classes=4)
        self.in_channels = in_channels
        
        if model_weights_path and Path(model_weights_path).exists():
            checkpoint = torch.load(model_weights_path, map_location=self.device)
            if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
                self.model.load_state_dict(checkpoint["state_dict"])
            elif isinstance(checkpoint, dict):
                self.model.load_state_dict(checkpoint)
            self.model.eval()
        else:
            self.model.eval()
            
        self.model.to(self.device)

    def predict(
        self,
        elevation_or_image_crop: Optional[Union[np.ndarray, torch.Tensor]] = None,
        polygon_geojson: Optional[Union[str, Dict[str, Any], shapely.geometry.base.BaseGeometry]] = None,
        default_crs: str = "EPSG:4326",
    ) -> Dict[str, Any]:
        """Predict roof geometry properties and compute 3D surface area.
        
        Returns:
            JSON-serializable dict:
            {
                'pitch_deg': float,
                'azimuth_deg': float,
                'surface_area_sqm': float,
                'roof_type': str,
                'horizontal_area_sqm': float,
                'confidence': float
            }
        """
        pitch_deg = 0.0
        azimuth_deg = 0.0
        roof_type = "flat"
        confidence = 0.85
        
        if elevation_or_image_crop is not None:
            if isinstance(elevation_or_image_crop, np.ndarray):
                arr = elevation_or_image_crop
                if arr.ndim == 2:
                    arr_norm = (arr - np.mean(arr)) / (np.std(arr) + 1e-5)
                    if self.in_channels == 1:
                        tensor = torch.from_numpy(arr_norm).unsqueeze(0).unsqueeze(0).float()
                    elif self.in_channels == 4:
                        rgb = np.zeros((3, arr.shape[0], arr.shape[1]), dtype=np.float32)
                        dsm = np.expand_dims(arr_norm, 0).astype(np.float32)
                        tensor = torch.from_numpy(np.concatenate([rgb, dsm], axis=0)).unsqueeze(0).float()
                    else:
                        tensor = torch.from_numpy(arr_norm).repeat(self.in_channels, 1, 1).unsqueeze(0).float()
                elif arr.ndim == 3:
                    if arr.shape[2] in (1, 3, 4):
                        arr = np.transpose(arr, (2, 0, 1))
                    tensor = torch.from_numpy(arr).unsqueeze(0).float()
                elif arr.ndim == 4:
                    tensor = torch.from_numpy(arr).float()
                else:
                    raise ValueError(f"Invalid array shape: {arr.shape}")
            elif isinstance(elevation_or_image_crop, torch.Tensor):
                tensor = elevation_or_image_crop
                if tensor.ndim == 2:
                    tensor = tensor.unsqueeze(0).unsqueeze(0)
                elif tensor.ndim == 3:
                    tensor = tensor.unsqueeze(0)
            else:
                raise TypeError("Input must be numpy array or torch Tensor")

            tensor = tensor.to(self.device)
            with torch.no_grad():
                out = self.model(tensor)
                
                probs = torch.softmax(out["class_logits"], dim=-1)[0]
                class_idx = int(torch.argmax(probs).item())
                roof_type = IDX_TO_CLASS.get(class_idx, "flat")
                confidence = float(probs[class_idx].item())
                
                pitch_deg = float(out["pitch_deg"][0].item())
                if roof_type == "flat":
                    pitch_deg = min(pitch_deg, 3.0)
                    
                sin_val = float(out["azimuth_sin_cos"][0, 0].item())
                cos_val = float(out["azimuth_sin_cos"][0, 1].item())
                azimuth_rad = math.atan2(sin_val, cos_val)
                azimuth_deg = float((math.degrees(azimuth_rad) + 360.0) % 360.0)

        horizontal_area = 0.0
        surface_area = 0.0
        if polygon_geojson is not None:
            surface_area = calculate_surface_area(polygon_geojson, pitch_angle=pitch_deg, default_crs=default_crs)
            horizontal_area = surface_area * math.cos(math.radians(pitch_deg))

        result = {
            "pitch_deg": round(pitch_deg, 2),
            "azimuth_deg": round(azimuth_deg, 2),
            "surface_area_sqm": round(surface_area, 2),
            "roof_type": roof_type,
            "horizontal_area_sqm": round(horizontal_area, 2),
            "confidence": round(confidence, 4),
        }
        return result


def main():
    parser = argparse.ArgumentParser(description="Helios Roof Geometry Inference Engine")
    parser.add_argument("--weights", type=str, default="models/roof_geometry_resnet18.pt", help="Model weights path")
    parser.add_argument("--pitch", type=float, default=15.0, help="Manual pitch angle in degrees")
    parser.add_argument("--sample-kharghar", action="store_true", help="Run sample inference on Kharghar candidate building")
    args = parser.parse_args()

    engine = GeometryEngine(model_weights_path=args.weights if Path(args.weights).exists() else None)
    
    sample_kharghar_polygon = {
        "type": "Polygon",
        "coordinates": [[
            [73.0685, 19.0450],
            [73.0690, 19.0450],
            [73.0690, 19.0455],
            [73.0685, 19.0455],
            [73.0685, 19.0450]
        ]]
    }
    
    from dataset import generate_synthetic_roof_patch
    dsm, rgb = generate_synthetic_roof_patch(roof_type="gable", pitch_deg=args.pitch, azimuth_deg=135.0)
    dsm_norm = (dsm - np.mean(dsm)) / (np.std(dsm) + 1e-5)
    composite = np.concatenate([np.transpose(rgb, (2, 0, 1)), np.expand_dims(dsm_norm, 0)], axis=0)
    
    output = engine.predict(elevation_or_image_crop=composite, polygon_geojson=sample_kharghar_polygon)
    
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
