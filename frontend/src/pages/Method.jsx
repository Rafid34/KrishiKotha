import React from 'react';
import { useLang, t } from '../i18n/index.jsx';

/** Method and Data page â€” implemented in Phase 12 */
export default function Method() {
  const { lang } = useLang();
  return (
    <div className="page-stub">
      <h1 lang={lang === 'bn' ? 'bn' : undefined}>
        {lang === 'bn' ? 'à¦ªà¦¦à§à¦§à¦¤à¦¿ à¦“ à¦¤à¦¥à§à¦¯' : 'Method & Data'}
      </h1>
      <p className="page-stub__note">Method and Data â€” implemented in Phase 12.</p>
      <p lang={lang === 'bn' ? 'bn' : undefined}>{t('disclaimer', lang)}</p>
    </div>
  );
}

