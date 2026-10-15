// i18n: language state and t() helper
// Language is stored as module-level state (not React state) so it can be
// imported by non-component utilities too. React components that need to
// re-render on lang change should use the useLang() hook.

import { createContext, useContext, useState, useCallback } from 'react';
import en from './en.json';
import bn from './bn.json';

const STRINGS = { en, bn };

export const LangContext = createContext({ lang: 'en', setLang: () => {} });

/** Provider — wrap the app root with this */
export function LangProvider({ children }) {
  const [lang, setLang] = useState('en');
  const toggle = useCallback(() => setLang(l => (l === 'en' ? 'bn' : 'en')), []);
  return (
    <LangContext.Provider value={{ lang, setLang: toggle }}>
      {children}
    </LangContext.Provider>
  );
}

/** Hook: returns { lang, toggle } */
export function useLang() {
  return useContext(LangContext);
}

/**
 * Translate a dot-notation key against the active language's string table.
 * Falls back to English, then to the raw key.
 * @param {string} key  Dot-separated key, e.g. "nav.dashboard"
 * @param {string} lang Active language code ('en' | 'bn')
 * @returns {string}
 */
export function t(key, lang = 'en') {
  const strings = STRINGS[lang] ?? STRINGS.en;
  const parts = key.split('.');
  let node = strings;
  for (const part of parts) {
    if (node == null || typeof node !== 'object') break;
    node = node[part];
  }
  if (node == null || typeof node === 'object') {
    // Fallback to English
    let fallback = STRINGS.en;
    for (const part of parts) {
      if (fallback == null || typeof fallback !== 'object') break;
      fallback = fallback[part];
    }
    return typeof fallback === 'string' ? fallback : key;
  }
  return String(node);
}
