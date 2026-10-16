import React from 'react';
import { Circle, Triangle, Square } from 'lucide-react';
import { LEVEL_META, levelLabel } from '../utils/risk.js';
import { useLang } from '../i18n/index.jsx';

/**
 * LevelIcon — monochrome Lucide-style line icon for risk levels.
 * Circle = low, Triangle = moderate, Square = high.
 * Always accompanies the colour so colourblind users are not excluded.
 */
export function LevelIcon({ level, size = 14, color: colorProp, ...props }) {
  const meta = LEVEL_META[level] ?? LEVEL_META.low;
  const color = colorProp ?? meta.color;
  const icon = meta.icon;

  if (icon === 'triangle') {
    return (
      <Triangle
        size={size}
        color={color}
        fill={color}
        fillOpacity={0.25}
        strokeWidth={2}
        aria-hidden="true"
        focusable="false"
        {...props}
      />
    );
  }
  if (icon === 'square') {
    return (
      <Square
        size={size}
        color={color}
        fill={color}
        fillOpacity={0.25}
        strokeWidth={2}
        aria-hidden="true"
        focusable="false"
        {...props}
      />
    );
  }
  // Circle (low)
  return (
    <Circle
      size={size}
      color={color}
      fill={color}
      fillOpacity={0.25}
      strokeWidth={2}
      aria-hidden="true"
      focusable="false"
      {...props}
    />
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

  return (
    <span
      className={`risk-badge risk-badge--${level}`}
      style={{
        '--badge-color': meta.color,
        '--badge-text-color': meta.textColor ?? meta.color,
      }}
      title={`${label}${score != null ? ` (${Math.round(score)})` : ''}`}
    >
      <LevelIcon level={level} size={12} color={meta.textColor ?? meta.color} />
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
  gap: 5px;
  padding: 3px 8px 3px 6px;
  border-radius: var(--radius-full);
  background: color-mix(in srgb, var(--badge-color) 14%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--badge-color) 40%, transparent);
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--badge-text-color, var(--badge-color));
  white-space: nowrap;
  line-height: 1.3;
}

.risk-badge--moderate {
  background: color-mix(in srgb, var(--risk-moderate) 16%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--risk-moderate) 50%, transparent);
  color: var(--risk-moderate);
}

.risk-badge--high {
  background: color-mix(in srgb, var(--risk-high) 16%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--risk-high) 50%, transparent);
  color: var(--risk-high);
}

.risk-badge--low {
  background: color-mix(in srgb, var(--risk-low) 14%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--risk-low) 45%, transparent);
  color: var(--risk-low);
}
`;
  if (!document.getElementById('risk-badge-styles')) {
    style.id = 'risk-badge-styles';
    document.head.appendChild(style);
  }
}
