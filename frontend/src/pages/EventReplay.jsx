import React from 'react';
import { useLang, t } from '../i18n/index.jsx';

/** Event Replay page â€” implemented in Phase 8 */
export default function EventReplay() {
  const { lang } = useLang();
  return (
    <div className="page-stub">
      <h1 lang={lang === 'bn' ? 'bn' : undefined}>
        {lang === 'bn' ? 'à¦¸à¦¿à¦²à§‡à¦Ÿ à¦¬à¦¨à§à¦¯à¦¾, à¦œà§à¦¨ à§¨à§¦à§¨à§¨' : 'Sylhet floods, June 2022'}
      </h1>
      <p className="page-stub__note">Event Replay â€” implemented in Phase 8.</p>
      <p lang={lang === 'bn' ? 'bn' : undefined}>{t('disclaimer', lang)}</p>
    </div>
  );
}

const style = document.createElement('style');
style.textContent = `
.page-stub {
  max-width: 800px;
  margin: var(--space-12) auto;
  padding: 0 var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
.page-stub h1 { color: var(--brand); }
.page-stub__note { font-size: var(--text-sm); color: var(--ink-muted); font-style: italic; }
`;
if (!document.getElementById('page-stub-styles')) {
  style.id = 'page-stub-styles';
  document.head.appendChild(style);
}

