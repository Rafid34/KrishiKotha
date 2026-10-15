import React from 'react';
import RiskBadge, { LevelIcon } from './RiskBadge.jsx';
import { useLang, t } from '../i18n/index.jsx';
import { formatNumber, formatDate } from '../utils/format.js';
import { hazardLabel } from '../utils/risk.js';

const HAZARDS = ['drought', 'flood', 'salt'];

/**
 * DistrictPanel â€” right-hand panel showing three score cards for a district.
 * Phase 7 scope: name, three score cards with badge, score number.
 * Phase 8 will add TrendChart, FactorBars and advice.
 *
 * @param {{
 *   district: object|null,
 *   riskEntry: object|null,
 *   date: string|null,
 * }} props
 */
export default function DistrictPanel({ district, riskEntry, date }) {
  const { lang } = useLang();

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
            {districtNameAlt}
          </p>
        </div>
        {date && (
          <time className="district-panel__date" dateTime={date} lang={lang === 'bn' ? 'bn' : undefined}>
            {formatDate(date, lang)}
          </time>
        )}
      </div>

      {/* Score cards */}
      <div className="district-panel__scores" aria-label={t('districtPanel.scores', lang)}>
        {HAZARDS.map(hazard => {
          const data = riskEntry?.[hazard];
          const level = data?.level ?? 'low';
          const score = data?.score;
          return (
            <ScoreCard
              key={hazard}
              hazard={hazard}
              level={level}
              score={score}
              lang={lang}
            />
          );
        })}
      </div>

      {/* Disclaimer â€” required on every screen per Â§8.4 */}
      <p className="district-panel__disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
        {t('disclaimer', lang)}
      </p>
    </div>
  );
}

function ScoreCard({ hazard, level, score, lang }) {
  const label = hazardLabel(hazard, lang);
  const scoreStr = score != null ? formatNumber(score, 1, lang) : 'â€”';

  return (
    <div
      className={`score-card score-card--${level}`}
      style={{ '--card-color': `var(--risk-${level})` }}
    >
      <div className="score-card__hazard-label" lang={lang === 'bn' ? 'bn' : undefined}>
        {label}
      </div>
      <div className="score-card__score" aria-label={`Score: ${score ?? 'unavailable'}`}>
        {scoreStr}
      </div>
      <RiskBadge level={level} score={score} lang={lang} />
    </div>
  );
}

/* â”€â”€â”€ Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const style = document.createElement('style');
style.textContent = `
.district-panel {
  background: var(--surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-5);
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
.district-panel__empty-text { font-size: var(--text-sm); max-width: 200px; }

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
}
.district-panel__name-alt {
  font-size: var(--text-sm);
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
  gap: var(--space-3);
}

.score-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  background: color-mix(in srgb, var(--card-color) 6%, var(--bg));
  border: 1.5px solid color-mix(in srgb, var(--card-color) 20%, transparent);
  border-radius: var(--radius-md);
  padding: var(--space-4) var(--space-3);
  text-align: center;
  transition: border-color var(--transition);
}
.score-card:hover {
  border-color: color-mix(in srgb, var(--card-color) 45%, transparent);
}

.score-card__hazard-label {
  font-size: var(--text-xs);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  color: var(--ink-muted);
}
.score-card__score {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--card-color);
  line-height: 1;
}

.district-panel__disclaimer {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  border-top: 1px solid var(--border);
  padding-top: var(--space-3);
  margin-top: auto;
}

@media (max-width: 480px) {
  .district-panel {
    padding: var(--space-4);
  }
  .district-panel__scores {
    gap: var(--space-2);
  }
  .score-card {
    padding: var(--space-3) var(--space-1);
  }
}

@media (max-width: 360px) {
  .district-panel {
    padding: var(--space-3);
  }
  .district-panel__scores {
    grid-template-columns: repeat(3, 1fr);
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

