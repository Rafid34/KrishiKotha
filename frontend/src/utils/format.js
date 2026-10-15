// Number, date and Bangla digit formatting utilities

const BN_DIGITS = '০১২৩৪৫৬৭৮৯';

/** Convert a Latin numeral string to Bangla digit string */
export function toBanglaDigits(str) {
  return String(str).replace(/[0-9]/g, d => BN_DIGITS[parseInt(d, 10)]);
}

/**
 * Format a number with a fixed number of decimal places.
 * @param {number|null|undefined} value
 * @param {number} decimals
 * @param {string} [lang] - 'bn' converts digits to Bangla
 */
export function formatNumber(value, decimals = 1, lang = 'en') {
  if (value == null || isNaN(value)) return lang === 'bn' ? '—' : '—';
  const str = value.toFixed(decimals);
  return lang === 'bn' ? toBanglaDigits(str) : str;
}

/**
 * Format a YYYY-MM-DD date string to a user-friendly format.
 * @param {string|null} dateStr
 * @param {string} [lang]
 */
export function formatDate(dateStr, lang = 'en') {
  if (!dateStr) return '—';
  const [year, month, day] = dateStr.split('-').map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const locale = lang === 'bn' ? 'bn-BD' : 'en-GB';
  try {
    const str = date.toLocaleDateString(locale, {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
    return lang === 'bn' ? toBanglaDigits(str) : str;
  } catch {
    return dateStr;
  }
}

/**
 * Clamp a number between min and max.
 */
export function clamp(val, min, max) {
  return Math.min(max, Math.max(min, val));
}
