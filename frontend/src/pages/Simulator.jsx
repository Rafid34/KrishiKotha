import React from 'react';
import { useLang, t } from '../i18n/index.jsx';

/** Farmer Simulator page â€” implemented in Phase 9 */
export default function Simulator() {
  const { lang } = useLang();
  return (
    <div className="page-stub">
      <h1 lang={lang === 'bn' ? 'bn' : undefined}>
        {lang === 'bn' ? 'à¦•à§ƒà¦·à¦• à¦¸à¦¿à¦®à§à¦²à§‡à¦Ÿà¦°' : 'Farmer Simulator'}
      </h1>
      <p className="page-stub__note">Farmer Simulator â€” implemented in Phase 9.</p>
      <p lang={lang === 'bn' ? 'bn' : undefined}>{t('disclaimer', lang)}</p>
    </div>
  );
}

