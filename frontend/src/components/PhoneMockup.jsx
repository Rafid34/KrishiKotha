import React from 'react';
// PhoneMockup — feature phone frame with message list
// Full implementation is Phase 9.

export default function PhoneMockup({ messages = [], onSend, loading }) {
  return (
    <div className="phone-mockup-stub" aria-label="Phone mockup (Phase 9)">
      <p style={{ color: 'var(--ink-muted)', fontSize: 'var(--text-sm)' }}>
        Phone mockup — Phase 9
      </p>
    </div>
  );
}
