import React from 'react';
import { useLang, t } from '../i18n/index.jsx';
import { HAZARD_LABELS } from '../utils/risk.js';

const HAZARDS = ['drought', 'flood', 'salt'];

/**
 * HazardToggle — folder-style tabs for hazard selection.
 * Remains a real native radio group with keyboard arrow-key behaviour and visible focus ring.
 * Spec & Reference: slight rotation (-2 to -1 deg) removed below 640px and on reduced motion.
 */
export default function HazardToggle({ value, onChange }) {
  const { lang } = useLang();

  return (
    <fieldset className="hazard-toggle" id="hazard-toggle-group">
      <legend className="sr-only">{t('dashboard.hazardLabel', lang)}</legend>
      <div className="hazard-toggle__options hazard-toggle__tabs" role="group" aria-label={t('dashboard.hazardLabel', lang)}>
        {HAZARDS.map((hazard, index) => {
          const label = (HAZARD_LABELS[hazard] ?? {})[lang] ?? hazard;
          const isActive = value === hazard;
          return (
            <label
              key={hazard}
              className={`hazard-toggle__label hazard-tab hazard-tab--${hazard}${isActive ? ' hazard-toggle__label--active hazard-tab--active' : ''}`}
              htmlFor={`hazard-${hazard}`}
              data-index={index}
            >
              <input
                type="radio"
                id={`hazard-${hazard}`}
                name="hazard"
                value={hazard}
                checked={isActive}
                onChange={() => onChange(hazard)}
                className="hazard-toggle__input hazard-tab__input"
              />
              <span className="hazard-tab__text" lang={lang === 'bn' ? 'bn' : undefined}>{label}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.hazard-toggle {
  border: none;
  padding: 0;
  margin: 0;
}
.hazard-toggle__tabs {
  display: flex;
  align-items: flex-end;
  gap: 0;
  position: relative;
  z-index: 2;
}

.hazard-toggle__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

/* Folder-tab style */
.hazard-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  min-width: 44px;
  padding: 0 var(--space-4);
  background: var(--surface-elevated);
  border: 1px solid var(--border);
  border-bottom: none;
  border-radius: 12px 12px 0 0;
  color: var(--ink-muted);
  font-family: var(--font-sans);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  user-select: none;
  white-space: nowrap;
  position: relative;
  transition: transform var(--transition), background var(--transition), color var(--transition), z-index var(--transition);
  box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.25);
}

/* Subtle decorative rotation on desktop */
.hazard-tab[data-index="0"] {
  transform: rotate(-2deg);
  transform-origin: bottom left;
  z-index: 1;
}
.hazard-tab[data-index="1"] {
  transform: rotate(-1deg);
  transform-origin: bottom center;
  margin-left: -6px;
  z-index: 2;
}
.hazard-tab[data-index="2"] {
  transform: rotate(1deg);
  transform-origin: bottom right;
  margin-left: -6px;
  z-index: 1;
}

.hazard-tab:hover {
  background: #36322F;
  color: var(--foreground);
}

/* Active tab is larger and uses Acid Lime accent */
.hazard-tab--active,
.hazard-tab[data-index="0"].hazard-tab--active {
  background: var(--accent);
  color: var(--accent-foreground);
  border-color: var(--accent);
  font-weight: 700;
  min-height: 48px;
  transform: translateY(-3px) scale(1.05) rotate(0deg);
  z-index: 10 !important;
  box-shadow: var(--shadow-glow), 0 -4px 12px rgba(0, 0, 0, 0.4);
}
.hazard-tab[data-index="1"].hazard-tab--active {
  background: var(--accent);
  color: var(--accent-foreground);
  border-color: var(--accent);
  font-weight: 700;
  min-height: 48px;
  transform: translateY(-3px) scale(1.05) rotate(0deg);
  z-index: 10 !important;
  box-shadow: var(--shadow-glow), 0 -4px 12px rgba(0, 0, 0, 0.4);
}
.hazard-tab[data-index="2"].hazard-tab--active {
  background: var(--accent);
  color: var(--accent-foreground);
  border-color: var(--accent);
  font-weight: 700;
  min-height: 48px;
  transform: translateY(-3px) scale(1.05) rotate(0deg);
  z-index: 10 !important;
  box-shadow: var(--shadow-glow), 0 -4px 12px rgba(0, 0, 0, 0.4);
}

.hazard-tab:has(.hazard-toggle__input:focus-visible) {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

/* Remove decorative rotation below 640px and respect reduced motion */
@media (max-width: 640px) {
  .hazard-toggle__tabs {
    gap: var(--space-2);
    flex-wrap: wrap;
  }
  .hazard-tab,
  .hazard-tab[data-index="0"],
  .hazard-tab[data-index="1"],
  .hazard-tab[data-index="2"] {
    transform: none !important;
    margin-left: 0;
    border-radius: var(--radius-sm);
    border-bottom: 1px solid var(--border);
    min-height: 44px;
    padding: 0 var(--space-3);
  }
  .hazard-tab--active,
  .hazard-tab[data-index="0"].hazard-tab--active,
  .hazard-tab[data-index="1"].hazard-tab--active,
  .hazard-tab[data-index="2"].hazard-tab--active {
    transform: none !important;
    min-height: 44px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hazard-tab,
  .hazard-tab[data-index="0"],
  .hazard-tab[data-index="1"],
  .hazard-tab[data-index="2"],
  .hazard-tab--active {
    transform: none !important;
    transition: none !important;
  }
}
`;
  if (!document.getElementById('hazard-toggle-styles')) {
    style.id = 'hazard-toggle-styles';
    document.head.appendChild(style);
  }
}
