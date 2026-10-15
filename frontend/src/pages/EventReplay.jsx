import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
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
import RiskBadge from '../components/RiskBadge.jsx';
import { useLang, t } from '../i18n/index.jsx';
import { formatNumber, formatDate } from '../utils/format.js';
import { getBacktestSylhet } from '../api/client.js';

export default function EventReplay() {
  const { lang } = useLang();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentDateIndex, setCurrentDateIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const playTimerRef = useRef(null);

  // Load backtest replay data from /api/backtest/sylhet-2022
  const loadData = useCallback(() => {
    setLoading(true);
    setError(null);
    getBacktestSylhet()
      .then(res => {
        setData(res);
        // Default to reference onset date or the last date in series
        const series = res.series || [];
        const onsetIdx = series.findIndex(p => p.date === res.reference_onset);
        if (onsetIdx !== -1) {
          setCurrentDateIndex(onsetIdx);
        } else if (series.length > 0) {
          setCurrentDateIndex(series.length - 1);
        }
        setLoading(false);
      })
      .catch(err => {
        setError(err.message || 'Failed to load replay data');
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Play/Pause interval timer
  useEffect(() => {
    if (!isPlaying) {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
      return;
    }

    const series = data?.series || [];
    if (series.length === 0) return;

    playTimerRef.current = setInterval(() => {
      setCurrentDateIndex(prev => {
        if (prev >= series.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 600); // 600ms per day

    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, data?.series]);

  const series = data?.series || [];
  const steps = data?.steps || [];
  const leadTimeDays = data?.lead_time_days ?? 32;
  const currentPoint = series[currentDateIndex] || null;
  const currentDate = currentPoint?.date || '';

  // Formatted chart points and data statistics (R-019)
  const { chartData, totalRain, peakRain, peakRainDate, peakScore, peakScoreDate } = useMemo(() => {
    let totRain = 0;
    let maxR = 0;
    let maxRDate = '';
    let maxS = 0;
    let maxSDate = '';
    const formatted = series.map(p => {
      const r = p.rain_mm != null ? p.rain_mm : 0;
      const s = p.flood_score != null ? p.flood_score : 0;
      totRain += r;
      if (r > maxR) {
        maxR = r;
        maxRDate = p.date;
      }
      if (s > maxS) {
        maxS = s;
        maxSDate = p.date;
      }
      return {
        date: p.date,
        shortDate: p.date ? p.date.slice(5) : '',
        rain_mm: r,
        flood_score: p.flood_score,
        p90: p.rain_pctl_90,
      };
    });
    return {
      chartData: formatted,
      totalRain: totRain,
      peakRain: maxR,
      peakRainDate: maxRDate,
      peakScore: maxS,
      peakScoreDate: maxSDate,
    };
  }, [series]);

  const handleStepClick = dateStr => {
    if (!dateStr) return;
    const idx = series.findIndex(p => p.date === dateStr);
    if (idx !== -1) {
      setCurrentDateIndex(idx);
      setIsPlaying(false);
    }
  };

  const handleSliderChange = e => {
    setCurrentDateIndex(Number(e.target.value));
    setIsPlaying(false);
  };

  const togglePlay = () => {
    if (currentDateIndex >= series.length - 1) {
      setCurrentDateIndex(0);
    }
    setIsPlaying(prev => !prev);
  };

  if (loading) {
    return (
      <div className="replay-page replay-page--loading" role="status">
        <p>{t('loading', lang)}</p>
        <p className="replay-disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
          {t('disclaimer', lang)}
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="replay-page replay-page--error" role="alert">
        <h2>{t('error', lang)}</h2>
        <p>{error}</p>
        <button type="button" className="replay-retry-btn" onClick={loadData}>
          {lang === 'bn' ? 'পুনরায় চেষ্টা করুন' : 'Retry'}
        </button>
        <p className="replay-disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
          {t('disclaimer', lang)}
        </p>
      </div>
    );
  }

  const chartSummaryText = t('replay.chartSummary', lang)
    .replace('{totalRain}', formatNumber(totalRain, 1, lang))
    .replace('{peakRain}', formatNumber(peakRain, 1, lang))
    .replace('{peakDate}', peakRainDate ? formatDate(peakRainDate, lang) : '—')
    .replace('{peakScore}', formatNumber(peakScore, 1, lang))
    .replace('{peakScoreDate}', peakScoreDate ? formatDate(peakScoreDate, lang) : '—');

  return (
    <div className="replay-page" role="main" aria-label={t('replay.title', lang)}>
      {/* Title Header */}
      <header className="replay-header">
        <div>
          <h1 className="replay-title" lang={lang === 'bn' ? 'bn' : undefined}>
            {t('replay.title', lang)}
          </h1>
          <p className="replay-subtitle" lang={lang === 'bn' ? 'bn' : undefined}>
            {t('replay.subtitle', lang)}
          </p>
        </div>
      </header>

      {/* Top: 5 Step Chips in Order */}
      <nav className="replay-steps" aria-label={t('replay.stepsTitle', lang)}>
        {steps.map(s => {
          const isPassedOrCurrent = s.date && currentDate && currentDate >= s.date;
          const isCurrentExact = s.date === currentDate;
          const labelText = lang === 'bn' && s.label_bn ? s.label_bn : s.label;

          return (
            <button
              type="button"
              key={s.step}
              className={`step-chip ${isPassedOrCurrent ? 'step-chip--active' : ''} ${isCurrentExact ? 'step-chip--selected' : ''}`}
              onClick={() => handleStepClick(s.date)}
              disabled={!s.date}
              aria-label={`Step ${s.step}: ${labelText}, ${s.date || 'unknown'}`}
            >
              <div className="step-chip__number">{s.step}</div>
              <div className="step-chip__content">
                <span className="step-chip__label" lang={lang === 'bn' ? 'bn' : undefined}>
                  {labelText}
                </span>
                <span className="step-chip__date">
                  {s.date ? formatDate(s.date, lang) : '—'}
                </span>
              </div>
            </button>
          );
        })}
      </nav>

      {/* Date Slider & Play Controls */}
      <section className="replay-controls" aria-label="Timeline controls">
        <div className="replay-controls__row">
          <button
            type="button"
            className="replay-play-btn"
            onClick={togglePlay}
            aria-label={isPlaying ? t('replay.pause', lang) : t('replay.play', lang)}
          >
            {isPlaying ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <rect x="6" y="4" width="4" height="16" rx="1"/>
                <rect x="14" y="4" width="4" height="16" rx="1"/>
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            )}
            <span lang={lang === 'bn' ? 'bn' : undefined}>
              {isPlaying ? t('replay.pause', lang) : t('replay.play', lang)}
            </span>
          </button>

          <input
            type="range"
            min={0}
            max={series.length - 1}
            value={currentDateIndex}
            onChange={handleSliderChange}
            className="replay-slider"
            aria-label="Timeline date slider"
          />

          <div className="replay-current-info">
            <time className="replay-current-date" dateTime={currentDate} lang={lang === 'bn' ? 'bn' : undefined}>
              {currentDate ? formatDate(currentDate, lang) : ''}
            </time>
            {currentPoint && (
              <div className="replay-current-badge">
                <span className="replay-current-score">
                  {formatNumber(currentPoint.flood_score, 1, lang)}
                </span>
                <RiskBadge level={currentPoint.flood_level} score={currentPoint.flood_score} lang={lang} />
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Middle: Rainfall chart with percentile lines, flood score, and milestone markers */}
      <section className="replay-chart-card" aria-label="Event chart">
        <div className="replay-chart-card__header">
          <h2 className="replay-chart-card__title" lang={lang === 'bn' ? 'bn' : undefined}>
            {lang === 'bn' ? 'বৃষ্টিপাত ও বন্যা ঝুঁকি সময়রেখা' : 'Rainfall & Flood Risk Timeline'}
          </h2>
          <span className="replay-chart-card__source">
            NASA GPM IMERG Final Run V07 & POWER
          </span>
        </div>

        <div
          className="replay-chart-container"
          role="img"
          aria-label={t('replay.title', lang)}
          aria-describedby="replay-chart-summary"
          style={{ width: '100%', height: 320 }}
        >
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 15, right: 15, left: -10, bottom: 5 }}
            >
              <XAxis
                dataKey="shortDate"
                tick={{ fontSize: 11, fill: 'var(--ink-muted)' }}
                tickLine={false}
                interval="preserveStartEnd"
                minTickGap={20}
              />
              {/* Left Y: Rainfall in mm */}
              <YAxis
                yAxisId="left"
                tick={{ fontSize: 11, fill: 'var(--ink-muted)' }}
                tickLine={false}
                axisLine={false}
                unit=" mm"
              />
              {/* Right Y: Flood Risk Score (0-100) */}
              <YAxis
                yAxisId="right"
                orientation="right"
                domain={[0, 100]}
                tick={{ fontSize: 11, fill: 'var(--risk-high)' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip content={<ReplayTooltip lang={lang} />} />
              <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ fontSize: 11, paddingBottom: 8 }}
              />

              {/* Moderate threshold line (40) */}
              <ReferenceLine
                yAxisId="right"
                y={40}
                stroke="#E0A100"
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{
                  value: lang === 'bn' ? 'মাঝারি (৪০)' : 'Moderate (40)',
                  fill: '#8F6600',
                  fontSize: 10,
                  position: 'insideBottomLeft',
                }}
              />

              {/* High threshold line (70) */}
              <ReferenceLine
                yAxisId="right"
                y={70}
                stroke="#C62828"
                strokeDasharray="4 4"
                strokeWidth={1}
                label={{
                  value: lang === 'bn' ? 'উচ্চ (৭০)' : 'High (70)',
                  fill: '#C62828',
                  fontSize: 10,
                  position: 'insideBottomLeft',
                }}
              />

              {/* Milestone Markers */}
              {data.first_moderate && (
                <ReferenceLine
                  yAxisId="left"
                  x={data.first_moderate.slice(5)}
                  stroke="#E0A100"
                  strokeDasharray="3 3"
                  label={{
                    value: lang === 'bn' ? 'প্রথম মাঝারি' : 'First Moderate',
                    fill: '#8F6600',
                    fontSize: 10,
                    position: 'top',
                  }}
                />
              )}

              {data.first_high && (
                <ReferenceLine
                  yAxisId="left"
                  x={data.first_high.slice(5)}
                  stroke="#C62828"
                  strokeWidth={1.5}
                  label={{
                    value: lang === 'bn' ? 'প্রথম উচ্চ' : 'First High',
                    fill: '#C62828',
                    fontSize: 10,
                    position: 'top',
                  }}
                />
              )}

              {data.reference_onset && (
                <ReferenceLine
                  yAxisId="left"
                  x={data.reference_onset.slice(5)}
                  stroke="#0B3D91"
                  strokeWidth={2}
                  label={{
                    value: lang === 'bn' ? 'বন্যা শুরু (১৬ জুন)' : 'Flood Onset (16 Jun)',
                    fill: '#0B3D91',
                    fontSize: 10,
                    position: 'top',
                  }}
                />
              )}

              {/* Current Slider Date Marker */}
              {currentDate && (
                <ReferenceLine
                  yAxisId="left"
                  x={currentDate.slice(5)}
                  stroke="var(--brand)"
                  strokeWidth={2}
                />
              )}

              {/* Rainfall Bars */}
              <Bar
                yAxisId="left"
                dataKey="rain_mm"
                name={t('replay.rainMm', lang)}
                fill="var(--nasa-blue, #0B3D91)"
                radius={[3, 3, 0, 0]}
                opacity={0.85}
              />

              {/* Flood Risk Score Line */}
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="flood_score"
                name={t('replay.floodScore', lang)}
                stroke="#C62828"
                strokeWidth={2.5}
                dot={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Text summary under chart per R-019 */}
        <p id="replay-chart-summary" className="replay-chart-summary" lang={lang === 'bn' ? 'bn' : undefined}>
          {chartSummaryText}
        </p>
      </section>

      {/* Bottom: Summary box with API lead time & fixed thresholds note */}
      <section className="replay-summary-box" aria-label="Lead time summary">
        <div className="replay-summary-banner">
          <div className="replay-summary-banner__icon" aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div className="replay-summary-banner__text">
            <h3 className="replay-summary-banner__title" lang={lang === 'bn' ? 'bn' : undefined}>
              {t('replay.leadTimeBanner', lang).replace('{days}', formatNumber(leadTimeDays, 0, lang))}
            </h3>
            <p className="replay-summary-banner__desc">
              {lang === 'bn'
                ? `প্রথম উচ্চ ঝুঁকি শুরু হয় ${data.first_high ? formatDate(data.first_high, lang) : ''} তারিখে এবং সরকারি বন্যা শুরু ১৬ জুন ২০২২-এ।`
                : `First High flood level was reached on ${data.first_high || '—'}, providing ${leadTimeDays} days of actionable lead time before the 16 June 2022 onset.`}
            </p>
          </div>
        </div>

        <div className="replay-method-note">
          <h4>{lang === 'bn' ? 'পদ্ধতিগত বৈধতা ও স্বচ্ছতা' : 'Methodological Validity & Transparency'}</h4>
          <p lang={lang === 'bn' ? 'bn' : undefined}>
            {t('replay.fixedThresholdsNote', lang)}
          </p>
          {data.citation && (
            <p className="replay-citation">
              <strong>{lang === 'bn' ? 'রেফারেন্স সূত্র:' : 'Reference Source:'}</strong> {data.citation}
            </p>
          )}
        </div>

        {/* Mandatory disclaimer */}
        <p className="replay-disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
          {t('disclaimer', lang)}
        </p>
      </section>
    </div>
  );
}

function ReplayTooltip({ active, payload, label, lang }) {
  if (!active || !payload || payload.length === 0) return null;

  const pt = payload[0].payload;
  return (
    <div className="replay-tooltip">
      <div className="replay-tooltip__date">
        {pt.date ? formatDate(pt.date, lang) : label}
      </div>
      <div className="replay-tooltip__item" style={{ color: 'var(--nasa-blue)' }}>
        <span>{t('replay.rainMm', lang)}:</span>
        <strong>{formatNumber(pt.rain_mm, 1, lang)} mm</strong>
      </div>
      <div className="replay-tooltip__item" style={{ color: '#C62828' }}>
        <span>{t('replay.floodScore', lang)}:</span>
        <strong>{formatNumber(pt.flood_score, 1, lang)}</strong>
      </div>
    </div>
  );
}

/* ─── Styles ───────────────────────────────────────────────────────── */
const style = document.createElement('style');
style.textContent = `
.replay-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-4) var(--space-8);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.replay-page--loading,
.replay-page--error {
  min-height: 50vh;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.replay-retry-btn {
  margin-top: var(--space-3);
  padding: 6px 16px;
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
}
.replay-retry-btn:hover {
  background: var(--brand-dark);
}

.replay-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--space-3);
}
.replay-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--brand);
  margin: 0;
}
.replay-subtitle {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  margin-top: 4px;
}

/* 5 Step chips */
.replay-steps {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: var(--space-2);
}

.step-chip {
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-2);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  text-align: left;
  transition: all var(--transition);
  font-family: inherit;
}
.step-chip:hover:not(:disabled) {
  border-color: var(--brand);
  transform: translateY(-1px);
  box-shadow: var(--shadow-sm);
}
.step-chip--active {
  border-color: var(--brand);
  background: color-mix(in srgb, var(--brand) 6%, var(--surface));
}
.step-chip--selected {
  border-color: var(--brand);
  background: color-mix(in srgb, var(--brand) 12%, var(--surface));
  box-shadow: 0 0 0 2px var(--brand);
}
.step-chip:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 2px;
}

.step-chip__number {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--border);
  color: var(--ink);
  font-weight: 700;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.step-chip--active .step-chip__number {
  background: var(--brand);
  color: #FFFFFF;
}

.step-chip__content {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.step-chip__label {
  font-size: var(--text-xs);
  font-weight: 700;
  color: var(--ink);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.step-chip__date {
  font-size: 11px;
  color: var(--ink-muted);
  white-space: nowrap;
}

/* Controls bar */
.replay-controls {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
}
.replay-controls__row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.replay-play-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  background: var(--brand);
  color: #FFFFFF;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
  font-family: inherit;
}
.replay-play-btn:hover {
  background: var(--brand-dark);
}
.replay-play-btn:focus-visible {
  outline: 3px solid var(--brand-dark);
  outline-offset: 2px;
}

.replay-slider {
  flex: 1;
  min-width: 180px;
  height: 6px;
  accent-color: var(--brand);
  cursor: pointer;
}

.replay-current-info {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}
.replay-current-date {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink);
  background: var(--bg);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
}
.replay-current-badge {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.replay-current-score {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--ink);
}

/* Chart card */
.replay-chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  box-shadow: var(--shadow-sm);
}
.replay-chart-card__header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  flex-wrap: wrap;
  gap: var(--space-2);
}
.replay-chart-card__title {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}
.replay-chart-card__source {
  font-size: 11px;
  color: var(--nasa-blue);
  font-weight: 500;
}
.replay-chart-summary {
  font-size: 12px;
  color: var(--ink-muted);
  border-top: 1px dashed var(--border);
  padding-top: var(--space-2);
  margin: 0;
}

/* Tooltip */
.replay-tooltip {
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
.replay-tooltip__date {
  font-weight: 700;
  color: var(--ink);
  border-bottom: 1px solid var(--border);
  padding-bottom: 2px;
  margin-bottom: 2px;
}
.replay-tooltip__item {
  display: flex;
  justify-content: space-between;
  gap: var(--space-3);
}

/* Summary Box */
.replay-summary-box {
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  box-shadow: var(--shadow-sm);
}

.replay-summary-banner {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  background: color-mix(in srgb, var(--brand) 8%, var(--bg));
  border: 1.5px solid var(--brand);
  border-radius: var(--radius-md);
  padding: var(--space-4);
}
.replay-summary-banner__icon {
  color: var(--brand);
  flex-shrink: 0;
}
.replay-summary-banner__title {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--brand-dark);
  margin: 0;
}
.replay-summary-banner__desc {
  font-size: var(--text-sm);
  color: var(--ink);
  margin-top: 4px;
}

.replay-method-note {
  background: var(--bg);
  border-radius: var(--radius-md);
  padding: var(--space-4);
  border: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}
.replay-method-note h4 {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}
.replay-method-note p {
  font-size: var(--text-xs);
  color: var(--ink-muted);
  line-height: 1.5;
  margin: 0;
}
.replay-citation {
  border-top: 1px dashed var(--border);
  padding-top: var(--space-2);
  font-style: italic;
}

.replay-disclaimer {
  font-size: 11px;
  color: var(--ink-muted);
  border-top: 1px solid var(--border);
  padding-top: var(--space-3);
  margin: 0;
}

/* Mobile responsive */
@media (max-width: 900px) {
  .replay-steps {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 600px) {
  .replay-steps {
    grid-template-columns: 1fr;
  }
  .replay-controls__row {
    flex-direction: column;
    align-items: stretch;
  }
  .replay-current-info {
    justify-content: space-between;
  }
}
`;
if (!document.getElementById('event-replay-styles')) {
  style.id = 'event-replay-styles';
  document.head.appendChild(style);
}
