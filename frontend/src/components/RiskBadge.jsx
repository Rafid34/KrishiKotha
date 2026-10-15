import React from 'react';
import { LEVEL_META, levelLabel } from '../utils/risk.js';
import { useLang, t } from '../i18n/index.jsx';

/**
 * LevelIcon — SVG icon shape for a risk level.
 * Circle = low, Triangle = moderate, Square = high.
 * Always accompanies the colour so colourblind users are not excluded.
 */
export function LevelIcon({ level, size = 16, color: colorProp, ...props }) {
  const color = colorProp ?? LEVEL_META[level]?.color ?? 'var(--risk-low)';
  const icon = LEVEL_META[level]?.icon ?? 'circle';

  if (icon === 'triangle') {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 16 16"
        aria-hidden="true"
        focusable="false"
        {...props}
      >
        <polygon points="8,2 15,14 1,14" fill={color} stroke="var(--ink)" strokeWidth={1} />
      </svg>
    );
  }
  if (icon === 'square') {
    return (
      <svg
        width={size}
        height={size}
        viewBox="0 0 16 16"
        aria-hidden="true"
        focusable="false"
        {...props}
      >
        <rect x="2" y="2" width="12" height="12" rx="2" fill={color} />
      </svg>
    );
  }
  // default: circle (low)
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      <circle cx="8" cy="8" r="6" fill={color} />
    </svg>
  );
}

/**
 * RiskBadge — coloured chip showing the risk level with icon + text.
 * Spec §8.4: "Risk levels are always shown with text and an icon shape
 * (circle, triangle, square), never colour alone."
 */
export default function RiskBadge({ level, score, lang: langProp }) {
  const { lang: ctxLang } = useLang();
  const lang = langProp ?? ctxLang;
  const meta = LEVEL_META[level] ?? LEVEL_META.low;
  const label = levelLabel(level, lang);
  const isModerate = level === 'moderate';

  return (
    <span
      className={`risk-badge risk-badge--${level}`}
      style={{
        '--badge-color': meta.color,
        '--badge-text-color': meta.textColor ?? meta.color,
      }}
      title={`${label}${score != null ? ` (${Math.round(score)})` : ''}`}
    >
      <LevelIcon level={level} size={14} color={isModerate ? 'var(--ink)' : meta.color} />
      <span className="risk-badge__text">{label}</span>
    </span>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px 2px 6px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--badge-color) 12%, transparent);
  border: 1.5px solid color-mix(in srgb, var(--badge-color) 40%, transparent);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--badge-text-color, var(--badge-color));
  white-space: nowrap;
  line-height: 1.4;
}

.risk-badge--moderate {
  background: var(--risk-moderate);
  border: 1.5px solid var(--risk-moderate);
  color: var(--ink);
}
`;
  if (!document.getElementById('risk-badge-styles')) {
    style.id = 'risk-badge-styles';
    document.head.appendChild(style);
  }
}

