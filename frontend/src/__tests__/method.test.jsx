import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToString } from 'react-dom/server';
import {
  formatFloodFormula,
  formatDroughtFormula,
  formatSalinityFormula,
  formatThresholds,
  formatSourceDate,
} from '../utils/method.js';
import Method from '../pages/Method.jsx';
import { LangProvider } from '../i18n/index.jsx';

describe('method formatting utils', () => {
  const sampleConstants = {
    thresholds: {
      moderate: 40.0,
      high: 70.0,
    },
    flood: {
      weight_rain3: 0.40,
      weight_rain7: 0.35,
      weight_soil: 0.25,
    },
    drought: {
      weight_soil: 0.45,
      weight_rain: 0.35,
      weight_heat: 0.20,
      deficit_scale: 125.0,
      heat_max_anomaly: 4.0,
    },
    salinity: {
      coast_max_km: 150.0,
      coast_min_km: 20.0,
      coast_span_km: 130.0,
      season_scores: {
        mar_to_may: 100.0,
        feb_and_jun: 60.0,
        other: 20.0,
      },
      weights_with_ndvi: {
        season: 0.40,
        dry: 0.30,
        veg: 0.30,
      },
      weights_without_ndvi: {
        season: 0.55,
        dry: 0.45,
      },
      ndvi_scale: 0.10,
    },
  };

  describe('formatFloodFormula', () => {
    it('builds flood formula containing weights from constants', () => {
      const text = formatFloodFormula(sampleConstants);
      expect(text).toContain('0.4 × f_rain3 + 0.35 × f_rain7 + 0.25 × f_soil');
      expect(text).toContain('f_rain3 = percentile_rank');
      expect(text).toContain('Degraded fallback');
    });

    it('adapts when custom weights are passed', () => {
      const custom = {
        flood: { weight_rain3: 0.5, weight_rain7: 0.3, weight_soil: 0.2 },
      };
      const text = formatFloodFormula(custom);
      expect(text).toContain('0.5 × f_rain3 + 0.3 × f_rain7 + 0.2 × f_soil');
    });
  });

  describe('formatDroughtFormula', () => {
    it('builds drought formula containing weights and parameters from constants', () => {
      const text = formatDroughtFormula(sampleConstants);
      expect(text).toContain('0.45 × d_soil + 0.35 × d_rain + 0.2 × d_heat');
      expect(text).toContain('clamp(rain_deficit × 125');
      expect(text).toContain('+4°C anomaly');
    });
  });

  describe('formatSalinityFormula', () => {
    it('builds salinity formula reflecting coast span, weights, and season sub-scores', () => {
      const text = formatSalinityFormula(sampleConstants);
      expect(text).toContain('150 - distance_to_coast_km) / 130');
      expect(text).toContain('0.4 × season + 0.3 × dry_index + 0.3 × veg_anomaly');
      expect(text).toContain('0.55 × season + 0.45 × dry_index');
      expect(text).toContain('March to May (peak salinity):     100');
    });
  });

  describe('formatThresholds', () => {
    it('returns low, moderate, and high threshold definitions', () => {
      const rows = formatThresholds(sampleConstants);
      expect(rows).toHaveLength(3);
      expect(rows[0]).toEqual({
        level: 'low',
        condition: '< 40',
        label: 'Low',
        labelBn: 'কম',
      });
      expect(rows[1].condition).toBe('40 – 69.99');
      expect(rows[2].condition).toBe('≥ 70');
    });
  });

  describe('formatSourceDate', () => {
    it('formats valid ISO date in English and Bangla', () => {
      const formattedEn = formatSourceDate('2022-06-16', 'en');
      expect(formattedEn).toContain('2022');
      const formattedBn = formatSourceDate('2022-06-16', 'bn');
      expect(formattedBn).toContain('২০২২');
    });

    it('returns fallback string when date is null or empty', () => {
      expect(formatSourceDate(null, 'en')).toBe('No data');
      expect(formatSourceDate(null, 'bn')).toBe('তথ্য নেই');
    });
  });
});

describe('Method Page Component', () => {
  it('renders initial loading state and disclaimer banner', () => {
    const html = renderToString(
      <LangProvider>
        <Method />
      </LangProvider>
    );

    expect(html).toContain('Method &amp; Data');
    expect(html).toContain('Based on NASA satellite data. Not an official government warning.');
    expect(html).toContain('Loading');
  });
});
