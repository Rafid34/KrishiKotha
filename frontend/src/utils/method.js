// Pure formatting logic for the Method and Data page (Section 8.2 & Phase 12)
import { formatDate } from './format.js';

/**
 * Format Flood scoring formula and weights from /api/scoring constants.
 * @param {object} constants - SCORING_CONSTANTS from /api/scoring
 * @returns {string} Preformatted formula text
 */
export function formatFloodFormula(constants) {
  const f = constants?.flood || {};
  const wRain3 = f.weight_rain3 ?? 0.40;
  const wRain7 = f.weight_rain7 ?? 0.35;
  const wSoil = f.weight_soil ?? 0.25;

  return [
    `Flood Risk Score (0 - 100) =`,
    `  ${wRain3} × f_rain3 + ${wRain7} × f_rain7 + ${wSoil} × f_soil`,
    ``,
    `Where:`,
    `  f_rain3 = percentile_rank(3-day accumulated rainfall vs baseline) × 100`,
    `  f_rain7 = percentile_rank(7-day accumulated rainfall vs baseline) × 100`,
    `  f_soil  = soil moisture percentile (SMAP L4 root zone or POWER GWETROOT fallback)`,
    ``,
    `Weights:`,
    `  - 3-day rainfall (f_rain3): ${wRain3}`,
    `  - 7-day rainfall (f_rain7): ${wRain7}`,
    `  - Soil moisture (f_soil):   ${wSoil}`,
    ``,
    `Degraded fallback (missing soil):`,
    `  Weights renormalize: rain3 = ${wRain3} / ${(wRain3 + wRain7).toFixed(2)}, rain7 = ${wRain7} / ${(wRain3 + wRain7).toFixed(2)}`,
  ].join('\n');
}

/**
 * Format Drought scoring formula and weights from /api/scoring constants.
 * @param {object} constants - SCORING_CONSTANTS from /api/scoring
 * @returns {string} Preformatted formula text
 */
export function formatDroughtFormula(constants) {
  const d = constants?.drought || {};
  const wSoil = d.weight_soil ?? 0.45;
  const wRain = d.weight_rain ?? 0.35;
  const wHeat = d.weight_heat ?? 0.20;
  const deficitScale = d.deficit_scale ?? 125.0;
  const heatMaxAnom = d.heat_max_anomaly ?? 4.0;

  return [
    `Drought Risk Score (0 - 100) =`,
    `  ${wSoil} × d_soil + ${wRain} × d_rain + ${wHeat} × d_heat`,
    ``,
    `Where:`,
    `  d_soil = (1 - soil_pctl) × 100  (dry root zone scores high)`,
    `  d_rain = clamp(rain_deficit × ${deficitScale}, 0, 100)  (80% deficit scores 100)`,
    `           rain_deficit = (rain30_mean - rain30_mm) / rain30_mean`,
    `  d_heat = clamp((heat_anomaly / ${heatMaxAnom}) × 100, 0, 100)  (+${heatMaxAnom}°C anomaly scores 100)`,
    `           heat_anomaly = max(0, tmax7 - tmax_base)`,
    ``,
    `Weights:`,
    `  - Root-zone soil dryness (d_soil): ${wSoil}`,
    `  - 30-day rainfall deficit (d_rain): ${wRain}`,
    `  - Extreme heat anomaly (d_heat):    ${wHeat}`,
    ``,
    `Degraded fallback handling:`,
    `  - Missing soil: drop soil term, renormalize rain (${wRain} / ${(wRain + wHeat).toFixed(2)}) and heat (${wHeat} / ${(wRain + wHeat).toFixed(2)})`,
    `  - Missing heat: drop heat term, renormalize soil (${wSoil} / ${(wSoil + wRain).toFixed(2)}) and rain (${wRain} / ${(wSoil + wRain).toFixed(2)})`,
    `  - Missing both: score on rain deficit alone with degraded flag`,
  ].join('\n');
}

/**
 * Format Salinity scoring formula and weights from /api/scoring constants.
 * @param {object} constants - SCORING_CONSTANTS from /api/scoring
 * @returns {string} Preformatted formula text
 */
export function formatSalinityFormula(constants) {
  const s = constants?.salinity || {};
  const coastMax = s.coast_max_km ?? 150.0;
  const coastMin = s.coast_min_km ?? 20.0;
  const coastSpan = s.coast_span_km ?? 130.0;
  const seasonHigh = s.season_scores?.mar_to_may ?? 100.0;
  const seasonMod = s.season_scores?.feb_and_jun ?? 60.0;
  const seasonLow = s.season_scores?.other ?? 20.0;

  const wWith = s.weights_with_ndvi || {};
  const wWithSeason = wWith.season ?? 0.40;
  const wWithDry = wWith.dry ?? 0.30;
  const wWithVeg = wWith.veg ?? 0.30;
  const ndviScale = s.ndvi_scale ?? 0.10;

  const wWithout = s.weights_without_ndvi || {};
  const wWithoutSeason = wWithout.season ?? 0.55;
  const wWithoutDry = wWithout.dry ?? 0.45;

  return [
    `Salinity Stress Proxy Score (0 - 100) =`,
    `  coastal_proximity_multiplier × inland_score`,
    ``,
    `Coastal proximity multiplier:`,
    `  multiplier = clamp((${coastMax} - distance_to_coast_km) / ${coastSpan}, 0, 1)`,
    `  - Distance ≤ ${coastMin} km: multiplier = 1.0 (maximum coastal exposure)`,
    `  - Distance ≥ ${coastMax} km: multiplier = 0.0 (inland districts score 0)`,
    ``,
    `Level 2 inland score (with MODIS NDVI anomaly):`,
    `  inland_score = ${wWithSeason} × season + ${wWithDry} × dry_index + ${wWithVeg} × veg_anomaly`,
    `  where:`,
    `    dry_index   = clamp(rain_deficit × 125, 0, 100)`,
    `    veg_anomaly = clamp((-ndvi_anomaly / ${ndviScale}) × 100, 0, 100)`,
    ``,
    `Level 1 inland score (without NDVI fallback):`,
    `  inland_score = ${wWithoutSeason} × season + ${wWithoutDry} × dry_index`,
    ``,
    `Season sub-scores:`,
    `  - March to May (peak salinity):     ${seasonHigh}`,
    `  - February and June (transitional):  ${seasonMod}`,
    `  - Other months (monsoon / flush):    ${seasonLow}`,
  ].join('\n');
}

/**
 * Return formatted threshold table rows from /api/scoring constants.
 * @param {object} constants
 * @returns {Array<{level: string, condition: string, label: string, labelBn: string}>}
 */
export function formatThresholds(constants) {
  const t = constants?.thresholds || {};
  const mod = t.moderate ?? 40.0;
  const high = t.high ?? 70.0;

  return [
    {
      level: 'low',
      condition: `< ${mod}`,
      label: 'Low',
      labelBn: 'কম',
    },
    {
      level: 'moderate',
      condition: `${mod} – ${(high - 0.01).toFixed(2)}`,
      label: 'Moderate',
      labelBn: 'মাঝারি',
    },
    {
      level: 'high',
      condition: `≥ ${high}`,
      label: 'High',
      labelBn: 'বেশি',
    },
  ];
}

/**
 * Format a last data date string for display.
 * @param {string|null} isoDate
 * @param {string} lang
 * @returns {string}
 */
export function formatSourceDate(isoDate, lang = 'en') {
  if (!isoDate) return lang === 'bn' ? 'তথ্য নেই' : 'No data';
  return formatDate(isoDate, lang);
}
