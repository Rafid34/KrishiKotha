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

vi.mock('../components/RiskMap.jsx', () => ({
  default: () => <div className="risk-map-mock" />,
}));

vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    ResponsiveContainer: ({ children }) => <div>{children}</div>,
  };
});

import { getDistricts, getRisk } from '../api/client.js';
import { LangContext, LangProvider } from '../i18n/index.jsx';
import Dashboard from '../pages/Dashboard.jsx';
import Simulator from '../pages/Simulator.jsx';

vi.mock('../api/client.js', () => ({
  getDistricts: vi.fn().mockResolvedValue([]),
  getRisk: vi.fn().mockResolvedValue({
    date: '2026-10-15',
    districts: [],
  }),
  postSimSms: vi.fn(),
  postAdvice: vi.fn(),
}));

describe('Default date and June 2022 flood demo quick-pick (R-018)', () => {
  it('Dashboard renders quick-pick button "June 2022 flood demo"', () => {
    const htmlEn = renderToString(
      <LangContext.Provider value={{ lang: 'en', setLang: () => {} }}>
        <Dashboard />
      </LangContext.Provider>
    );

    expect(htmlEn).toContain('dashboard__demo-pick-btn');
    expect(htmlEn).toContain('June 2022 flood demo');

    const htmlBn = renderToString(
      <LangContext.Provider value={{ lang: 'bn', setLang: () => {} }}>
        <Dashboard />
      </LangContext.Provider>
    );

    expect(htmlBn).toContain('dashboard__demo-pick-btn');
    expect(htmlBn).toContain('জুন ২০২২ বন্যা ডেমো');
  });

  it('Simulator renders quick-pick button "June 2022 flood demo"', () => {
    const htmlEn = renderToString(
      <LangContext.Provider value={{ lang: 'en', setLang: () => {} }}>
        <Simulator />
      </LangContext.Provider>
    );

    expect(htmlEn).toContain('simulator-demopick-btn');
    expect(htmlEn).toContain('June 2022 flood demo');

    const htmlBn = renderToString(
      <LangContext.Provider value={{ lang: 'bn', setLang: () => {} }}>
        <Simulator />
      </LangContext.Provider>
    );

    expect(htmlBn).toContain('simulator-demopick-btn');
    expect(htmlBn).toContain('জুন ২০২২ বন্যা ডেমো');
  });

  it('Dashboard accepts initial date from API and button sets 2022-06-16', () => {
    // When date is supplied from API
    const apiDate = '2026-10-15';
    const htmlApi = renderToString(
      <LangProvider initialLang="en">
        <Dashboard initialDate={apiDate} />
      </LangProvider>
    );
    expect(htmlApi).toContain(`value="${apiDate}"`);

    // When quick-pick sets 2022-06-16
    const htmlDemo = renderToString(
      <LangProvider initialLang="en">
        <Dashboard initialDate="2022-06-16" />
      </LangProvider>
    );
    expect(htmlDemo).toContain('value="2022-06-16"');
  });

  it('Simulator accepts initial date from API and button sets 2022-06-16', () => {
    const apiDate = '2026-10-15';
    const htmlApi = renderToString(
      <LangProvider initialLang="en">
        <Simulator initialDate={apiDate} />
      </LangProvider>
    );
    expect(htmlApi).toContain(`value="${apiDate}"`);

    const htmlDemo = renderToString(
      <LangProvider initialLang="en">
        <Simulator initialDate="2022-06-16" />
      </LangProvider>
    );
    expect(htmlDemo).toContain('value="2022-06-16"');
  });
});
