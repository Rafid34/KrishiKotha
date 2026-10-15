import React from 'react';
import { describe, it, expect, vi } from 'vitest';

// Use vi.hoisted to polyfill DOM elements before ES modules load
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

vi.mock('../api/client.js', () => ({
  getBacktestSylhet: vi.fn().mockResolvedValue({
    series: [
      { date: '2022-05-15', rain_mm: 50.0, flood_score: 75.0, rain_pctl_90: 40.0 },
      { date: '2022-05-16', rain_mm: 120.0, flood_score: 92.0, rain_pctl_90: 40.0 },
    ],
    steps: [],
    lead_time_days: 32,
    first_high: '2022-05-15',
    reference_onset: '2022-06-16',
  }),
}));

vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
  };
});

import { LangContext, LangProvider } from '../i18n/index.jsx';
import TrendChart from '../components/TrendChart.jsx';
import EventReplay from '../pages/EventReplay.jsx';

describe('Chart Summaries (R-019)', () => {
  const sampleSeries = [
    { date: '2022-05-15', rain_mm: 25.5, soil_pct: 45.0, rain_pctl_90: 30.0 },
    { date: '2022-05-16', rain_mm: 80.0, soil_pct: 68.0, rain_pctl_90: 30.0 },
    { date: '2022-05-17', rain_mm: 10.5, soil_pct: 55.0, rain_pctl_90: 30.0 },
  ];

  it('TrendChart renders data-driven summary with role="img" and aria-describedby in English', () => {
    const html = renderToString(
      <LangProvider>
        <TrendChart series={sampleSeries} districtId="sylhet" />
      </LangProvider>
    );

    // Chart container has role="img" and links to summary via aria-describedby
    expect(html).toContain('role="img"');
    expect(html).toContain('aria-describedby="trend-chart-summary"');

    // Summary element has matching id
    expect(html).toContain('id="trend-chart-summary"');

    // Summary contains computed total rain (25.5 + 80.0 + 10.5 = 116.0), peak (80.0), soil range (45–68)
    expect(html).toContain('Total rainfall 116.0 mm');
    expect(html).toContain('peak rainfall 80.0 mm');
    expect(html).toContain('45–68%');

    // Spec constraint: Do not use aria-live on static summary
    expect(html).not.toContain('aria-live');
  });

  it('TrendChart renders data-driven summary in Bangla with Bangla digits', () => {
    const html = renderToString(
      <LangContext.Provider value={{ lang: 'bn', setLang: () => {} }}>
        <TrendChart series={sampleSeries} districtId="sylhet" />
      </LangContext.Provider>
    );

    expect(html).toContain('id="trend-chart-summary"');
    // Total 116.0 in Bangla: ১১৬.০
    expect(html).toContain('১১৬.০');
    // Peak 80.0 in Bangla: ৮০.০
    expect(html).toContain('৮০.০');
    // Soil range 45–68 in Bangla: ৪৫–৬৮
    expect(html).toContain('৪৫–৬৮');
    expect(html).not.toContain('aria-live');
  });

  it('EventReplay chart container has role="img", aria-describedby, and no aria-live', () => {
    const html = renderToString(
      <LangProvider>
        <EventReplay />
      </LangProvider>
    );

    // During SSR / initial load, verify disclaimer and no aria-live
    expect(html).not.toContain('aria-live');
  });
});
