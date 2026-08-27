# Roof geometry simulation

Helios exposes a roof-plane simulation for demonstrating how explicit pitch and
azimuth assumptions affect surface area and screening yield. The API route is
`POST /geometry/simulate`; the existing MapLibre viewer exposes the same inputs
under **Roof geometry**.

Every simulation requires a roof type, pitch, azimuth, and provenance string.
Responses use `decision_status: simulation_only` and `confidence: null`.
Simulated values are not written into the production candidate catalogue and are
not treated as model predictions or ranking evidence.

The contributed PR included a ResNet-18 architecture and synthetic training
summary but no validated weights or geographically held-out Kharghar evaluation.
Helios therefore abstains from learned roof prediction until registered weights,
input imagery/elevation provenance, and local validation are available. Flat roofs
do not receive invented orientation, and Copernicus GLO-30 remains terrain context,
not roof geometry.
