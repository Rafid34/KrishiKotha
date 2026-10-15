import React from 'react';
import { useLang, t } from '../i18n/index.jsx';
import { HAZARD_LABELS } from '../utils/risk.js';

const HAZARDS = ['drought', 'flood', 'salt'];

/**
 * HazardToggle — three native radio buttons for selecting the active hazard.
 * Spec §8.4: "The hazard toggle uses native radio inputs."
 */
export default function HazardToggle({ value, onChange }) {
  const { lang } = useLang();

  return (
    <fieldset className="hazard-toggle" id="hazard-toggle-group">
      <legend className="sr-only">{t('dashboard.hazardLabel', lang)}</legend>
      <div className="hazard-toggle__options" role="group" aria-label={t('dashboard.hazardLabel', lang)}>
        {HAZARDS.map(hazard => {
          const label = (HAZARD_LABELS[hazard] ?? {})[lang] ?? hazard;
          return (
            <label
              key={hazard}
              className={`hazard-toggle__label${value === hazard ? ' hazard-toggle__label--active' : ''}`}
              htmlFor={`hazard-${hazard}`}
            >
              <input
                type="radio"
                id={`hazard-${hazard}`}
                name="hazard"
                value={hazard}
                checked={value === hazard}
                onChange={() => onChange(hazard)}
                className="hazard-toggle__input"
              />
              <span lang={lang === 'bn' ? 'bn' : undefined}>{label}</span>
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
}
.hazard-toggle__options {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}
.hazard-toggle__input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}
.hazard-toggle__label {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-full);
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--ink);
  font-size: var(--text-sm);
  font-weight: 500;
  cursor: pointer;
  transition: border-color var(--transition), background var(--transition), color var(--transition);
  user-select: none;
  white-space: nowrap;
}
.hazard-toggle__label:hover {
  border-color: var(--brand);
  color: var(--brand);
}
.hazard-toggle__label--active {
  background: var(--brand);
  border-color: var(--brand);
  color: #fff;
  font-weight: 600;
}
.hazard-toggle__input:focus-visible + span {
  /* Focus ring visible on the label text when navigating by keyboard */
}
.hazard-toggle__label:has(input:focus-visible) {
  outline: 3px solid var(--brand);
  outline-offset: 2px;
}
`;
  if (!document.getElementById('hazard-toggle-styles')) {
    style.id = 'hazard-toggle-styles';
    document.head.appendChild(style);
  }
}
