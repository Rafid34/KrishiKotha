import React from 'react';
import { t } from '../i18n/index.jsx';
import { GIBS_LAYERS, overlayMessageKey } from '../config/layers.js';

/**
 * NASA GIBS overlay chooser (native radios, keyboard accessible). Shows the attribution while a
 * layer is selected, and the fallback message when that layer has no imagery for the date or its
 * tiles fail to load. Styles live in RiskMap.jsx (`.overlay-control*`).
 */
export default function OverlayControl({ value, onChange, status, tileError, layer, lang }) {
  const messageKey = overlayMessageKey(status, tileError);
  const message = messageKey
    ? t(messageKey, lang).replace('{start}', layer?.coverageStart ?? '')
    : null;
  return (
    <fieldset className="overlay-control" lang={lang === 'bn' ? 'bn' : undefined}>
      <legend className="overlay-control__title">{t('overlay.title', lang)}</legend>
      <label className="overlay-control__option">
        <input type="radio" name="gibs-overlay" value="none" checked={value === 'none'} onChange={() => onChange('none')} />
        {t('overlay.none', lang)}
      </label>
      {GIBS_LAYERS.map(l => (
        <label key={l.key} className="overlay-control__option">
          <input type="radio" name="gibs-overlay" value={l.key} checked={value === l.key} onChange={() => onChange(l.key)} />
          {l.label[lang] ?? l.label.en}
        </label>
      ))}
      {value !== 'none' && (
        <p className="overlay-control__credit" data-testid="gibs-credit">{t('overlay.credit', lang)}</p>
      )}
      {message && (
        <p className="overlay-control__fallback" role="status" data-testid="gibs-fallback">{message}</p>
      )}
    </fieldset>
  );
}
