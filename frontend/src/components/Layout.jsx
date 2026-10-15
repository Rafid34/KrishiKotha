import React from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useLang, t } from '../i18n/index.jsx';

const NAV_LINKS = [
  { to: '/',          key: 'nav.dashboard' },
  { to: '/replay',   key: 'nav.replay' },
  { to: '/simulator',key: 'nav.simulator' },
  { to: '/method',   key: 'nav.method' },
];

export default function Layout() {
  const { lang, setLang: toggleLang } = useLang();

  return (
    <div className="layout">
      <header className="layout__header" role="banner">
        <div className="layout__header-inner">
          {/* Logo / brand */}
          <a href="/" className="layout__brand" aria-label="Krishi Kotha home">
            <svg width="28" height="28" viewBox="0 0 28 28" aria-hidden="true" focusable="false">
              <circle cx="14" cy="14" r="13" fill="var(--brand)" />
              {/* Simplified leaf/crop icon */}
              <path d="M14 22 C14 22 8 17 8 12 C8 8 11 6 14 6 C17 6 20 8 20 12 C20 17 14 22 14 22Z"
                    fill="white" opacity="0.9"/>
            </svg>
            <span className="layout__brand-text">
              <span lang={lang === 'bn' ? 'bn' : 'en'}>{t('appName', lang)}</span>
            </span>
          </a>

          {/* Main navigation */}
          <nav className="layout__nav" aria-label="Main navigation">
            {NAV_LINKS.map(({ to, key }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  'layout__nav-link' + (isActive ? ' layout__nav-link--active' : '')
                }
                lang={lang === 'bn' ? 'bn' : undefined}
              >
                {t(key, lang)}
              </NavLink>
            ))}
          </nav>

          {/* Language toggle */}
          <button
            id="lang-toggle"
            className="layout__lang-btn"
            onClick={toggleLang}
            aria-label={`Switch language to ${lang === 'en' ? 'Bangla' : 'English'}`}
            title={`Switch language to ${lang === 'en' ? 'Bangla' : 'English'}`}
          >
            <span aria-hidden="true">{t('lang.toggle', lang)}</span>
          </button>
        </div>
      </header>

      <main className="layout__main" id="main-content">
        <Outlet />
      </main>
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100dvh;
}

.layout__header {
  background: var(--brand);
  color: #fff;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-md);
}

.layout__header-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 var(--space-4);
  height: 56px;
  display: flex;
  align-items: center;
  gap: var(--space-4);
}

.layout__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: #fff;
  text-decoration: none;
  flex-shrink: 0;
}
.layout__brand:hover,
.layout__brand:focus-visible {
  color: rgba(255,255,255,0.85);
  text-decoration: none;
}
.layout__brand-text {
  font-size: var(--text-lg);
  font-weight: 700;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

.layout__nav {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex: 1;
  overflow-x: auto;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.layout__nav::-webkit-scrollbar { display: none; }

.layout__nav-link {
  color: rgba(255,255,255,0.80);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: 500;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  white-space: nowrap;
  min-height: 44px;
  display: flex;
  align-items: center;
  transition: background var(--transition), color var(--transition);
}
.layout__nav-link:hover {
  color: #fff;
  background: rgba(255,255,255,0.12);
  text-decoration: none;
}
.layout__nav-link--active {
  color: #fff;
  background: rgba(255,255,255,0.18);
}
.layout__nav-link:focus-visible {
  outline: 3px solid rgba(255,255,255,0.8);
  outline-offset: 2px;
}

.layout__lang-btn {
  margin-left: auto;
  flex-shrink: 0;
  background: rgba(255,255,255,0.15);
  color: #fff;
  border: 1.5px solid rgba(255,255,255,0.40);
  border-radius: var(--radius-full);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: 600;
  min-height: 44px;
  min-width: 44px;
  cursor: pointer;
  transition: background var(--transition), border-color var(--transition);
}
.layout__lang-btn:hover {
  background: rgba(255,255,255,0.25);
  border-color: rgba(255,255,255,0.70);
}
.layout__lang-btn:focus-visible {
  outline: 3px solid rgba(255,255,255,0.8);
  outline-offset: 2px;
}

.layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

@media (max-width: 640px) {
  .layout__brand-text { font-size: var(--text-base); }
  .layout__header-inner { padding: 0 var(--space-3); gap: var(--space-2); }
}
`;
  if (!document.getElementById('layout-styles')) {
    style.id = 'layout-styles';
    document.head.appendChild(style);
  }
}
