"""Roof geometry dataset generator and PyTorch Dataset for Helios.

Supports multi-modal inputs:
- 1-channel DSM / elevation crops
- 3-channel RGB optical imagery
- 4-channel RGB + DSM composite patches

Labels:
- Roof Class: ['flat', 'gable', 'hip', 'single-slant'] (indices 0, 1, 2, 3)
- Pitch Angle (theta): [0.0, 45.0] degrees
- Azimuth Angle (phi): [0.0, 360.0] degrees (with sin/cos representation)
"""

from __future__ import annotations

import math
import numpy as np
import torch
from torch.utils.data import Dataset
from typing import Tuple, Dict, Any, Optional, List


ROOF_CLASSES = ["flat", "gable", "hip", "single-slant"]
CLASS_TO_IDX = {name: idx for idx, name in enumerate(ROOF_CLASSES)}
IDX_TO_CLASS = {idx: name for idx, name in enumerate(ROOF_CLASSES)}


def generate_synthetic_roof_patch(
    roof_type: str,
    pitch_deg: float,
    azimuth_deg: float,
    size: int = 128,
    base_height: float = 10.0,
    noise_std: float = 0.05,
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a realistic synthetic DSM elevation crop and pseudo-optical patch.
    
    Args:
        roof_type: One of 'flat', 'gable', 'hip', 'single-slant'
        pitch_deg: Pitch angle in degrees (0 to 45)
        azimuth_deg: Compass orientation in degrees (0 to 360, 0=North, 90=East)
        size: Width/height of the square patch in pixels
        base_height: Ground/base height in meters
        noise_std: Measurement noise in DSM height (m)
        seed: Optional RNG seed
        
    Returns:
        dsm_crop: 2D numpy array (size, size) with surface elevation in meters
        rgb_patch: 3D numpy array (size, size, 3) with simulated RGB illumination
    """
    if seed is not None:
        np.random.seed(seed)
        
    # Grid coordinates centered at origin [-1, 1]
    y_coords, x_coords = np.mgrid[-1:1:complex(0, size), -1:1:complex(0, size)]
    
    # Rotation by azimuth angle
    azimuth_rad = math.radians(azimuth_deg)
    cos_az = math.cos(azimuth_rad)
    sin_az = math.sin(azimuth_rad)
    
    # Rotated coordinates aligned with roof orientation
    x_rot = x_coords * cos_az + y_coords * sin_az
    y_rot = -x_coords * sin_az + y_coords * cos_az
    
    tan_pitch = math.tan(math.radians(pitch_deg))
    scale = 10.0  # spatial extent in meters
    
    # Elevation profile based on roof type
    if roof_type == "flat":
        # Flat roof has minimal/zero pitch
        z = np.zeros_like(x_rot)
    elif roof_type == "single-slant":
        # Monopitch / Shed roof: single sloping plane
        z = -y_rot * (scale * tan_pitch)
    elif roof_type == "gable":
        # Dual pitch symmetric around central ridge line (y_rot = 0)
        z = (1.0 - np.abs(y_rot)) * (scale * tan_pitch)
    elif roof_type == "hip":
        # Quad pitch: sloping on all 4 sides towards apex/ridge
        dist_ridge = np.maximum(np.abs(y_rot), np.maximum(0.0, np.abs(x_rot) - 0.4))
        z = (1.0 - dist_ridge) * (scale * tan_pitch)
    else:
        raise ValueError(f"Unknown roof type: {roof_type}. Choose from {ROOF_CLASSES}")
    
    # Absolute elevation = base_height + relative elevation + sensor noise
    dsm = base_height + z + np.random.normal(0, noise_std, size=(size, size))
    
    # Compute surface normal gradients for shading / pseudo-RGB
    dz_dy, dz_dx = np.gradient(dsm)
    normal_x = -dz_dx
    normal_y = -dz_dy
    normal_z = np.ones_like(dsm)
    norm = np.sqrt(normal_x**2 + normal_y**2 + normal_z**2)
    nx, ny, nz = normal_x / norm, normal_y / norm, normal_z / norm
    
    # Sun direction for optical shading
    sun_az = math.radians(135.0)
    sun_el = math.radians(45.0)
    sun_vec = np.array([
        math.cos(sun_el) * math.sin(sun_az),
        math.cos(sun_el) * math.cos(sun_az),
        math.sin(sun_el)
    ])
    
    shading = np.clip(nx * sun_vec[0] + ny * sun_vec[1] + nz * sun_vec[2], 0.1, 1.0)
    
    base_color = np.array([0.45, 0.48, 0.52])
    rgb = np.dstack([
        shading * base_color[0] + np.random.normal(0, 0.02, (size, size)),
        shading * base_color[1] + np.random.normal(0, 0.02, (size, size)),
        shading * base_color[2] + np.random.normal(0, 0.02, (size, size)),
    ])
    rgb = np.clip(rgb, 0.0, 1.0).astype(np.float32)
    dsm = dsm.astype(np.float32)
    
    return dsm, rgb


class RoofGeometryDataset(Dataset):
    """PyTorch Dataset yielding roof crops for geometry training."""
    
    def __init__(
        self,
        num_samples: int = 1000,
        patch_size: int = 128,
        in_channels: int = 4,  # 1 for DSM, 3 for RGB, 4 for RGB+DSM
        seed: int = 42,
    ):
        super().__init__()
        self.num_samples = num_samples
        self.patch_size = patch_size
        self.in_channels = in_channels
        self.rng = np.random.RandomState(seed)
        
        self.samples = []
        for i in range(num_samples):
            r_type = self.rng.choice(ROOF_CLASSES)
            if r_type == "flat":
                pitch = float(self.rng.uniform(0.0, 3.0))
            else:
                pitch = float(self.rng.uniform(5.0, 45.0))
            azimuth = float(self.rng.uniform(0.0, 360.0))
            base_h = float(self.rng.uniform(5.0, 40.0))
            self.samples.append({
                "roof_type": r_type,
                "class_idx": CLASS_TO_IDX[r_type],
                "pitch_deg": pitch,
                "azimuth_deg": azimuth,
                "base_height": base_h,
                "seed": seed + i,
            })
            
    def __len__(self) -> int:
        return self.num_samples
        
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        spec = self.samples[idx]
        dsm, rgb = generate_synthetic_roof_patch(
            roof_type=spec["roof_type"],
            pitch_deg=spec["pitch_deg"],
            azimuth_deg=spec["azimuth_deg"],
            size=self.patch_size,
            base_height=spec["base_height"],
            seed=spec["seed"],
        )
        
        dsm_norm = (dsm - np.mean(dsm)) / (np.std(dsm) + 1e-5)
        dsm_channel = np.expand_dims(dsm_norm, axis=0)  # (1, H, W)
        rgb_channels = np.transpose(rgb, (2, 0, 1))      # (3, H, W)
        
        if self.in_channels == 1:
            input_tensor = torch.from_numpy(dsm_channel).float()
        elif self.in_channels == 3:
            input_tensor = torch.from_numpy(rgb_channels).float()
        elif self.in_channels == 4:
            combined = np.concatenate([rgb_channels, dsm_channel], axis=0)
            input_tensor = torch.from_numpy(combined).float()
        else:
            raise ValueError(f"Unsupported in_channels: {self.in_channels}")
            
        class_idx = torch.tensor(spec["class_idx"], dtype=torch.long)
        pitch_val = torch.tensor(spec["pitch_deg"], dtype=torch.float32)
        
        azimuth_rad = math.radians(spec["azimuth_deg"])
        azimuth_sin_cos = torch.tensor([math.sin(azimuth_rad), math.cos(azimuth_rad)], dtype=torch.float32)
        azimuth_val = torch.tensor(spec["azimuth_deg"], dtype=torch.float32)
        
        return {
            "input": input_tensor,
            "class_idx": class_idx,
            "pitch_deg": pitch_val,
            "azimuth_sin_cos": azimuth_sin_cos,
            "azimuth_deg": azimuth_val,
            "roof_type": spec["roof_type"],
        }
