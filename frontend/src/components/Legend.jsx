import React from 'react';
import { LEVEL_META, levelLabel } from '../utils/risk.js';
import { LevelIcon } from './RiskBadge.jsx';
import { useLang, t } from '../i18n/index.jsx';

/**
 * Legend â€” shows the three risk levels with colour, icon and label.
 * Placed in the bottom-left corner of the map.
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

/* â”€â”€â”€ Styles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ */
const style = document.createElement('style');
style.textContent = `
.legend {
  background: var(--surface);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-3) var(--space-4);
  min-width: 110px;
  pointer-events: none;
}
.legend__title {
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: var(--space-2);
}
.legend__row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: 4px;
}
.legend__row:last-child { margin-bottom: 0; }
`;
if (!document.getElementById('legend-styles')) {
  style.id = 'legend-styles';
  document.head.appendChild(style);
}

