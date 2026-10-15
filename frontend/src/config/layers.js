// GIBS layer configuration — used by RiskMap for NASA imagery overlays (Phase 10).
// Layer identifiers are confirmed from GetCapabilities at:
//   https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities
// This file is a placeholder until Phase 10 confirms layer availability.

export const GIBS_BASE =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/{TileMatrixSet}/{z}/{y}/{x}.png';

export const GIBS_LAYERS = [
  {
    id: 'IMERG_Precipitation_Rate',
    label: 'NASA IMERG Precipitation',
    tileMatrixSet: '2km',
    attribution: 'NASA GIBS',
  },
  {
    id: 'MODIS_Terra_NDVI_8Day',
    label: 'MODIS Terra NDVI',
    tileMatrixSet: '250m',
    attribution: 'NASA GIBS',
  },
];

/** Hazard → CSS colour token string (mirrors tokens.css) */
export const HAZARD_COLORS = {
  low:      'var(--risk-low)',
  moderate: 'var(--risk-moderate)',
  high:     'var(--risk-high)',
};
