// API client: thin fetch wrapper for the backend REST API.
// All paths are relative to the Vite dev proxy (/api → http://localhost:8000).

const BASE = '/api';

/** Generic GET with JSON parsing and error normalisation */
async function get(path, params = {}) {
  const url = new URL(BASE + path, window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v != null) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) {
    let body;
    try { body = await res.json(); } catch { body = null; }
    const msg = body?.error?.message ?? `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return res.json();
}

// ── District routes ───────────────────────────────────────────────────────────

/** GET /api/districts → array of district objects */
export function getDistricts() {
  return get('/districts');
}

/** GET /api/crops → array of crop objects */
export function getCrops() {
  return get('/crops');
}

// ── Risk routes ───────────────────────────────────────────────────────────────

/**
 * GET /api/risk — map-level snapshot for all districts
 * @param {string|null} date  YYYY-MM-DD; defaults to latest
 * @param {string|null} hazard  'drought'|'flood'|'salt'
 */
export function getRisk({ date = null, hazard = null } = {}) {
  return get('/risk', { date, hazard });
}

/**
 * GET /api/risk/{districtId} — time series for a district
 * @param {string} districtId
 * @param {number} days  Window length (default 60)
 * @param {string|null} date  Window end date
 */
export function getRiskSeries(districtId, { days = 60, date = null } = {}) {
  return get(`/risk/${districtId}`, { days, date });
}

/**
 * GET /api/risk/{districtId}/explain — factor breakdown
 * @param {string} districtId
 * @param {string|null} date
 */
export function getRiskExplain(districtId, { date = null } = {}) {
  return get(`/risk/${districtId}/explain`, { date });
}

// ── Meta routes ───────────────────────────────────────────────────────────────

/** GET /api/health */
export function getHealth() {
  return get('/health');
}

/** GET /api/sources */
export function getSources() {
  return get('/sources');
}

/** GET /api/pipeline/status */
export function getPipelineStatus() {
  return get('/pipeline/status');
}

/** GET /api/scoring → scoring constants and thresholds */
export function getScoring() {
  return get('/scoring');
}


// ── Advice / messaging ───────────────────────────────────────────────────────

/**
 * POST /api/advice
 * @param {{ district_id, crop_id, date, language }} body
 */
export function postAdvice(body) {
  return fetch(`${BASE}/advice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async res => {
    if (!res.ok) {
      const b = await res.json().catch(() => null);
      throw new Error(b?.error?.message ?? `HTTP ${res.status}`);
    }
    return res.json();
  });
}

/**
 * POST /api/sim/sms
 * @param {{ from: string, body: string }} body
 */
export function postSimSms(body) {
  return fetch(`${BASE}/sim/sms`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }).then(async res => {
    if (!res.ok) {
      const b = await res.json().catch(() => null);
      throw new Error(b?.error?.message ?? `HTTP ${res.status}`);
    }
    return res.json();
  });
}

// ── Backtest route ────────────────────────────────────────────────────────────

/** GET /api/backtest/sylhet-2022 → backtest replay data */
export function getBacktestSylhet() {
  return get('/backtest/sylhet-2022');
}
