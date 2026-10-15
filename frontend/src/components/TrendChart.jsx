import React from 'react';
// TrendChart — 60-day rainfall bars with baseline 90th percentile and soil wetness line
// Full implementation deferred to Phase 8 (requires Recharts).

/** @param {{ series: Array, districtId: string }} props */
export default function TrendChart({ series, districtId }) {
  return (
    <div className="trend-chart-stub" role="img" aria-label="Rainfall trend chart (Phase 8)">
      <p style={{ color: 'var(--ink-muted)', fontSize: 'var(--text-sm)' }}>
        Trend chart — Phase 8
      </p>
    </div>
  );
}
