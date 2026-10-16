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
      {/* Fixed top bar with 8px blur glassmorphism effect */}
      <header className="layout__header" role="banner">
        <div className="layout__header-inner">
          {/* Logo / brand with circular icon */}
          <a href="/" className="layout__brand" aria-label="Krishi Kotha home">
            <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true" focusable="false" className="layout__logo-icon">
              <circle cx="16" cy="16" r="15" fill="var(--surface-elevated)" stroke="var(--border)" strokeWidth="1" />
              {/* Sprout / seed leaf in Acid Lime */}
              <path
                d="M16 24 C16 24 10 18 10 13 C10 9 13 7 16 7 C19 7 22 9 22 13 C22 18 16 24 16 24Z"
                fill="var(--accent)"
              />
              <circle cx="16" cy="13" r="2.5" fill="var(--bg)" />
            </svg>
            <span className="layout__brand-text">
              <span lang={lang === 'bn' ? 'bn' : 'en'}>{t('appName', lang)}</span>
            </span>
          </a>

          {/* Pill-shaped centre navigation */}
          <nav className="layout__nav-pill" aria-label="Main navigation">
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

          {/* Right actions: language toggle and primary CTA button */}
          <div className="layout__actions">
            <button
              id="lang-toggle"
              className="layout__lang-btn"
              onClick={toggleLang}
              aria-label={`Switch language to ${lang === 'en' ? 'Bangla' : 'English'}`}
              title={`Switch language to ${lang === 'en' ? 'Bangla' : 'English'}`}
            >
              <span aria-hidden="true">{t('lang.toggle', lang)}</span>
            </button>

            {/* Primary Lime CTA Button */}
            <NavLink
              to="/simulator"
              className="layout__cta-btn btn-primary"
              aria-label={t('nav.simulator', lang)}
            >
              <span>{t('nav.simulator', lang)}</span>
            </NavLink>
          </div>
        </div>
      </header>

      {/* Main content with offset for fixed top bar */}
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
  position: relative;
  background-color: var(--bg);
  color: var(--foreground);
}

/* Fixed top bar with glass effect (backdrop-filter blur 8px) */
.layout__header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: rgba(12, 10, 9, 0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
  z-index: 100;
}

.layout__header-inner {
  max-width: 1360px;
  height: 100%;
  margin: 0 auto;
  padding: 0 var(--space-4);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.layout__brand {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--foreground);
  text-decoration: none;
  flex-shrink: 0;
}
.layout__brand:hover,
.layout__brand:focus-visible {
  color: var(--foreground);
  text-decoration: none;
}
.layout__logo-icon {
  flex-shrink: 0;
}
.layout__brand-text {
  font-family: var(--font-serif);
  font-size: var(--text-xl);
  font-weight: 400;
  letter-spacing: -0.01em;
  white-space: nowrap;
}

/* Pill-shaped centre navigation bar */
.layout__nav-pill {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px;
  background: rgba(231, 229, 228, 0.05);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  overflow-x: auto;
  -ms-overflow-style: none;
  scrollbar-width: none;
}
.layout__nav-pill::-webkit-scrollbar { display: none; }

/* Nav links with 300ms transition to #E7E5E4 background with #0C0A09 text */
.layout__nav-link {
  color: var(--ink-muted);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: 500;
  padding: 0 var(--space-4);
  border-radius: var(--radius-full);
  white-space: nowrap;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition), color var(--transition);
}
.layout__nav-link:hover {
  color: #0C0A09;
  background: #E7E5E4;
  text-decoration: none;
}
.layout__nav-link--active {
  color: #0C0A09;
  background: #E7E5E4;
  font-weight: 600;
}
.layout__nav-link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Right actions */
.layout__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.layout__lang-btn {
  background: rgba(255, 255, 255, 0.06);
  color: var(--foreground);
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  padding: 0 var(--space-3);
  font-size: var(--text-sm);
  font-weight: 600;
  min-height: 44px;
  min-width: 44px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background var(--transition), border-color var(--transition);
}
.layout__lang-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.25);
}
.layout__lang-btn:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

/* Primary CTA button on the right */
.layout__cta-btn {
  text-decoration: none;
  white-space: nowrap;
}
.layout__cta-btn:hover {
  text-decoration: none;
}

.layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding-top: 64px; /* Offset for fixed header */
  position: relative;
  z-index: 1;
}

@media (max-width: 1024px) {
  .layout__cta-btn {
    display: none; /* Keep clean space on tablet/mobile */
  }
}

@media (max-width: 640px) {
  .layout__header {
    height: 56px;
  }
  .layout__main {
    padding-top: 56px;
  }
  .layout__brand-text {
    display: none; /* Show icon only on small mobile to maximize nav room */
  }
  .layout__header-inner {
    padding: 0 var(--space-2);
    gap: var(--space-1);
  }
  .layout__nav-pill {
    padding: 2px;
  }
  .layout__nav-link {
    padding: 0 var(--space-2);
    font-size: var(--text-xs);
  }
}
`;
  if (!document.getElementById('layout-styles')) {
    style.id = 'layout-styles';
    document.head.appendChild(style);
  }
}
