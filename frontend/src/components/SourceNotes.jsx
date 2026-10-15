import React from 'react';
import { t } from '../i18n/index.jsx';
import { formatNumber } from '../utils/format.js';

/**
 * Provenance notes under the "why this score" title (Phase 10):
 * - which soil input fed flood/drought (SMAP L4, or POWER as the fallback, F2.1);
 * - the NDVI anomaly with product and version, or the Level 1 salinity fallback (F2.2).
 * Styles live in FactorBars.jsx (`.factor-note*`).
 */
export default function SourceNotes({ hazard, soilSource, ndvi, lang }) {
  const bn = lang === 'bn' ? 'bn' : undefined;
  const showSoil = (hazard === 'flood' || hazard === 'drought') && soilSource;
  const showNdvi = hazard === 'salt' && ndvi;
  return (
    <>
      {showSoil && (
        <p
          className={`factor-note ${soilSource.fallback ? 'factor-note--fallback' : ''}`}
          data-testid="soil-source-note"
          lang={bn}
        >
          <strong>{t('districtPanel.soilSource', lang)}:</strong>{' '}
          {soilSource.fallback ? t('districtPanel.soilSourcePower', lang) : t('districtPanel.soilSourceSmap', lang)}
          {soilSource.version ? ` (${soilSource.version})` : ''}
        </p>
      )}
      {showNdvi && (
        <p className={`factor-note ${ndvi.used ? '' : 'factor-note--fallback'}`} data-testid="ndvi-note" lang={bn}>
          {ndvi.used ? (
            <>
              <strong>{t('districtPanel.ndviUsed', lang)}:</strong>{' '}
              {formatNumber(ndvi.anomaly, 3, lang)} • {ndvi.product}
              {ndvi.version ? ` (v${ndvi.version})` : ''}
            </>
          ) : (
            t('districtPanel.ndviFallback', lang)
          )}
        </p>
      )}
    </>
  );
}
