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
 * Implements Section 8.2 & Task 8.2 using Recharts.
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
              tick={{ fontSize: 10, fill: '#E65100' }}
              tickLine={false}
              axisLine={false}
              unit="%"
            />
            <Tooltip content={<CustomTooltip lang={lang} />} />
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: 11, paddingBottom: 4 }}
            />

            {/* Baseline 90th percentile reference line */}
            {p90Value != null && (
              <ReferenceLine
                yAxisId="left"
                y={p90Value}
                stroke="#D32F2F"
                strokeDasharray="3 3"
                strokeWidth={1.5}
                label={{
                  value: lang === 'bn' ? '৯০তম পারসেন্টাইল' : '90th pctl',
                  fill: '#D32F2F',
                  fontSize: 10,
                  position: 'insideTopLeft',
                }}
              />
            )}

            {/* Rainfall Bars */}
            <Bar
              yAxisId="left"
              dataKey="rain_mm"
              name={t('districtPanel.rainfall', lang)}
              fill="var(--nasa-blue, #0B3D91)"
              radius={[3, 3, 0, 0]}
              maxBarSize={16}
            />

            {/* Soil Wetness Line */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="soil_pct"
              name={t('districtPanel.soilWetness', lang)}
              stroke="#E65100"
              strokeWidth={2}
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Accessible summary text below chart per Section 8.4 & R-019 */}
      <p id="trend-chart-summary" className="trend-chart__summary" lang={lang === 'bn' ? 'bn' : undefined}>
        {summaryText}
      </p>
    </div>
  );
}

function CustomTooltip({ active, payload, label, lang }) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload;
  return (
    <div className="trend-tooltip">
      <div className="trend-tooltip__date">
        {data.date ? formatDate(data.date, lang) : label}
      </div>
      <div className="trend-tooltip__item" style={{ color: 'var(--nasa-blue)' }}>
        <span>{t('districtPanel.rainfall', lang)}:</span>
        <strong>{formatNumber(data.rain_mm, 1, lang)} mm</strong>
      </div>
      {data.soil_pct != null && (
        <div className="trend-tooltip__item" style={{ color: '#E65100' }}>
          <span>{t('districtPanel.soilWetness', lang)}:</span>
          <strong>{formatNumber(data.soil_pct, 0, lang)}%</strong>
        </div>
      )}
      {data.p90 != null && (
        <div className="trend-tooltip__item" style={{ color: '#D32F2F' }}>
          <span>{t('districtPanel.pctl90', lang)}:</span>
          <strong>{formatNumber(data.p90, 1, lang)} mm</strong>
        </div>
      )}
    </div>
  );
}

/* ─── Styles ───────────────────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `
.trend-chart {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  background: var(--bg);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  border: 1px solid var(--border);
}
.trend-chart--empty {
  min-height: 120px;
  align-items: center;
  justify-content: center;
}
.trend-chart__empty-text {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}
.trend-chart__title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}
.trend-chart__summary {
  font-size: 11px;
  color: var(--ink-muted);
  margin: 0;
  line-height: 1.4;
  border-top: 1px dashed var(--border);
  padding-top: var(--space-2);
}

.trend-tooltip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  box-shadow: var(--shadow-sm);
  font-size: 11px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.trend-tooltip__date {
  font-weight: 700;
  color: var(--ink);
  border-bottom: 1px solid var(--border);
  padding-bottom: 2px;
  margin-bottom: 2px;
}
.trend-tooltip__item {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}
`;
if (!document.getElementById('trend-chart-styles')) {
  style.id = 'trend-chart-styles';
  document.head.appendChild(style);
}
