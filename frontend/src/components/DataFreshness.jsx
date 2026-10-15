import React from 'react';
import { useLang, t } from '../i18n/index.jsx';
import { formatDate } from '../utils/format.js';

/**
 * DataFreshness — shows the data source and last data date for the
 * currently displayed risk snapshot.
 *
 * @param {{ sources: object|null }} props
 *   sources = { rain: { name, data_date }, soil: { name, data_date }, tmax: { name, data_date } }
 */
export default function DataFreshness({ sources }) {
  const { lang } = useLang();

  if (!sources) return null;

  const items = [
    { key: 'rain', label: t('fresh.rain', lang), source: sources.rain },
    { key: 'soil', label: t('fresh.soil', lang), source: sources.soil },
    { key: 'tmax', label: t('fresh.tmax', lang), source: sources.tmax },
  ].filter(item => item.source);

  return (
    <div className="data-freshness" aria-label={t('dashboard.dataFreshness', lang)}>
      {items.map(({ key, label, source }) => (
        <span key={key} className="data-freshness__item">
          <span className="data-freshness__label">{label}</span>
          {' '}
          <span className="data-freshness__date" lang={lang === 'bn' ? 'bn' : undefined}>
            {formatDate(source.data_date, lang)}
          </span>
        </span>
      ))}
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.data-freshness {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  font-size: var(--text-xs);
  color: var(--ink-muted);
  padding: var(--space-1) 0;
}
.data-freshness__label {
  font-weight: 500;
}
.data-freshness__date {
  color: var(--nasa-blue);
  font-weight: 600;
}
`;
  if (!document.getElementById('data-freshness-styles')) {
    style.id = 'data-freshness-styles';
    document.head.appendChild(style);
  }
}
