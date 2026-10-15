import React from 'react';
import { useLang, t } from '../i18n/index.jsx';
import { formatNumber } from '../utils/format.js';
import { hazardLabel } from '../utils/risk.js';
import SourceNotes from './SourceNotes.jsx';

const FACTOR_NAMES = {
  rain3_pctl: { en: '3-Day Rainfall Percentile', bn: '৩ দিনের বৃষ্টি পারসেন্টাইল' },
  rain7_pctl: { en: '7-Day Rainfall Percentile', bn: '৭ দিনের বৃষ্টি পারসেন্টাইল' },
  soil_pctl: { en: 'Root Zone Soil Moisture', bn: 'মাটির মূল অঞ্চলের আর্দ্রতা' },
  seasonal_intrusion: { en: 'Seasonal Salinity Index', bn: 'মৌসুমী লবণাক্ততা সূচক' },
  rain_deficit: { en: '30-Day Rainfall Deficit', bn: '৩০ দিনের বৃষ্টির ঘাটতি' },
  heat_anomaly: { en: '7-Day Temperature Anomaly', bn: '৭ দিনের তাপমাত্রার অসঙ্গতি' },
  // Matches the input name emitted by `score_salt` in the backend (`vegetation_anomaly`).
  vegetation_anomaly: { en: 'Vegetation Health Anomaly (NDVI)', bn: 'উদ্ভিদ স্বাস্থ্য অসঙ্গতি (NDVI)' },
};

/**
 * FactorBars — displays weighted input components and provenance behind a risk score.
 *
 * @param {{
 *   explain: object|null,
 *   hazard: string,
 * }} props
 */
export default function FactorBars({ explain, hazard }) {
  const { lang } = useLang();

  if (!explain) {
    return (
      <div className="factor-bars factor-bars--empty">
        <p className="factor-bars__muted">{t('loading', lang)}</p>
      </div>
    );
  }

  const hazardBlock = explain[hazard];
  const inputs = hazardBlock?.inputs ?? [];
  const coastal = hazardBlock?.coastal_factor ?? null;
  const isDegraded = explain.degraded;


  return (
    <section className="factor-bars" aria-label={t('districtPanel.whyScore', lang)}>
      <div className="factor-bars__header">
        <h3 className="factor-bars__title" lang={lang === 'bn' ? 'bn' : undefined}>
          {t('districtPanel.whyScore', lang)} — {hazardLabel(hazard, lang)}
        </h3>
        {isDegraded && (
          <span className="factor-bars__degraded-badge" title="Missing input fallback">
            {t('districtPanel.fallbackUsed', lang)}
          </span>
        )}
      </div>

      {/* Source notes: show which soil input was used and any NDVI fallback (F2.1, F2.2) */}
      <SourceNotes
        hazard={hazard}
        soilSource={explain.soil_source ?? null}
        ndvi={explain.ndvi ?? null}
        lang={lang}
      />

      <div className="factor-bars__list">
        {inputs.map((item, idx) => {
          const nameObj = FACTOR_NAMES[item.name];
          const nameLabel = nameObj ? (lang === 'bn' ? nameObj.bn : nameObj.en) : item.name;
          const weightPct = Math.round((item.weight ?? 0) * 100);
          const val = item.value != null ? Math.min(100, Math.max(0, item.value)) : 0;
          const rawStr = item.raw != null ? formatNumber(item.raw, 1, lang) : null;

          return (
            <div key={item.name || idx} className="factor-item">
              <div className="factor-item__top">
                <span className="factor-item__name" lang={lang === 'bn' ? 'bn' : undefined}>
                  {nameLabel}
                </span>
                <div className="factor-item__meta">
                  {rawStr != null && (
                    <span className="factor-item__raw">
                      raw: {rawStr}
                    </span>
                  )}
                  <span className="factor-item__weight">
                    {weightPct}%
                  </span>
                </div>
              </div>

              {/* Progress bar */}
              <div
                className="factor-item__bar-track"
                role="progressbar"
                aria-valuenow={Math.round(val)}
                aria-valuemin="0"
                aria-valuemax="100"
                aria-label={`${nameLabel}: ${Math.round(val)}%`}
              >
                <div
                  className="factor-item__bar-fill"
                  style={{ width: `${val}%` }}
                />
              </div>

              {/* Source & Date provenance */}
              {(item.source || item.data_date) && (
                <div className="factor-item__source">
                  <span>{item.source}</span>
                  {item.data_date && <span> • {item.data_date}</span>}
                </div>
              )}
            </div>
          );
        })}

        {/* Coastal factor multiplier (salinity only) */}
        {coastal && (
          <div className="factor-coastal">
            <div className="factor-coastal__header">
              <span className="factor-coastal__label" lang={lang === 'bn' ? 'bn' : undefined}>
                {t('districtPanel.coastalProximity', lang)}
              </span>
              <span className="factor-coastal__multiplier">
                {coastal.multiplier != null ? `${coastal.multiplier}×` : '—'}
              </span>
            </div>
            <p className="factor-coastal__detail">
              {t('districtPanel.distance', lang)}: {coastal.raw != null ? `${coastal.raw} km` : '—'} • sub-score: {coastal.value != null ? Math.round(coastal.value) : '—'}/100
            </p>
            {coastal.source && (
              <p className="factor-item__source">{coastal.source}</p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

/* ─── Styles ───────────────────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `
.factor-bars {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  background: var(--bg);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  border: 1px solid var(--border);
}
.factor-bars--empty {
  min-height: 80px;
  align-items: center;
  justify-content: center;
}
.factor-bars__muted {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}
.factor-bars__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.factor-bars__title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}
.factor-bars__degraded-badge {
  font-size: 11px;
  background: #FFF3CD;
  color: #856404;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid #FFEBAA;
  font-weight: 500;
}

.factor-bars__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.factor-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.factor-item__top {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: var(--space-2);
}
.factor-item__name {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--ink);
}
.factor-item__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.factor-item__raw {
  font-size: 11px;
  color: var(--ink-muted);
  font-family: monospace;
}
.factor-item__weight {
  font-size: 11px;
  font-weight: 700;
  color: var(--brand);
  background: color-mix(in srgb, var(--brand) 10%, transparent);
  padding: 1px 5px;
  border-radius: var(--radius-sm);
}

.factor-item__bar-track {
  height: 7px;
  background: var(--surface);
  border-radius: 4px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.factor-item__bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--brand), color-mix(in srgb, var(--brand) 70%, var(--risk-high)));
  border-radius: 4px;
  transition: width 0.3s ease;
}

.factor-item__source {
  font-size: 10px;
  color: var(--ink-muted);
  letter-spacing: 0.02em;
}

.factor-note {
  font-size: 11px;
  color: var(--ink-muted);
  margin: 0;
}
.factor-note--fallback {
  background: #FFF3CD;
  color: #856404;
  border: 1px solid #FFEBAA;
  border-radius: var(--radius-sm);
  padding: 3px 6px;
}

.factor-coastal {
  background: var(--surface);
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  margin-top: var(--space-1);
}
.factor-coastal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.factor-coastal__label {
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--ink);
}
.factor-coastal__multiplier {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--brand);
}
.factor-coastal__detail {
  font-size: 11px;
  color: var(--ink-muted);
  margin-top: 2px;
}
`;
if (!document.getElementById('factor-bars-styles')) {
  style.id = 'factor-bars-styles';
  document.head.appendChild(style);
}
