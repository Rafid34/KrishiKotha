import React, { useState, useEffect } from 'react';
import RiskBadge from './RiskBadge.jsx';
import TrendChart from './TrendChart.jsx';
import FactorBars from './FactorBars.jsx';
import { useLang, t } from '../i18n/index.jsx';
import { formatNumber, formatDate } from '../utils/format.js';
import { hazardLabel } from '../utils/risk.js';
import { getRiskSeries, getRiskExplain, postAdvice, getCrops } from '../api/client.js';

const HAZARDS = ['drought', 'flood', 'salt'];

/**
 * DistrictPanel — comprehensive detail panel for a selected district.
 * Implements Section 8.2 & Task 8.1:
 * - District names (both languages)
 * - Three score cards with RiskBadge
 * - 60-day rainfall trend & soil moisture chart (TrendChart)
 * - "Why this score" factor bars from /explain (FactorBars)
 * - "Advice for farmers" section with crop selector & live advice
 * - Data sources & mandatory disclaimer
 *
 * @param {{
 *   district: object|null,
 *   riskEntry: object|null,
 *   date: string|null,
 * }} props
 */
export default function DistrictPanel({ district, riskEntry, date }) {
  const { lang } = useLang();

  const [selectedHazard, setSelectedHazard] = useState('flood');
  const [selectedCrop, setSelectedCrop] = useState('aman');
  const [crops, setCrops] = useState([]);
  const [seriesData, setSeriesData] = useState([]);
  const [explainData, setExplainData] = useState(null);
  const [adviceData, setAdviceData] = useState(null);
  const [loadingData, setLoadingData] = useState(false);

  // Load crop options once
  useEffect(() => {
    getCrops()
      .then(setCrops)
      .catch(() => {
        setCrops([
          { id: 'aman', name_en: 'Aman rice', name_bn: 'আমন ধান' },
          { id: 'boro', name_en: 'Boro rice', name_bn: 'বোরো ধান' },
          { id: 'aus', name_en: 'Aus rice', name_bn: 'আউশ ধান' },
        ]);
      });
  }, []);

  // Fetch 60-day series, explain factors, and advice when district or date changes
  useEffect(() => {
    if (!district?.id) {
      setSeriesData([]);
      setExplainData(null);
      setAdviceData(null);
      return;
    }

    setLoadingData(true);

    // 1. 60-day series
    getRiskSeries(district.id, { date, days: 60 })
      .then(res => setSeriesData(res.series || []))
      .catch(() => setSeriesData([]));

    // 2. Explain factors
    getRiskExplain(district.id, { date })
      .then(setExplainData)
      .catch(() => setExplainData(null));

    // 3. Advice for farmers
    postAdvice({
      district_id: district.id,
      crop_id: selectedCrop,
      date: date || undefined,
      language: lang,
    })
      .then(setAdviceData)
      .catch(() => setAdviceData(null))
      .finally(() => setLoadingData(false));
  }, [district?.id, date, selectedCrop, lang]);

  if (!district) {
    return (
      <div className="district-panel district-panel--empty" role="status">
        <div className="district-panel__empty-icon" aria-hidden="true">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <circle cx="24" cy="24" r="22" stroke="var(--border)" strokeWidth="2"/>
            <path d="M16 28C16 28 18 32 24 32C30 32 32 28 32 28" stroke="var(--ink-muted)" strokeWidth="2" strokeLinecap="round"/>
            <circle cx="19" cy="21" r="2" fill="var(--ink-muted)"/>
            <circle cx="29" cy="21" r="2" fill="var(--ink-muted)"/>
          </svg>
        </div>
        <p className="district-panel__empty-text" lang={lang === 'bn' ? 'bn' : undefined}>
          {t('dashboard.selectDistrict', lang)}
        </p>
      </div>
    );
  }

  const districtName = lang === 'bn' ? district.name_bn : district.name_en;
  const districtNameAlt = lang === 'bn' ? district.name_en : district.name_bn;

  return (
    <div className="district-panel" role="region" aria-label={`${district.name_en} risk detail`}>
      {/* Header */}
      <div className="district-panel__header">
        <div>
          <h2 className="district-panel__name" lang={lang === 'bn' ? 'bn' : undefined}>
            {districtName}
          </h2>
          <p className="district-panel__name-alt" lang={lang === 'bn' ? undefined : 'bn'}>
            {districtNameAlt} • {district.division}
          </p>
        </div>
        {date && (
          <time className="district-panel__date" dateTime={date} lang={lang === 'bn' ? 'bn' : undefined}>
            {formatDate(date, lang)}
          </time>
        )}
      </div>

      {/* Score cards (clickable to switch factor view) */}
      <div className="district-panel__scores" aria-label={t('districtPanel.scores', lang)}>
        {HAZARDS.map(h => {
          const data = riskEntry?.[h];
          const level = data?.level ?? 'low';
          const score = data?.score;
          const isSelected = selectedHazard === h;
          return (
            <button
              type="button"
              key={h}
              className={`score-card score-card--${level} ${isSelected ? 'score-card--selected' : ''}`}
              style={{ '--card-color': level === 'moderate' ? 'var(--risk-moderate-text)' : `var(--risk-${level})` }}
              onClick={() => setSelectedHazard(h)}
              aria-pressed={isSelected}
              aria-label={`${hazardLabel(h, lang)}: ${score ?? 'unavailable'}, ${level}`}
            >
              <span className="score-card__hazard-label" lang={lang === 'bn' ? 'bn' : undefined}>
                {hazardLabel(h, lang)}
              </span>
              <span className="score-card__score">
                {score != null ? formatNumber(score, 1, lang) : '—'}
              </span>
              <RiskBadge level={level} score={score} lang={lang} />
            </button>
          );
        })}
      </div>

      {/* Trend Chart (60-day rainfall bars, 90th percentile baseline, soil moisture) */}
      <div className="district-panel__section">
        <TrendChart series={seriesData} districtId={district.id} />
      </div>

      {/* Why this score factor breakdown from /explain */}
      <div className="district-panel__section">
        <FactorBars explain={explainData} hazard={selectedHazard} />
      </div>

      {/* Advice for farmers section */}
      <div className="district-panel__section district-advice">
        <div className="district-advice__header">
          <h3 className="district-advice__title" lang={lang === 'bn' ? 'bn' : undefined}>
            {t('districtPanel.advice', lang)}
          </h3>
          <div className="district-advice__crop-picker">
            <label htmlFor="advice-crop-select" className="district-advice__crop-label" lang={lang === 'bn' ? 'bn' : undefined}>
              {t('districtPanel.selectCrop', lang)}:
            </label>
            <select
              id="advice-crop-select"
              value={selectedCrop}
              onChange={e => setSelectedCrop(e.target.value)}
              className="district-advice__select"
            >
              {crops.map(c => (
                <option key={c.id} value={c.id}>
                  {lang === 'bn' ? c.name_bn : c.name_en}
                </option>
              ))}
            </select>
          </div>
        </div>

        {adviceData ? (
          <div className="district-advice__card">
            <div className="district-advice__rule-tag">
              <code>{adviceData.rule_id}</code>
            </div>
            <p className="district-advice__bn" lang="bn">
              {adviceData.text_bn}
            </p>
            <p className="district-advice__en">
              {adviceData.text_en}
            </p>
          </div>
        ) : (
          <p className="district-advice__loading">{t('loading', lang)}</p>
        )}
      </div>

      {/* Disclaimer — required on every screen per Section 8.4 */}
      <p className="district-panel__disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
        {t('disclaimer', lang)}
      </p>
    </div>
  );
}

/* ─── Styles ───────────────────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `
.district-panel {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-4);
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  overflow-y: auto;
}

.district-panel--empty {
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--space-4);
  color: var(--ink-muted);
  min-height: 200px;
}
.district-panel__empty-icon { opacity: 0.5; }
.district-panel__empty-text { font-size: var(--text-sm); max-width: 220px; }

.district-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}
.district-panel__name {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}
.district-panel__name-alt {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  margin-top: 2px;
}
.district-panel__date {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  white-space: nowrap;
  background: var(--bg);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  flex-shrink: 0;
}

.district-panel__scores {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: color-mix(in srgb, var(--card-color) 6%, var(--bg));
  border: 1.5px solid color-mix(in srgb, var(--card-color) 25%, transparent);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-2);
  text-align: center;
  cursor: pointer;
  transition: all var(--transition);
  font-family: inherit;
}
.score-card:hover {
  border-color: var(--card-color);
  background: color-mix(in srgb, var(--card-color) 12%, var(--bg));
}
.score-card--selected {
  border-color: var(--card-color);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--card-color) 40%, transparent);
}
.score-card:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 2px;
}

.score-card__hazard-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--ink-muted);
}
.score-card__score {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--card-color);
  line-height: 1;
}

.district-panel__section {
  display: flex;
  flex-direction: column;
}

/* Advice card */
.district-advice {
  background: var(--bg);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  border: 1px solid var(--border);
  gap: var(--space-2);
}
.district-advice__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.district-advice__title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}
.district-advice__crop-picker {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}
.district-advice__crop-label {
  font-size: 11px;
  color: var(--ink-muted);
}
.district-advice__select {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--ink);
  cursor: pointer;
}
.district-advice__select:focus-visible {
  outline: 2px solid var(--brand);
}

.district-advice__card {
  background: var(--surface);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.district-advice__rule-tag code {
  font-size: 10px;
  background: color-mix(in srgb, var(--brand) 10%, transparent);
  color: var(--brand);
  padding: 2px 5px;
  border-radius: var(--radius-sm);
}
.district-advice__bn {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink);
  line-height: 1.5;
  margin: 0;
}
.district-advice__en {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  font-style: italic;
  line-height: 1.4;
  margin: 0;
}
.district-advice__loading {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  margin: var(--space-2) 0;
}

.district-panel__disclaimer {
  font-size: 11px;
  color: var(--ink-muted);
  border-top: 1px solid var(--border);
  padding-top: var(--space-3);
  margin-top: auto;
}

@media (max-width: 480px) {
  .district-panel {
    padding: var(--space-3);
  }
  .district-panel__scores {
    gap: 4px;
  }
  .score-card {
    padding: var(--space-2) 2px;
  }
  .score-card__score {
    font-size: var(--text-xl);
  }
}
`;
if (!document.getElementById('district-panel-styles')) {
  style.id = 'district-panel-styles';
  document.head.appendChild(style);
}
