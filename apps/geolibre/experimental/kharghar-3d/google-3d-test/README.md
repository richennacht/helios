# Google 3D Tiles AOI test

This route is deployed inside the Vercel project's configured root directory at
`/google-3d-test`. It isolates Google Photorealistic 3D Tiles authentication and
rendering from Helios AOI and ranking logic.

The key remains only in browser memory and the input is cleared after renderer
creation. The page uses deck.gl `Tile3DLayer` over MapLibre, reports the actual
Google root response, and displays tile attribution.

The location selector includes Kharghar as the target AOI and New York as a
known-covered control. This separates renderer/authentication failures from a
location that lacks Google's photorealistic surface mesh.
