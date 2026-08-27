/**
 * HELIOS Client-Side Constraint-Aware Solar PV Panel Layout Optimizer
 * ===================================================================
 * Implements real-time geometric module packing, parapet setbacks (1.0m),
 * maintenance aisles (0.8m), solar access thresholding (>=80%), and
 * 15% reserved space policy directly on MapLibre 3D rooftops.
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.HeliosPVOptimizer = factory();
  }
})(typeof self !== 'undefined' ? self : this, function () {

  const WGS84_A = 6378137.0;

  function latLonToMeters(lon, lat, refLon, refLat) {
    const rad = Math.PI / 180.0;
    const latRad = refLat * rad;
    const dx = (lon - refLon) * rad * WGS84_A * Math.cos(latRad);
    const dy = (lat - refLat) * rad * WGS84_A;
    return [dx, dy];
  }

  function metersToLatLon(dx, dy, refLon, refLat) {
    const rad = Math.PI / 180.0;
    const latRad = refLat * rad;
    const lon = refLon + dx / (WGS84_A * Math.cos(latRad) * rad);
    const lat = refLat + dy / (WGS84_A * rad);
    return [lon, lat];
  }

  function pointInPolygon(x, y, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const xi = ring[i][0], yi = ring[i][1];
      const xj = ring[j][0], yj = ring[j][1];
      const intersect = ((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / ((yj - yi) || 1e-12) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function distSqPointToSegment(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    if (lenSq === 0) return (px - x1) * (px - x1) + (py - y1) * (py - y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / lenSq;
    t = Math.max(0, Math.min(1, t));
    const projX = x1 + t * dx;
    const projY = y1 + t * dy;
    return (px - projX) * (px - projX) + (py - projY) * (py - projY);
  }

  function minDistanceToPolygonBoundary(px, py, ring) {
    let minDistSq = Infinity;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const dSq = distSqPointToSegment(px, py, ring[j][0], ring[j][1], ring[i][0], ring[i][1]);
      if (dSq < minDistSq) minDistSq = dSq;
    }
    return Math.sqrt(minDistSq);
  }

  function computeFootprintCentroid(ring) {
    let sumX = 0, sumY = 0;
    const n = ring.length > 1 && ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1] ? ring.length - 1 : ring.length;
    for (let i = 0; i < n; i++) {
      sumX += ring[i][0];
      sumY += ring[i][1];
    }
    return [sumX / n, sumY / n];
  }

  /**
   * Optimize PV module layout for a single building polygon
   */
  function optimizeBuildingLayout(feature, options = {}) {
    const config = Object.assign({
      parapetSetback: 1.0,               // 1.0m parapet setback
      maintenanceAisleWidth: 0.8,        // 0.8m maintenance aisles
      maintenanceAisleFreqRows: 2,       // Walkway every 2 rows
      reservedSpaceRatio: 0.15,          // 15% reserved space
      minSolarAccess: 0.80,              // 80% min solar access
      moduleLength: 2.2,                 // 2.2m length
      moduleWidth: 1.1,                  // 1.1m width
      moduleWattageWp: 550.0,            // 550 Wp
      tiltDeg: 15.0,                     // 15 deg tilt
      azimuthDeg: 180.0,                 // 180 deg (South facing)
      annualPoaKwhM2: 1800.0,            // NASA POWER Kharghar
      capexPerKwpInr: 50000.0,           // Rs 50,000 / kWp
      tariffPerKwhInr: 8.0,              // Rs 8.0 / kWh
      performanceRatio: 0.80,            // 80% PR
    }, options);

    const coords = feature.geometry.type === 'Polygon'
      ? feature.geometry.coordinates[0]
      : feature.geometry.coordinates[0][0];

    const [refLon, refLat] = computeFootprintCentroid(coords);

    // Convert WGS84 polygon to local metric coordinates (meters)
    const metricRing = coords.map(pt => latLonToMeters(pt[0], pt[1], refLon, refLat));

    // Bounding box of roof in meters
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const [x, y] of metricRing) {
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }

    // Module ground footprint projection
    const tiltRad = config.tiltDeg * Math.PI / 180.0;
    const dimX = config.moduleWidth;                          // 1.1m along East-West row
    const dimY = config.moduleLength * Math.cos(tiltRad);     // 2.125m along North-South pitch
    const sunAltitudeRad = 28.0 * Math.PI / 180.0;            // Design winter altitude
    const shadowClearance = (config.moduleLength * Math.sin(tiltRad)) / Math.tan(sunAltitudeRad);
    const stepY = dimY + shadowClearance;                     // ~3.195m pitch
    const stepX = dimX + 0.02;                                // 1.12m with clamp gap

    // Sweep grid offsets to maximize packed panel yield
    let bestPanels = [];
    const nSteps = 5;
    const offsetsX = [0, stepX * 0.25, stepX * 0.5, stepX * 0.75];
    const offsetsY = [0, stepY * 0.25, stepY * 0.5, stepY * 0.75];

    for (const offX of offsetsX) {
      for (const offY of offsetsY) {
        const candidatePanels = [];
        let currY = minY + offY;
        let rowIdx = 0;

        while (currY + dimY <= maxY) {
          // Maintenance aisle between row blocks
          if (config.maintenanceAisleFreqRows > 0 && rowIdx > 0 && (rowIdx % config.maintenanceAisleFreqRows === 0)) {
            currY += config.maintenanceAisleWidth;
            if (currY + dimY > maxY) break;
          }

          let currX = minX + offX;
          while (currX + dimX <= maxX) {
            const p1 = [currX, currY];
            const p2 = [currX + dimX, currY];
            const p3 = [currX + dimX, currY + dimY];
            const p4 = [currX, currY + dimY];
            const center = [currX + dimX * 0.5, currY + dimY * 0.5];

            // Strict containment test: all 4 corners + center inside polygon
            const allInside = pointInPolygon(p1[0], p1[1], metricRing) &&
                              pointInPolygon(p2[0], p2[1], metricRing) &&
                              pointInPolygon(p3[0], p3[1], metricRing) &&
                              pointInPolygon(p4[0], p4[1], metricRing) &&
                              pointInPolygon(center[0], center[1], metricRing);

            if (allInside) {
              // Parapet setback check: distance from all 4 corners to boundary >= setback
              const d1 = minDistanceToPolygonBoundary(p1[0], p1[1], metricRing);
              const d2 = minDistanceToPolygonBoundary(p2[0], p2[1], metricRing);
              const d3 = minDistanceToPolygonBoundary(p3[0], p3[1], metricRing);
              const d4 = minDistanceToPolygonBoundary(p4[0], p4[1], metricRing);

              if (Math.min(d1, d2, d3, d4) >= config.parapetSetback - 1e-4) {
                // Synthetic realistic roof solar access (accounting for North parapet shadow)
                const normY = (currY - minY) / (maxY - minY || 1);
                const solarAccess = normY > 0.88 ? 0.75 : 0.95;

                if (solarAccess >= config.minSolarAccess) {
                  candidatePanels.push({
                    metricBox: [p1, p2, p3, p4],
                    solarAccess: solarAccess,
                    center: center
                  });
                }
              }
            }
            currX += stepX;
          }
          currY += stepY;
          rowIdx++;
        }

        if (candidatePanels.length > bestPanels.length) {
          bestPanels = candidatePanels;
        }
      }
    }

    // Apply 15% Reserved Space policy
    if (config.reservedSpaceRatio > 0 && bestPanels.length > 0) {
      const keepCount = Math.floor(bestPanels.length * (1.0 - config.reservedSpaceRatio));
      bestPanels.sort((a, b) => b.solarAccess - a.solarAccess || b.center[1] - a.center[1]);
      bestPanels = bestPanels.slice(0, keepCount);
      bestPanels.sort((a, b) => b.center[1] - a.center[1] || a.center[0] - b.center[0]);
    }

    const totalPanelCount = bestPanels.length;
    const installedDcCapacityKwp = (totalPanelCount * config.moduleWattageWp) / 1000.0;
    const roofHeightM = Number(feature.properties.height_m) || Number(feature.properties.render_height) || 10.0;

    // Calculate annual generation and financials
    const annualYieldKwh = installedDcCapacityKwp * config.annualPoaKwhM2 * 0.95 * config.performanceRatio;
    const estimatedCostInr = installedDcCapacityKwp * config.capexPerKwpInr;
    const annualValueInr = annualYieldKwh * config.tariffPerKwhInr;
    const simplePaybackYears = annualValueInr > 0 ? estimatedCostInr / annualValueInr : 0;

    // Convert placed panels to WGS84 GeoJSON features with 3D elevations
    const panelFeatures = bestPanels.map((p, idx) => {
      const ringWgs84 = p.metricBox.map(pt => metersToLatLon(pt[0], pt[1], refLon, refLat));
      ringWgs84.push(ringWgs84[0]); // close polygon

      return {
        type: 'Feature',
        geometry: {
          type: 'Polygon',
          coordinates: [ringWgs84]
        },
        properties: {
          layer: 'pv_panel',
          panel_id: idx + 1,
          candidate_id: feature.properties.candidate_id || feature.properties.osm_way_id || 'building',
          roof_height_m: roofHeightM,
          panel_elev_top: roofHeightM + 0.55,
          panel_elev_base: roofHeightM + 0.35,
          rated_power_w: config.moduleWattageWp,
          solar_access: p.solarAccess
        }
      };
    });

    return {
      candidateId: feature.properties.candidate_id || feature.properties.osm_way_id || 'building',
      totalPanelCount: totalPanelCount,
      installedDcCapacityKwp: installedDcCapacityKwp,
      annualYieldKwh: annualYieldKwh,
      estimatedCostInr: estimatedCostInr,
      annualValueInr: annualValueInr,
      simplePaybackYears: simplePaybackYears,
      roofHeightM: roofHeightM,
      panelFeatures: panelFeatures,
      config: config
    };
  }

  /**
   * Optimize PV layouts across all selected buildings in AOI
   */
  function optimizeAoiLayout(features, options = {}) {
    const results = features.map(f => optimizeBuildingLayout(f, options));
    const allPanelFeatures = results.flatMap(r => r.panelFeatures);

    const totalPanels = results.reduce((sum, r) => sum + r.totalPanelCount, 0);
    const totalCapacityKwp = results.reduce((sum, r) => sum + r.installedDcCapacityKwp, 0);
    const totalYieldKwh = results.reduce((sum, r) => sum + r.annualYieldKwh, 0);
    const totalCostInr = results.reduce((sum, r) => sum + r.estimatedCostInr, 0);

    return {
      buildingResults: results,
      totalPanels: totalPanels,
      totalCapacityKwp: totalCapacityKwp,
      totalYieldKwh: totalYieldKwh,
      totalCostInr: totalCostInr,
      panelFeatureCollection: {
        type: 'FeatureCollection',
        features: allPanelFeatures
      }
    };
  }

  return {
    latLonToMeters: latLonToMeters,
    metersToLatLon: metersToLatLon,
    pointInPolygon: pointInPolygon,
    optimizeBuildingLayout: optimizeBuildingLayout,
    optimizeAoiLayout: optimizeAoiLayout
  };
});
