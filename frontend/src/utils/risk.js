// Level to colour and label helpers
// Level thresholds mirror backend/app/services/risk/scoring.py:
//   score < 40  → low
//   40 ≤ score < 70 → moderate
//   score ≥ 70  → high

/** @type {Record<string, {color: string, label: string, labelBn: string, icon: 'circle'|'triangle'|'square'}>} */
export const LEVEL_META = {
  low: {
    color: 'var(--risk-low)',
    label: 'Low',
    labelBn: 'কম',
    icon: 'circle',
  },
  moderate: {
    color: 'var(--risk-moderate)',
    label: 'Moderate',
    labelBn: 'মাঝারি',
    icon: 'triangle',
  },
  high: {
    color: 'var(--risk-high)',
    label: 'High',
    labelBn: 'বেশি',
    icon: 'square',
  },
};

/** Map a level string to its CSS colour token value */
export function levelColor(level) {
  return (LEVEL_META[level] ?? LEVEL_META.low).color;
}

/** Map a level string to its English display label */
export function levelLabel(level, lang = 'en') {
  const meta = LEVEL_META[level] ?? LEVEL_META.low;
  return lang === 'bn' ? meta.labelBn : meta.label;
}

/** Map a level string to its icon shape key */
export function levelIcon(level) {
  return (LEVEL_META[level] ?? LEVEL_META.low).icon;
}

/** Map a score number to a level string */
export function scoreToLevel(score) {
  if (score >= 70) return 'high';
  if (score >= 40) return 'moderate';
  return 'low';
}

/** Friendly label for a hazard id */
export const HAZARD_LABELS = {
  drought: { en: 'Drought', bn: 'খরা' },
  flood:   { en: 'Flood',   bn: 'বন্যা' },
  salt:    { en: 'Salinity', bn: 'লবণাক্ততা' },
};

export function hazardLabel(hazard, lang = 'en') {
  return (HAZARD_LABELS[hazard] ?? { en: hazard, bn: hazard })[lang];
}
