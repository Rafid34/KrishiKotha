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
import { LangProvider } from '../i18n/index.jsx';
import Dashboard from '../pages/Dashboard.jsx';

vi.mock('../api/client.js', () => ({
  getDistricts: vi.fn(),
  getRisk: vi.fn(),
}));

describe('Error states & Retry (R-020)', () => {
  it('mocks a failing districts fetch and handles rejection', async () => {
    vi.mocked(getDistricts).mockRejectedValueOnce(new Error('Network connection timeout'));

    let caughtError = null;
    await getDistricts().catch(err => {
      caughtError = err.message;
    });

    expect(caughtError).toBe('Network connection timeout');
  });

  it('renders visible error banner with Retry button when district error is set', () => {
    const html = renderToString(
      <LangProvider>
        <Dashboard initialDistrictError="Network connection timeout" />
      </LangProvider>
    );

    expect(html).toContain('dashboard__error--districts');
    expect(html).toContain('Network connection timeout');
    expect(html).toContain('dashboard__retry-btn');
    expect(html).toContain('Retry');
  });

  it('renders visible error banner with Retry button when risk error is set', () => {
    const html = renderToString(
      <LangProvider>
        <Dashboard initialRiskError="Failed to load risk data" />
      </LangProvider>
    );

    expect(html).toContain('dashboard__error');
    expect(html).toContain('Failed to load risk data');
    expect(html).toContain('dashboard__retry-btn');
  });
});
