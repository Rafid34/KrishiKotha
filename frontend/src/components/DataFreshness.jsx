import React from 'react';
import { useLang, t } from '../i18n/index.jsx';
import { formatDate } from '../utils/format.js';

/**
 * DataFreshness — non-critical callout styled as a Sticky Note card.
 * Adheres to DESIGN_REFERENCE.json:
 * Background: #D4F268 (Acid Lime), Text: #1C1917 (Warm Charcoal), subtle rotation on desktop.
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
    <div className="data-freshness sticky-note data-freshness--sticky" aria-label={t('dashboard.dataFreshness', lang)}>
      <div className="data-freshness__header">
        <span className="data-freshness__pin" aria-hidden="true">📌</span>
        <strong className="data-freshness__title">{t('dashboard.dataFreshness', lang)}</strong>
      </div>
      <div className="data-freshness__items">
        {items.map(({ key, label, source }) => (
          <span key={key} className="data-freshness__item">
            <span className="data-freshness__label">{label}:</span>{' '}
            <span className="data-freshness__date" lang={lang === 'bn' ? 'bn' : undefined}>
              {formatDate(source.data_date, lang)}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.data-freshness--sticky {
  background: var(--sticky-bg);
  color: var(--sticky-text);
  border-radius: var(--radius-lg);
  padding: var(--space-3) var(--space-5);
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
  transform: rotate(1deg);
  transition: transform var(--transition), box-shadow var(--transition);
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: fit-content;
}

.data-freshness--sticky:hover {
  transform: rotate(0deg) scale(1.02);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45);
}

.data-freshness__header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-serif);
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--sticky-text);
}

.data-freshness__pin {
  font-size: 14px;
}

.data-freshness__items {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  color: var(--sticky-text);
}

.data-freshness__label {
  font-weight: 600;
  opacity: 0.9;
}

.data-freshness__date {
  font-family: var(--font-mono);
  font-weight: 700;
  background: rgba(28, 25, 24, 0.12);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

@media (max-width: 640px) {
  .data-freshness--sticky {
    transform: none !important;
    max-width: 100%;
    padding: var(--space-3);
  }
}

@media (prefers-reduced-motion: reduce) {
  .data-freshness--sticky {
    transform: none !important;
    transition: none !important;
  }
}
`;
  if (!document.getElementById('data-freshness-styles')) {
    style.id = 'data-freshness-styles';
    document.head.appendChild(style);
  }
}
