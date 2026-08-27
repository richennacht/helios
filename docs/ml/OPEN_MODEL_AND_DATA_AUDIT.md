# Open model and data audit for rooftop analysis

## Adopted baseline

RID2 is the primary training source for the first Helios roof-understanding
model. It supplies CC BY 4.0 aerial imagery, fixed splits and semantic masks for
roof orientation and roof superstructures. Helios preserves its source label
encoding and records the DOI and archive checksum in a source manifest.

The first baseline is a shared-encoder U-Net with separate segment and
superstructure heads. This avoids duplicating the visual encoder while retaining
separate losses and held-out metrics.

## Reuse findings

| Source | Reusable asset | Decision |
|---|---|---|
| RID2 | 4764 images, segment masks, obstruction masks, fixed splits | primary training dataset |
| TUM RID | U-Net/FPN/PSPNet training code and deterministic module placement | method reference; old Python stack is not copied into runtime |
| TUM ECOPPP | RID2 processing and related PV-potential code | inspect after dataset extraction |
| Swiss STDL proj-rooftops | MIT-licensed LiDAR/SAM rooftop occupancy workflows | reuse concepts and fixtures; full imagery is request-only |
| RoofN3D | PointNet code, demo weights and roof point-cloud labels | geometry research baseline only; repository has no explicit licence file |
| pybdshadow | BSD-licensed building-shadow generation and sunshine-time analysis | candidate deterministic shade baseline |
| Sai150 roof-top-dataset | 50 MIT-licensed images, masks, polygons and ridge lines | loader/inference smoke tests only |

## Important gaps

RID2 orientation labels are directional classes, not measured continuous roof
slope angles. It can train roof-plane segmentation and coarse azimuth, but the
geometry model still needs slope/height supervision from 3DBAG, ZRG, LiDAR/DSM
or an equivalent source.

RID2 excludes tree overhang and shadow from its superstructure annotations.
Those require a separate canopy/shadow label source or a physical DSM-based
shade engine. The roof-understanding output must not silently treat unlabeled
tree shadow as usable roof.

No public model found so far is ready to drop into Kharghar without domain
validation. Existing open code materially reduces implementation work, but a
held-out Indian imagery set remains a promotion requirement.

## Phase boundary

This phase gathers and validates data and establishes a trainable baseline. It
does not yet promote the model into ranking, replace professional inspection or
claim accurate Indian rooftop performance.
