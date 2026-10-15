// NASA GIBS overlay configuration used by RiskMap (Phase 10, task 10.4, feature F2.6).
//
// Every id, tile matrix set, format and coverage start below was read from the live GetCapabilities
// document on 2026-10-15 (re-run `python scripts/inspect_gibs.py` to re-check):
//   https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/wmts.cgi?SERVICE=WMTS&REQUEST=GetCapabilities
// Tile requests were also probed with `python scripts/probe_gibs_tiles.py`:
//   - a date inside a layer's period snaps to that period (2022-06-10 and 2022-06-16 return the same
//     16-day NDVI tile), so any calendar date inside the coverage works;
//   - a date before the coverage start returns HTTP 404, so the UI checks `layerAvailability` first and
//     shows a "no imagery for this date" fallback instead of an empty map.
//
// Differences from the spec's assumptions (also recorded in docs/data_sources.md):
//   - Tile matrix sets are `GoogleMapsCompatible_Level6` (IMERG) and `GoogleMapsCompatible_Level9`
//     (MODIS), not '2km' / '250m'. `maxNativeZoom` is Level - 0 (6 and 9); Leaflet upscales beyond that.
//   - `MODIS_Terra_NDVI_8Day` exists but its coverage only starts 2025-02-12, so it cannot show the
//     2022-06-16 demo date. `MODIS_Terra_L3_NDVI_16Day` (coverage from 2000-03-05) is listed as well and
//     is the default NDVI choice because it also matches the 16-day MOD13Q1 product used by the pipeline.

export const GIBS_TILE_URL =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{time}/{tileMatrixSet}/{z}/{y}/{x}.png';

export const GIBS_ATTRIBUTION =
  'Imagery: <a href="https://earthdata.nasa.gov/gibs" target="_blank" rel="noopener">NASA GIBS</a>';

export const GIBS_LAYERS = [
  {
    key: 'imerg',
    id: 'IMERG_Precipitation_Rate',
    label: { en: 'NASA IMERG precipitation rate', bn: 'নাসা আইএমইআরজি বৃষ্টিপাতের হার' },
    tileMatrixSet: 'GoogleMapsCompatible_Level6',
    maxNativeZoom: 6,
    format: 'png',
    coverageStart: '2000-06-01',
    attribution: 'NASA GIBS',
    opacity: 0.7,
  },
  {
    key: 'ndvi16',
    id: 'MODIS_Terra_L3_NDVI_16Day',
    label: { en: 'MODIS Terra NDVI (16-day)', bn: 'মোডিস টেরা এনডিভিআই (১৬ দিন)' },
    tileMatrixSet: 'GoogleMapsCompatible_Level9',
    maxNativeZoom: 9,
    format: 'png',
    coverageStart: '2000-03-05',
    attribution: 'NASA GIBS',
    opacity: 0.7,
  },
  {
    key: 'ndvi8',
    id: 'MODIS_Terra_NDVI_8Day',
    label: { en: 'MODIS Terra NDVI (rolling 8-day)', bn: 'মোডিস টেরা এনডিভিআই (৮ দিন)' },
    tileMatrixSet: 'GoogleMapsCompatible_Level9',
    maxNativeZoom: 9,
    format: 'png',
    coverageStart: '2025-02-12',
    attribution: 'NASA GIBS',
    opacity: 0.7,
  },
];

/** Build the Leaflet tile URL template for a layer on one date (`{z}/{y}/{x}` stay for Leaflet). */
export function gibsTileUrl(layer, date) {
  return GIBS_TILE_URL
    .replace('{layer}', layer.id)
    .replace('{time}', date)
    .replace('{tileMatrixSet}', layer.tileMatrixSet);
}

/**
 * Whether imagery exists for `date` (YYYY-MM-DD). Coverage ends at the present, so only the start
 * date and future dates are checked; ISO date strings compare correctly as text.
 * @returns {'ok'|'before_coverage'|'future'|'invalid'}
 */
export function layerAvailability(layer, date, today = new Date().toISOString().slice(0, 10)) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date ?? '')) return 'invalid';
  if (date < layer.coverageStart) return 'before_coverage';
  if (date > today) return 'future';
  return 'ok';
}

/** i18n key of the fallback message to show for an overlay state, or null when none is needed. */
export function overlayMessageKey(status, tileError = false) {
  if (status === 'before_coverage') return 'overlay.beforeCoverage';
  if (status === 'future') return 'overlay.future';
  if (tileError) return 'overlay.tileError';
  return null;
}

/** Hazard level to CSS colour token string (mirrors tokens.css) */
export const HAZARD_COLORS = {
  low:      'var(--risk-low)',
  moderate: 'var(--risk-moderate)',
  high:     'var(--risk-high)',
};
