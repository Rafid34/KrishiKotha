import React from 'react';
// AdviceCard — Bangla and English advice with audio button
// Full implementation is Phase 9 (audio) and Phase 11 (TTS).

export default function AdviceCard({ advice }) {
  if (!advice) return null;
  return (
    <div className="advice-card card">
      <p lang="bn" style={{ fontSize: 'var(--text-lg)' }}>{advice.text_bn}</p>
      <p lang="en" style={{ color: 'var(--ink-muted)', fontSize: 'var(--text-sm)' }}>
        {advice.text_en}
      </p>
      {advice.rule_id && (
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--nasa-blue)' }}>
          Rule: {advice.rule_id}
        </p>
      )}
    </div>
  );
}
