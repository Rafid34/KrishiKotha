import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';
import { useLang, t } from '../i18n/index.jsx';
import { formatNumber, formatDate } from '../utils/format.js';

/**
 * TrendChart — 60-day rainfall bars with baseline 90th percentile and soil wetness line.
 * Styled for dark UI with Catalog label, WCAG AA contrast lines, and screen reader summary.
 *
 * @param {{
 *   series: Array,
 *   districtId?: string,
 * }} props
 */
export default function TrendChart({ series = [], districtId }) {
  const { lang } = useLang();

  // Compute 90th percentile of rainfall across the window if not in data point
  const { chartData, p90Value, maxRain, peakDay, totalRain, minSoil, maxSoil } = useMemo(() => {
    if (!series || series.length === 0) {
      return { chartData: [], p90Value: null, maxRain: 0, peakDay: null, totalRain: 0, minSoil: null, maxSoil: null };
    }

    const rainValues = series
      .map(p => p.rain_mm)
      .filter(v => v != null && !isNaN(v))
      .sort((a, b) => a - b);

    let fallbackP90 = null;
    if (rainValues.length > 0) {
      const idx = Math.floor(rainValues.length * 0.90);
      fallbackP90 = rainValues[Math.min(idx, rainValues.length - 1)];
    }

    let maxR = 0;
    let peak = null;

    const formatted = series.map(p => {
      const r = p.rain_mm != null ? Math.round(p.rain_mm * 10) / 10 : 0;
      const s = p.soil_pct != null
        ? Math.round(p.soil_pct)
        : (p.soil_wetness != null ? Math.round(p.soil_wetness * 100) : null);
      const p90 = p.rain_pctl_90 ?? fallbackP90;

      if (r > maxR) {
        maxR = r;
        peak = p.date;
      }

      return {
        date: p.date,
        shortDate: p.date ? p.date.slice(5) : '', // MM-DD
        rain_mm: r,
        soil_pct: s,
        p90: p90 != null ? Math.round(p90 * 10) / 10 : null,
      };
    });

    const soilVals = formatted.map(p => p.soil_pct).filter(v => v != null);
    return {
      chartData: formatted,
      p90Value: fallbackP90 != null ? Math.round(fallbackP90 * 10) / 10 : null,
      maxRain: maxR,
      peakDay: peak,
      totalRain: formatted.reduce((acc, p) => acc + (p.rain_mm || 0), 0),
      minSoil: soilVals.length > 0 ? Math.min(...soilVals) : null,
      maxSoil: soilVals.length > 0 ? Math.max(...soilVals) : null,
    };
  }, [series]);

  if (!series || series.length === 0) {
    return (
      <div className="trend-chart trend-chart--empty" role="img" aria-label="Rainfall trend">
        <p className="trend-chart__empty-text">{t('noData', lang)}</p>
      </div>
    );
  }

  // Current conditions summary for accessibility (R-019)
  const summaryText = t('districtPanel.trendSummary', lang)
    .replace('{totalRain}', formatNumber(totalRain, 1, lang))
    .replace('{peakRain}', formatNumber(maxRain, 1, lang))
    .replace('{peakDay}', peakDay ? formatDate(peakDay, lang) : '—')
    .replace('{soilMin}', minSoil != null ? formatNumber(minSoil, 0, lang) : '—')
    .replace('{soilMax}', maxSoil != null ? formatNumber(maxSoil, 0, lang) : '—');

  return (
    <div className="trend-chart" role="region" aria-label={t('districtPanel.rainfallTrend', lang)}>
      <div className="trend-chart__header">
        {/* Catalog label */}
        <div className="catalog-label trend-chart__catalog-label" aria-hidden="true">
          <span className="catalog-label__dot" />
          <span className="catalog-label__mono">Fig. 2 60-day rainfall trend & soil moisture</span>
        </div>
        <h3 className="trend-chart__title" lang={lang === 'bn' ? 'bn' : undefined}>
          {t('districtPanel.rainfallTrend', lang)}
        </h3>
      </div>

      <div
        className="trend-chart__plot"
        role="img"
        aria-label={t('districtPanel.rainfallTrend', lang)}
        aria-describedby="trend-chart-summary"
        style={{ width: '100%', height: 210 }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -15, bottom: 0 }}
          >
            <XAxis
              dataKey="shortDate"
              tick={{ fontSize: 10, fill: 'var(--ink-muted)' }}
              tickLine={false}
              interval="preserveStartEnd"
              minTickGap={25}
            />
            {/* Left Y: Rainfall in mm */}
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 10, fill: 'var(--ink-muted)' }}
              tickLine={false}
              axisLine={false}
              unit=" mm"
            />
            {/* Right Y: Soil Wetness in % */}
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              tick={{ fontSize: 10, fill: '#4ADE80' }}
              tickLine={false}
              axisLine={false}
              unit="%"
            />
            <Tooltip content={<CustomTooltip lang={lang} />} />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: 11, paddingBottom: 4, color: 'var(--ink-muted)' }}
            />

            {/* Baseline 90th percentile reference line */}
            {p90Value != null && (
              <ReferenceLine
                yAxisId="left"
                y={p90Value}
                stroke="#F87171"
                strokeDasharray="3 3"
                strokeWidth={1.5}
                label={{
                  value: lang === 'bn' ? '৯০তম পারসেন্টাইল' : '90th pctl',
                  fill: '#F87171',
                  fontSize: 10,
                  position: 'insideTopRight',
                }}
              />
            )}

            {/* Rainfall bars */}
            <Bar
              yAxisId="left"
              dataKey="rain_mm"
              name={t('districtPanel.rainfall', lang)}
              fill="#60A5FA"
              opacity={0.85}
              radius={[2, 2, 0, 0]}
              maxBarSize={8}
            />

            {/* Soil wetness line */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="soil_pct"
              name={t('districtPanel.soilWetness', lang)}
              stroke="#4ADE80"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Screen reader summary under chart */}
      <p id="trend-chart-summary" className="trend-chart__summary" lang={lang === 'bn' ? 'bn' : undefined}>
        {summaryText}
      </p>
    </div>
  );
}

function CustomTooltip({ active, payload, label, lang }) {
  if (!active || !payload || payload.length === 0) return null;

  return (
    <div className="trend-tooltip">
      <p className="trend-tooltip__date">{label}</p>
      {payload.map((item, index) => (
        <p key={index} className="trend-tooltip__item" style={{ color: item.color }}>
          <span>{item.name}: </span>
          <strong>{formatNumber(item.value, 1, lang)} {item.unit || ''}</strong>
        </p>
      ))}
    </div>
  );
}

/* ─── Styles ────────────────────────────────────────────────────────── */
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style) {
  style.textContent = `
.trend-chart {
  background: var(--surface-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  position: relative;
}

.trend-chart__header {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  margin-bottom: var(--space-2);
}

.trend-chart__catalog-label {
  align-self: flex-start;
  margin-bottom: 2px;
}

.trend-chart__title {
  font-family: var(--font-serif);
  font-size: var(--text-base);
  font-weight: 400;
  color: var(--foreground);
}

.trend-chart__summary {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  line-height: 1.4;
  margin-top: var(--space-2);
  border-top: 1px solid var(--border);
  padding-top: var(--space-2);
}

.trend-tooltip {
  background: #1C1917;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  box-shadow: var(--shadow-md);
  font-size: 11px;
}
.trend-tooltip__date {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--foreground);
  margin-bottom: 4px;
}
.trend-tooltip__item {
  margin: 2px 0;
}
`;
  if (!document.getElementById('trend-chart-styles')) {
    style.id = 'trend-chart-styles';
    document.head.appendChild(style);
  }
}
