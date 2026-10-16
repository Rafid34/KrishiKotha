import React from 'react';
import { describe, it, expect, vi } from 'vitest';

// Polyfill DOM before ES modules load
vi.hoisted(() => {
  if (typeof globalThis.document === 'undefined') {
    globalThis.document = {
      createElement: () => ({ setAttribute: () => {}, appendChild: () => {}, style: {} }),
      head: { appendChild: () => {} },
      getElementById: () => null,
    };
  }
  if (typeof globalThis.window === 'undefined') {
    globalThis.window = {
      addEventListener: () => {},
      removeEventListener: () => {},
    };
  }
});

import { renderToString } from 'react-dom/server';

vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
  };
});

import { LangContext } from '../i18n/index.jsx';
import EventReplay from '../pages/EventReplay.jsx';

const mockCensoredData = {
  district_id: 'sylhet',
  series: [
    { date: '2022-05-15', flood_score: 75.0, flood_level: 'high', rain_mm: 50.0 },
    { date: '2022-05-16', flood_score: 80.0, flood_level: 'high', rain_mm: 60.0 },
    { date: '2022-06-16', flood_score: 95.0, flood_level: 'high', rain_mm: 120.0 },
  ],
  first_moderate: '2022-05-15',
  first_high: '2022-05-15', // equals first date of series
  reference_onset: '2022-06-16',
  lead_time_days: 32,
  steps: [
    { step: 1, label: 'Rain begins', label_bn: 'বৃষ্টি শুরু', date: '2022-05-15' },
    { step: 5, label: 'Flood', label_bn: 'বন্যা', date: '2022-06-16' },
  ],
};

const mockUncensoredData = {
  district_id: 'sylhet',
  series: [
    { date: '2022-05-15', flood_score: 25.0, flood_level: 'low', rain_mm: 10.0 },
    { date: '2022-06-02', flood_score: 72.0, flood_level: 'high', rain_mm: 80.0 },
    { date: '2022-06-16', flood_score: 95.0, flood_level: 'high', rain_mm: 120.0 },
  ],
  first_moderate: '2022-05-25',
  first_high: '2022-06-02', // after first date of series (2022-05-15)
  reference_onset: '2022-06-16',
  lead_time_days: 14,
  steps: [
    { step: 1, label: 'Rain begins', label_bn: 'বৃষ্টি শুরু', date: '2022-05-15' },
    { step: 4, label: 'First high', label_bn: 'প্রথম উচ্চ ঝুঁকি', date: '2022-06-02' },
    { step: 5, label: 'Flood', label_bn: 'বন্যা', date: '2022-06-16' },
  ],
};

describe('Censored lead time guard in EventReplay (F7)', () => {
  describe('Censored case: first_high equals first date of series (2022-05-15)', () => {
    it('English: does not show "Warning came N days before the flood" and shows censored notice', () => {
      const html = renderToString(
        <LangContext.Provider value={{ lang: 'en', setLang: () => {} }}>
          <EventReplay initialData={mockCensoredData} />
        </LangContext.Provider>
      );

      // Must not show standard warning came banner
      expect(html).not.toContain('Warning came 32 days before the flood');
      expect(html).not.toContain('Warning came');

      // Must show that flood risk was already High on the first day of the window (2022-05-15)
      // and lead time is therefore at least 32 days, measured from the window start
      expect(html).toContain('Flood risk was already High on the first day of the window (2022-05-15)');
      expect(html).toContain('lead time is therefore at least 32 days, measured from the window start');
      expect(html).toContain('Lead time is at least 32 days (from window start)');
    });

    it('Bangla: does not show uncensored banner and shows Bangla censored notice', () => {
      const html = renderToString(
        <LangContext.Provider value={{ lang: 'bn', setLang: () => {} }}>
          <EventReplay initialData={mockCensoredData} />
        </LangContext.Provider>
      );

      // Must not show standard banner in Bangla
      expect(html).not.toContain('বন্যার ৩২ দিন আগেই সতর্কতা পাওয়া যায়');

      // Must show Bangla censored notice
      expect(html).toContain('উইন্ডোর প্রথম দিনেই (2022-05-15) বন্যার ঝুঁকি ইতিমধ্যেই উচ্চ ছিল');
      expect(html).toContain('সতর্কতার সময়কাল অন্তত ৩২ দিন, যা উইন্ডো শুরুর তারিখ থেকে পরিমাপকৃত');
      expect(html).toContain('সতর্কতার সময়কাল অন্তত ৩২ দিন (উইন্ডো শুরুর তারিখ থেকে পরিমাপকৃত)');
    });
  });

  describe('Uncensored case: first_high is after first date of series', () => {
    it('English: shows standard "Warning came 14 days before the flood"', () => {
      const html = renderToString(
        <LangContext.Provider value={{ lang: 'en', setLang: () => {} }}>
          <EventReplay initialData={mockUncensoredData} />
        </LangContext.Provider>
      );

      expect(html).toContain('Warning came 14 days before the flood');
      expect(html).not.toContain('already High on the first day of the window');
      expect(html).not.toContain('from window start');
    });

    it('Bangla: shows standard "বন্যার ১৪ দিন আগেই সতর্কতা পাওয়া যায়"', () => {
      const html = renderToString(
        <LangContext.Provider value={{ lang: 'bn', setLang: () => {} }}>
          <EventReplay initialData={mockUncensoredData} />
        </LangContext.Provider>
      );

      expect(html).toContain('বন্যার ১৪ দিন আগেই সতর্কতা পাওয়া যায়');
      expect(html).not.toContain('উইন্ডোর প্রথম দিনেই');
    });
  });
});
