import React, { useState, useEffect } from 'react';
import { useLang, t } from '../i18n/index.jsx';
import { getSources, getScoring } from '../api/client.js';
import {
  formatFloodFormula,
  formatDroughtFormula,
  formatSalinityFormula,
  formatThresholds,
  formatSourceDate,
} from '../utils/method.js';
import RiskBadge from '../components/RiskBadge.jsx';
import SerratedDivider from '../components/SerratedDivider.jsx';

/**
 * Method & Data page — Section 8.2 & Phase 12
 * Displays data sources, scoring formulas derived from /api/scoring,
 * risk thresholds, and operational limitations.
 */
export default function Method() {
  const { lang } = useLang();

  const [sources, setSources] = useState(null);
  const [scoring, setScoring] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = () => {
    setLoading(true);
    setError(null);
    Promise.all([getSources(), getScoring()])
      .then(([srcs, scoreData]) => {
        setSources(srcs);
        setScoring(scoreData?.constants || scoreData);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || 'Failed to load method data');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  const isBn = lang === 'bn';

  return (
    <div className="method-page" lang={isBn ? 'bn' : undefined}>
      {/* Header */}
      <header className="method-header">
        <h1 className="method-title">{t('method.title', lang)}</h1>
        <p className="method-subtitle">{t('method.subtitle', lang)}</p>

        {/* Not an official warning disclaimer */}
        <div className="method-disclaimer-banner" role="note">
          <span className="method-disclaimer-icon" aria-hidden="true">⚠️</span>
          <p className="method-disclaimer-text">{t('disclaimer', lang)}</p>
        </div>
      </header>

      <SerratedDivider />

      {/* Loading state */}
      {loading && (
        <div className="method-status card">
          <div className="method-spinner" aria-hidden="true" />
          <p>{t('loading', lang)}</p>
        </div>
      )}

      {/* Error state */}
      {error && !loading && (
        <div className="method-status method-status--error card">
          <p>{t('error', lang)}: {error}</p>
          <button className="method-retry-btn" onClick={fetchData}>
            {isBn ? 'পুনরায় চেষ্টা করুন' : 'Retry'}
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="method-content">
          {/* Section 1: Datasets table */}
          <section className="method-section card" aria-labelledby="method-datasets-heading">
            <h2 id="method-datasets-heading">{t('method.datasetsTitle', lang)}</h2>
            <p className="method-section-desc">{t('method.datasetsDesc', lang)}</p>

            <div className="method-table-wrapper">
              <table className="method-table">
                <thead>
                  <tr>
                    <th scope="col">{t('method.colName', lang)}</th>
                    <th scope="col">{t('method.colShortName', lang)}</th>
                    <th scope="col">{t('method.colVersion', lang)}</th>
                    <th scope="col">{t('method.colResolution', lang)}</th>
                    <th scope="col">{t('method.colLatency', lang)}</th>
                    <th scope="col">{t('method.colLastDate', lang)}</th>
                    <th scope="col">{t('method.colLink', lang)}</th>
                  </tr>
                </thead>
                <tbody>
                  {sources && sources.map(ds => (
                    <tr key={ds.short_name || ds.name}>
                      <td className="method-ds-name">
                        <strong>{ds.name}</strong>
                      </td>
                      <td>
                        <code>{ds.short_name}</code>
                      </td>
                      <td>{ds.version || '—'}</td>
                      <td className="method-ds-meta">{ds.resolution || '—'}</td>
                      <td className="method-ds-meta">{ds.latency || '—'}</td>
                      <td className="method-ds-date">
                        {formatSourceDate(ds.last_data_date, lang)}
                      </td>
                      <td>
                        {ds.url ? (
                          <a
                            href={ds.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="method-link"
                          >
                            {t('method.visitLink', lang)} →
                          </a>
                        ) : (
                          '—'
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Section 2: Formulas as <pre> blocks from /api/scoring constants */}
          <section className="method-section card" aria-labelledby="method-scoring-heading">
            <h2 id="method-scoring-heading">{t('method.scoringTitle', lang)}</h2>
            <p className="method-section-desc">{t('method.scoringDesc', lang)}</p>

            <div className="method-formulas-grid">
              {/* Flood formula */}
              <div className="method-formula-card">
                <h3>{t('method.floodTitle', lang)}</h3>
                <pre className="method-code-block">
                  <code>{formatFloodFormula(scoring)}</code>
                </pre>
              </div>

              {/* Drought formula */}
              <div className="method-formula-card">
                <h3>{t('method.droughtTitle', lang)}</h3>
                <pre className="method-code-block">
                  <code>{formatDroughtFormula(scoring)}</code>
                </pre>
              </div>

              {/* Salinity formula */}
              <div className="method-formula-card">
                <h3>{t('method.salinityTitle', lang)}</h3>
                <pre className="method-code-block">
                  <code>{formatSalinityFormula(scoring)}</code>
                </pre>
              </div>

              {/* Preprocessing card */}
              {scoring?.preprocessing && (
                <div className="method-formula-card">
                  <h3>{lang === 'bn' ? 'প্রাক-প্রক্রিয়াকরণ (Preprocessing)' : 'Rainfall Preprocessing'}</h3>
                  <pre className="method-code-block">
                    <code>
                      {[
                        `wet_day_threshold = ${scoring.preprocessing.wet_day_mm} mm/day`,
                        ``,
                        lang === 'bn'
                          ? '১.০ মিমি-র কম দৈনিক বৃষ্টিপাতকে ০ হিসেবে রূপান্তর করা হয় (ভিত্তি বছর এবং লাইভ উভয় ক্ষেত্রে)।'
                          : 'Daily rainfall < 1.0 mm is set to 0.0 mm in both baseline climatology and live observation feeds.',
                      ].join('\n')}
                    </code>
                  </pre>
                </div>
              )}
            </div>
          </section>

          {/* Section 3: Level thresholds */}
          <section className="method-section card" aria-labelledby="method-thresholds-heading">
            <h2 id="method-thresholds-heading">{t('method.thresholdsTitle', lang)}</h2>
            <p className="method-section-desc">{t('method.thresholdsDesc', lang)}</p>

            <div className="method-thresholds-grid">
              {formatThresholds(scoring).map(item => (
                <div key={item.level} className="method-threshold-card">
                  <div className="method-threshold-badge">
                    <RiskBadge level={item.level} lang={lang} />
                  </div>
                  <div className="method-threshold-range">
                    <code>{item.condition}</code>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Section 4: Limitations list */}
          <section className="method-section card" aria-labelledby="method-limitations-heading">
            <h2 id="method-limitations-heading">{t('method.limitationsTitle', lang)}</h2>
            <p className="method-section-desc">{t('method.limitationsDesc', lang)}</p>

            <ul className="method-limitations-list">
              <li className="method-limitation-item">
                <h4>{t('method.limSalinityProxyTitle', lang)}</h4>
                <p>{t('method.limSalinityProxy', lang)}</p>
              </li>
              <li className="method-limitation-item">
                <h4>{t('method.limBaselineMismatchTitle', lang)}</h4>
                <p>{t('method.limBaselineMismatch', lang)}</p>
              </li>
              <li className="method-limitation-item">
                <h4>{t('method.limResolutionTitle', lang)}</h4>
                <p>{t('method.limResolution', lang)}</p>
              </li>
              <li className="method-limitation-item">
                <h4>{t('method.limAdvisoryOnlyTitle', lang)}</h4>
                <p>{t('method.limAdvisoryOnly', lang)}</p>
              </li>
              <li className="method-limitation-item">
                <h4>{t('method.limObservationOnlyTitle', lang)}</h4>
                <p>{t('method.limObservationOnly', lang)}</p>
              </li>
            </ul>
          </section>
        </div>
      )}
    </div>
  );
}

// Scoped styling using tokens
const METHOD_STYLES = `
.method-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-4) var(--space-12);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.method-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  padding-bottom: var(--space-2);
}

.method-title {
  font-family: var(--font-heading);
  font-size: 2.25rem;
  font-weight: 300;
  color: var(--ink);
  margin: 0;
}

[lang="bn"] .method-title,
.method-title[lang="bn"] {
  font-family: var(--font-bangla-heading);
  font-weight: 600;
}

.method-subtitle {
  font-size: var(--text-base);
  color: var(--ink-muted);
  margin: 0;
}

.method-disclaimer-banner {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  background: rgba(251, 191, 36, 0.08);
  border: 1px solid var(--risk-moderate);
  border-left: 4px solid var(--risk-moderate);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
}

.method-disclaimer-icon {
  font-size: var(--text-xl);
}

.method-disclaimer-text {
  font-size: var(--text-sm);
  font-weight: 600;
  color: #FDE68A;
  margin: 0;
}

.method-status {
  text-align: center;
  padding: var(--space-8);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  background: var(--surface-primary);
  border: 1px solid var(--border);
  border-radius: 24px;
}

.method-status--error {
  border: 1px solid var(--risk-high);
  color: #FCA5A5;
}

.method-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: method-spin 0.8s linear infinite;
}

@keyframes method-spin {
  to { transform: rotate(360deg); }
}

.method-retry-btn {
  background: var(--accent);
  color: #0C0A09;
  padding: 8px 24px;
  border: none;
  border-radius: 9999px;
  font-weight: 700;
  font-size: var(--text-sm);
  min-height: 44px;
  cursor: pointer;
  transition: opacity var(--transition);
}

.method-retry-btn:hover {
  opacity: 0.9;
}

.method-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.method-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  background: var(--surface-primary);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: var(--space-6);
}

.method-section h2 {
  font-family: var(--font-heading);
  font-size: var(--text-xl);
  font-weight: 400;
  color: var(--ink);
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--space-3);
  margin: 0;
}

[lang="bn"] .method-section h2,
.method-section h2[lang="bn"] {
  font-family: var(--font-bangla-heading);
  font-weight: 600;
}

.method-section-desc {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  margin: 0;
}

.method-table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-secondary);
}

.method-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: var(--text-sm);
}

.method-table th,
.method-table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}

.method-table th {
  background: var(--surface-secondary);
  font-weight: 600;
  color: var(--ink);
  white-space: nowrap;
}

.method-table tbody tr:last-child td {
  border-bottom: none;
}

.method-table tbody tr:hover {
  background: var(--surface-elevated);
}

.method-ds-name {
  min-width: 200px;
}

.method-ds-meta {
  color: var(--ink-muted);
  font-size: var(--text-xs);
  max-width: 240px;
}

.method-ds-date {
  white-space: nowrap;
  font-weight: 500;
  color: var(--ink);
}

.method-link {
  color: var(--accent);
  font-weight: 600;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  min-height: 44px;
}

.method-link:hover {
  text-decoration: underline;
}

.method-formulas-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.method-formula-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  background: var(--surface-secondary);
}

.method-formula-card h3 {
  font-family: var(--font-heading);
  font-size: var(--text-base);
  font-weight: 400;
  margin-bottom: var(--space-2);
  color: var(--accent);
}

[lang="bn"] .method-formula-card h3,
.method-formula-card h3[lang="bn"] {
  font-family: var(--font-bangla-heading);
  font-weight: 600;
}

.method-code-block {
  background: #0C0A09;
  color: #E7E5E4;
  border: 1px solid var(--border);
  padding: var(--space-4);
  border-radius: var(--radius-md);
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
  margin: 0;
  white-space: pre;
}

.method-thresholds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-4);
}

.method-threshold-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--surface-secondary);
}

.method-threshold-range code {
  font-family: var(--font-mono);
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--ink);
  background: var(--surface-primary);
  border: 1px solid var(--border);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
}

.method-limitations-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: 0;
  margin: 0;
}

.method-limitation-item {
  border-left: 3px solid var(--accent);
  padding-left: var(--space-4);
}

.method-limitation-item h4 {
  font-family: var(--font-heading);
  font-size: var(--text-base);
  font-weight: 400;
  color: var(--ink);
  margin-bottom: var(--space-1);
}

[lang="bn"] .method-limitation-item h4,
.method-limitation-item h4[lang="bn"] {
  font-family: var(--font-bangla-heading);
  font-weight: 600;
}

.method-limitation-item p {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  line-height: 1.6;
  margin: 0;
}

@media (max-width: 768px) {
  .method-page {
    padding: var(--space-4) var(--space-3) var(--space-8);
  }
}
`;
if (typeof document !== 'undefined' && !document.getElementById('method-page-styles')) {
  const style = document.createElement('style');
  style.id = 'method-page-styles';
  style.textContent = METHOD_STYLES;
  document.head.appendChild(style);
}

