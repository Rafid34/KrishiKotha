import React, { useState, useEffect, useCallback } from 'react';
import RiskMap from '../components/RiskMap.jsx';
import HazardToggle from '../components/HazardToggle.jsx';
import DistrictPanel from '../components/DistrictPanel.jsx';
import DataFreshness from '../components/DataFreshness.jsx';
import SerratedDivider from '../components/SerratedDivider.jsx';
import { useLang, t } from '../i18n/index.jsx';
import { getDistricts, getRisk } from '../api/client.js';

export default function Dashboard({ initialDate = '', initialDistrictError = null, initialRiskError = null } = {}) {
  const { lang } = useLang();

  const [hazard, setHazard] = useState('flood');
  const [date, setDate] = useState(initialDate);
  const [districts, setDistricts] = useState([]);
  const [districtError, setDistrictError] = useState(initialDistrictError);
  const [riskResponse, setRiskResponse] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(!initialRiskError);
  const [error, setError] = useState(initialRiskError);

  // Fetch district list with error state and retry
  const fetchDistricts = useCallback(() => {
    setDistrictError(null);
    getDistricts()
      .then(data => {
        setDistricts(data);
        setDistrictError(null);
      })
      .catch(err => {
        setDistrictError(err.message || 'Failed to load districts');
        setDistricts([]);
      });
  }, []);

  useEffect(() => {
    fetchDistricts();
  }, [fetchDistricts]);

  // Fetch risk data whenever date changes
  const fetchRisk = useCallback(() => {
    setLoading(true);
    setError(null);
    getRisk(date ? { date } : {})
      .then(data => {
        setRiskResponse(data);
        if (!date && data?.date) {
          setDate(data.date);
        }
        setLoading(false);
      })
      .catch(err => { setError(err.message || 'Failed to load risk data'); setLoading(false); });
  }, [date]);

  useEffect(() => {
    fetchRisk();
  }, [fetchRisk]);

  const handleDateChange = useCallback(e => setDate(e.target.value), []);
  const handleHazardChange = useCallback(h => setHazard(h), []);
  const handleSelectDistrict = useCallback(id => setSelectedId(id), []);

  // Build the data structures the child components need
  const riskData = riskResponse?.districts ?? [];

  const selectedRiskEntry = selectedId
    ? riskData.find(r => r.district_id === selectedId) ?? null
    : null;

  const selectedDistrict = selectedId
    ? districts.find(d => d.id === selectedId) ?? null
    : null;

  // Sources come from the first riskData entry's sources field
  const sources = riskResponse?.districts?.[0]?.sources ?? null;

  return (
    <div className="dashboard">
      {/* Controls bar */}
      <div className="dashboard__controls">
        <div className="dashboard__controls-inner">
          <div className="dashboard__title-row">
            <h1 className="dashboard__title" lang={lang === 'bn' ? 'bn' : undefined}>
              {t('dashboard.title', lang)}
            </h1>

            {/* Mandatory advisory disclaimer shown at all times */}
            <p className="dashboard__disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
              {t('disclaimer', lang)}
            </p>
          </div>

          <div className="dashboard__control-row">
            {/* Hazard toggle (folder-style tabs, native radio group per spec §8.4) */}
            <HazardToggle value={hazard} onChange={handleHazardChange} />

            {/* Date picker & quick-pick demo button */}
            <div className="dashboard__date-picker">
              <label
                htmlFor="risk-date-input"
                className="dashboard__date-label"
                lang={lang === 'bn' ? 'bn' : undefined}
              >
                {t('dashboard.datePicker', lang)}
              </label>
              <input
                id="risk-date-input"
                type="date"
                value={date}
                min="2022-05-15"
                max={new Date().toISOString().slice(0, 10)}
                onChange={handleDateChange}
                className="dashboard__date-input"
                aria-label={t('dashboard.datePicker', lang)}
              />
              <button
                type="button"
                className="dashboard__demo-pick-btn"
                onClick={() => setDate('2022-06-16')}
                title={lang === 'bn' ? '১৬ জুন ২০২২ বন্যা ডেমো' : 'June 2022 flood demo'}
              >
                {lang === 'bn' ? 'জুন ২০২২ বন্যা ডেমো' : 'June 2022 flood demo'}
              </button>
            </div>

            {/* Data freshness callout (Sticky note styled) */}
            {sources && <DataFreshness sources={sources} />}
          </div>
        </div>
      </div>

      {/* Serrated edge divider between controls and main map body */}
      <SerratedDivider className="dashboard__divider" />

      {/* Main content: map + panel */}
      <div className="dashboard__body">
        {/* Map column */}
        <section className="dashboard__map-col" aria-label="Risk map">
          {districtError && (
            <div className="dashboard__error dashboard__error--districts" role="alert">
              <span>{lang === 'bn' ? 'জেলা তথ্য লোড করতে ব্যর্থ হয়েছে' : 'Failed to load districts'}: {districtError}</span>
              <button type="button" className="dashboard__retry-btn" onClick={fetchDistricts}>
                {lang === 'bn' ? 'পুনরায় চেষ্টা করুন' : 'Retry'}
              </button>
            </div>
          )}
          {loading && (
            <div className="dashboard__loading" role="status" aria-live="polite">
              <span lang={lang === 'bn' ? 'bn' : undefined}>{t('loading', lang)}</span>
            </div>
          )}
          {error && (
            <div className="dashboard__error" role="alert">
              <span lang={lang === 'bn' ? 'bn' : undefined}>{t('error', lang)}</span>
              <span className="dashboard__error-detail">{error}</span>
              <button type="button" className="dashboard__retry-btn" onClick={fetchRisk}>
                {lang === 'bn' ? 'পুনরায় চেষ্টা করুন' : 'Retry'}
              </button>
            </div>
          )}
          {!loading && !error && riskData.length === 0 && (
            <div className="dashboard__no-data" role="status">
              <span lang={lang === 'bn' ? 'bn' : undefined}>{t('noData', lang)}</span>
            </div>
          )}
          <RiskMap
            districts={districts}
            riskData={riskData}
            hazard={hazard}
            selectedId={selectedId}
            onSelectDistrict={handleSelectDistrict}
            date={date}
          />
        </section>

        {/* District detail panel */}
        <aside className="dashboard__panel-col" aria-label="District detail">
          <DistrictPanel
            district={selectedDistrict}
            riskEntry={selectedRiskEntry}
            date={date}
          />
        </aside>
      </div>
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.dashboard {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Controls bar */
.dashboard__controls {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: var(--space-4) 0 var(--space-3) 0;
  flex-shrink: 0;
  position: relative;
  z-index: 10;
}
.dashboard__controls-inner {
  max-width: 1360px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.dashboard__title-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--space-3);
}

.dashboard__title {
  font-family: var(--font-serif);
  font-size: var(--text-3xl);
  color: var(--foreground);
  font-weight: 300;
  letter-spacing: -0.02em;
  margin: 0;
}

.dashboard__disclaimer {
  font-size: 11px;
  color: var(--ink-muted);
  margin: 0;
  line-height: 1.4;
}

.dashboard__control-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.dashboard__date-picker {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.dashboard__date-label {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}
.dashboard__date-input {
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  padding: var(--space-1) var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--foreground);
  background: var(--surface-elevated);
  min-height: 44px;
  cursor: pointer;
  transition: border-color var(--transition);
}
.dashboard__date-input:hover,
.dashboard__date-input:focus {
  border-color: var(--accent);
  outline: none;
}
.dashboard__date-input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.dashboard__demo-pick-btn {
  padding: 0 var(--space-4);
  background: rgba(212, 242, 104, 0.12);
  border: 1px solid rgba(212, 242, 104, 0.35);
  border-radius: var(--radius-full);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--accent);
  min-height: 44px;
  cursor: pointer;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition-fast), transform var(--transition-fast);
}
.dashboard__demo-pick-btn:hover {
  background: rgba(212, 242, 104, 0.22);
  transform: translateY(-1px);
}
.dashboard__demo-pick-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Serrated divider under controls */
.dashboard__divider {
  margin: 0;
  background: var(--surface);
}

/* Body: map + panel */
.dashboard__body {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: minmax(360px, 55vh) auto;
  max-width: 1360px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-4);
  gap: var(--space-4);
  overflow-y: auto;
}

/* >=1024px: 65/35 split */
@media (min-width: 1024px) {
  .dashboard__body {
    grid-template-columns: 65fr 35fr;
    grid-template-rows: 1fr;
    height: calc(100dvh - 64px - 140px);
    overflow: hidden;
  }
  .dashboard__map-col {
    overflow: hidden;
    height: 100%;
  }
  .dashboard__panel-col {
    overflow-y: auto;
    height: 100%;
  }
}

.dashboard__map-col {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.dashboard__loading,
.dashboard__error,
.dashboard__no-data {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  background: rgba(12, 10, 9, 0.85);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--foreground);
  backdrop-filter: blur(4px);
}
.dashboard__error {
  color: var(--risk-high);
}
.dashboard__error--districts {
  position: relative;
  inset: auto;
  z-index: 5;
  padding: var(--space-2) var(--space-4);
  background: rgba(248, 113, 113, 0.12);
  border: 1px solid rgba(248, 113, 113, 0.4);
  color: var(--risk-high);
  border-radius: var(--radius-md);
  flex-direction: row;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.dashboard__error-detail {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}
.dashboard__retry-btn {
  padding: 0 var(--space-4);
  background: var(--accent);
  color: var(--accent-foreground);
  border: none;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: 600;
  min-height: 44px;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.dashboard__retry-btn:hover {
  background: var(--brand-dark);
}

@media (max-width: 640px) {
  .dashboard__controls-inner {
    padding: 0 var(--space-3);
    gap: var(--space-2);
  }
  .dashboard__body {
    padding: var(--space-3);
    gap: var(--space-3);
  }
  .dashboard__title {
    font-size: var(--text-2xl);
  }
  .dashboard__control-row {
    gap: var(--space-2);
  }
}

@media (max-width: 360px) {
  .dashboard__controls-inner {
    padding: 0 var(--space-2);
  }
  .dashboard__body {
    padding: var(--space-2);
    gap: var(--space-2);
  }
}
`;
  if (!document.getElementById('dashboard-styles')) {
    style.id = 'dashboard-styles';
    document.head.appendChild(style);
  }
}
