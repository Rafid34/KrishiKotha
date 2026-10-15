import React, { useState, useEffect, useCallback } from 'react';
import RiskMap from '../components/RiskMap.jsx';
import HazardToggle from '../components/HazardToggle.jsx';
import DistrictPanel from '../components/DistrictPanel.jsx';
import DataFreshness from '../components/DataFreshness.jsx';
import { useLang, t } from '../i18n/index.jsx';
import { getDistricts, getRisk } from '../api/client.js';

// Demo date — 2022-06-16 is the key event date in the snapshots
const DEMO_DATE = '2022-06-16';

export default function Dashboard() {
  const { lang } = useLang();

  const [hazard, setHazard] = useState('flood');
  const [date, setDate] = useState(DEMO_DATE);
  const [districts, setDistricts] = useState([]);
  const [riskResponse, setRiskResponse] = useState(null);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch district list once
  useEffect(() => {
    getDistricts()
      .then(setDistricts)
      .catch(() => setDistricts([]));
  }, []);

  // Fetch risk data whenever date changes
  useEffect(() => {
    setLoading(true);
    setError(null);
    getRisk({ date })
      .then(data => { setRiskResponse(data); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, [date]);

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
  // (they're the same for all districts on a given date)
  const sources = riskResponse?.districts?.[0]?.sources ?? null;

  return (
    <div className="dashboard">
      {/* Controls bar */}
      <div className="dashboard__controls">
        <div className="dashboard__controls-inner">
          <h1 className="dashboard__title" lang={lang === 'bn' ? 'bn' : undefined}>
            {t('dashboard.title', lang)}
          </h1>

          <div className="dashboard__control-row">
            {/* Hazard toggle (native radios per spec §8.4) */}
            <HazardToggle value={hazard} onChange={handleHazardChange} />

            {/* Date picker */}
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
            </div>
          </div>

          {/* Data freshness strip */}
          {sources && <DataFreshness sources={sources} />}

          {/* Mandatory advisory disclaimer shown at all times */}
          <p className="dashboard__disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
            {t('disclaimer', lang)}
          </p>
        </div>
      </div>

      {/* Main content: map + panel */}
      <div className="dashboard__body">
        {/* Map column */}
        <section className="dashboard__map-col" aria-label="Risk map">
          {loading && (
            <div className="dashboard__loading" role="status" aria-live="polite">
              <span lang={lang === 'bn' ? 'bn' : undefined}>{t('loading', lang)}</span>
            </div>
          )}
          {error && (
            <div className="dashboard__error" role="alert">
              <span lang={lang === 'bn' ? 'bn' : undefined}>{t('error', lang)}</span>
              <span className="dashboard__error-detail">{error}</span>
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
const style = document.createElement('style');
style.textContent = `
.dashboard {
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

/* Controls bar */
.dashboard__controls {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: var(--space-4) 0;
  flex-shrink: 0;
}
.dashboard__controls-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.dashboard__title {
  font-size: var(--text-xl);
  color: var(--brand);
  font-weight: 700;
}
.dashboard__disclaimer {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  margin: 0;
  line-height: 1.4;
}
.dashboard__control-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-5);
}
.dashboard__date-picker {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.dashboard__date-label {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--ink-muted);
  white-space: nowrap;
}
.dashboard__date-input {
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--ink);
  background: var(--bg);
  min-height: 44px;
  cursor: pointer;
  transition: border-color var(--transition);
}
.dashboard__date-input:hover,
.dashboard__date-input:focus {
  border-color: var(--brand);
  outline: none;
}
.dashboard__date-input:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 2px;
}

/* Body: map + panel */
.dashboard__body {
  flex: 1;
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: minmax(340px, 55vh) auto;
  max-width: 1280px;
  width: 100%;
  margin: 0 auto;
  padding: var(--space-4);
  gap: var(--space-4);
  overflow-y: auto;
}

/* â‰¥1024px: side-by-side, 65/35 split */
@media (min-width: 1024px) {
  .dashboard__body {
    grid-template-columns: 65fr 35fr;
    grid-template-rows: 1fr;
    height: calc(100dvh - 56px - 120px); /* Viewport minus header minus controls */
    overflow: hidden;
  }
  .dashboard__map-col {
    overflow: hidden;
  }
  .dashboard__panel-col {
    overflow-y: auto;
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
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  background: rgba(247,246,241,0.85);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--ink-muted);
  backdrop-filter: blur(2px);
}
.dashboard__error {
  color: var(--risk-high);
}
.dashboard__error-detail {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}

@media (max-width: 480px) {
  .dashboard__controls {
    padding: var(--space-3) 0;
  }
  .dashboard__controls-inner {
    padding: 0 var(--space-3);
    gap: var(--space-2);
  }
  .dashboard__body {
    padding: var(--space-3);
    gap: var(--space-3);
  }
  .dashboard__title {
    font-size: var(--text-lg);
  }
  .dashboard__control-row {
    gap: var(--space-3);
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

