import React from 'react';
import { describe, it, expect, vi } from 'vitest';

// Use vi.hoisted to ensure document and window exist before hoisted ES module imports run
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

// Mock client api calls to avoid unhandled rejections during renderToString
vi.mock('../api/client.js', () => ({
  getDistricts: vi.fn().mockResolvedValue([]),
  getRisk: vi.fn().mockResolvedValue({ date: '2022-06-16', districts: [] }),
  getBacktestSylhet: vi.fn().mockResolvedValue({}),
  getScoringConstants: vi.fn().mockResolvedValue({}),
  getSources: vi.fn().mockResolvedValue([]),
  sendSimSms: vi.fn().mockResolvedValue({}),
}));

// Mock RiskMap to avoid Leaflet accessing DOM in node test environment
vi.mock('../components/RiskMap.jsx', () => ({
  default: () => <div className="risk-map-mock" />,
}));

// Mock recharts responsive container for SSR
vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
  };
});

import { LangProvider } from '../i18n/index.jsx';
import Dashboard from '../pages/Dashboard.jsx';
import EventReplay from '../pages/EventReplay.jsx';
import Simulator from '../pages/Simulator.jsx';
import Method from '../pages/Method.jsx';

const DISCLAIMER_EN = 'Based on NASA satellite data. Not an official government warning.';

describe('Mandatory Disclaimer (R-004) on all pages', () => {
  it('renders disclaimer on Dashboard at all times', () => {
    const html = renderToString(
      <LangProvider>
        <Dashboard />
      </LangProvider>
    );
    expect(html).toContain(DISCLAIMER_EN);
  });

  it('renders disclaimer on EventReplay page', () => {
    const html = renderToString(
      <LangProvider>
        <EventReplay />
      </LangProvider>
    );
    expect(html).toContain(DISCLAIMER_EN);
  });

  it('renders disclaimer on Simulator page', () => {
    const html = renderToString(
      <LangProvider>
        <Simulator />
      </LangProvider>
    );
    expect(html).toContain(DISCLAIMER_EN);
  });

  it('renders disclaimer on Method page', () => {
    const html = renderToString(
      <LangProvider>
        <Method />
      </LangProvider>
    );
    expect(html).toContain(DISCLAIMER_EN);
  });
});
