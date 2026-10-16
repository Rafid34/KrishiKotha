import React from 'react';
import { LEVEL_META, levelLabel } from '../utils/risk.js';
import { LevelIcon } from './RiskBadge.jsx';
import { useLang, t } from '../i18n/index.jsx';

/**
 * Legend — shows the three risk levels with colour, Lucide line icon and label.
 * Placed in the bottom-left corner of the map with dark glass styling.
 */
export default function Legend() {
  const { lang } = useLang();

  return (
    <div className="legend" role="complementary" aria-label={t('map.legend', lang)}>
      <p className="legend__title">{t('map.legend', lang)}</p>
      {Object.entries(LEVEL_META).map(([level, meta]) => (
        <div key={level} className="legend__row">
          <LevelIcon level={level} size={14} />
          <span style={{ color: meta.textColor ?? meta.color, fontWeight: 600, fontSize: 'var(--text-xs)' }}>
            {levelLabel(level, lang)}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `
.legend {
  background: rgba(28, 25, 24, 0.92);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-3) var(--space-4);
  min-width: 120px;
  pointer-events: none;
}
.legend__title {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--space-2);
}
.legend__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 5px;
}
.legend__row:last-child { margin-bottom: 0; }
`;
if (!document.getElementById('legend-styles')) {
  style.id = 'legend-styles';
  document.head.appendChild(style);
}
