import React, { useState } from 'react';
import RiskBadge from './RiskBadge.jsx';
import { useLang } from '../i18n/index.jsx';
import { hazardLabel } from '../utils/risk.js';

/**
 * AdviceCard — renders generated crop advice with Bangla and English copy,
 * rule ID provenance, hazard badge, and Level 2 voice playback.
 *
 * Implements Section 8.2, 8.4, and Task 9.2:
 * - Bangla text at least 18 px in Noto Sans Bengali
 * - English text in Inter
 * - Rule ID tag
 * - Level 2 voice call / audio playback button
 *
 * @param {{
 *   advice: {
 *     rule_id: string,
 *     text_bn: string,
 *     text_en?: string,
 *     hazard?: string|null,
 *     level?: string|null,
 *     audio_url?: string|null
 *   }|null,
 *   onCall?: () => void
 * }} props
 */
export default function AdviceCard({ advice, onCall }) {
  const { lang } = useLang();
  const [isPlaying, setIsPlaying] = useState(false);

  if (!advice) {
    return (
      <div className="advice-card advice-card--empty card" role="region" aria-label="Advice card placeholder">
        <p className="advice-card__placeholder">
          {lang === 'bn'
            ? 'পরামর্শ দেখতে একটি জেলা ও ফসলের নাম পাঠান (যেমন: SYLHET AMAN)।'
            : 'Send a district and crop name (e.g. SYLHET AMAN) to view advice.'}
        </p>
      </div>
    );
  }

  const handlePlayAudio = () => {
    if (onCall) {
      onCall();
      return;
    }

    // Level 2 Web Speech fallback when audio_url is not a hosted file
    if (typeof window !== 'undefined' && 'speechSynthesis' in window && advice.text_bn) {
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(advice.text_bn);
        utterance.lang = 'bn-BD';
        utterance.rate = 0.9;
        utterance.onstart = () => setIsPlaying(true);
        utterance.onend = () => setIsPlaying(false);
        utterance.onerror = () => setIsPlaying(false);
        window.speechSynthesis.speak(utterance);
      } catch {
        setIsPlaying(false);
      }
    }
  };

  return (
    <div
      className="advice-card card"
      role="region"
      aria-label={lang === 'bn' ? 'ফসলের পরামর্শ' : 'Crop Advisory'}
    >
      <div className="advice-card__header">
        <div className="advice-card__meta">
          {advice.rule_id && (
            <span className="advice-card__rule-tag" title="Rule identifier in advice engine">
              <span className="advice-card__rule-prefix">Rule:</span> {advice.rule_id}
            </span>
          )}
          {advice.hazard && advice.level && (
            <div className="advice-card__hazard-badge">
              <span className="advice-card__hazard-name">
                {hazardLabel(advice.hazard, lang)}:
              </span>
              <RiskBadge level={advice.level} size="sm" />
            </div>
          )}
        </div>

        <button
          type="button"
          className={`advice-card__audio-btn ${isPlaying ? 'advice-card__audio-btn--playing' : ''}`}
          onClick={handlePlayAudio}
          title={lang === 'bn' ? 'বাংলা অডিও শুনুন (লেভেল ২)' : 'Play Bangla voice (Level 2)'}
          aria-label={lang === 'bn' ? 'পরামর্শ শুনুন' : 'Listen to advisory'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
          </svg>
          <span>{isPlaying ? (lang === 'bn' ? 'শুনছেন…' : 'Playing…') : (lang === 'bn' ? 'শুনুন' : 'Audio')}</span>
        </button>
      </div>

      <div className="advice-card__body">
        {/* Bangla text: guaranteed >= 18px in Noto Sans Bengali */}
        <p
          className="advice-card__text-bn"
          lang="bn"
          style={{ fontSize: '18px', fontFamily: 'var(--font-bangla)' }}
        >
          {advice.text_bn}
        </p>

        {/* English translation */}
        {advice.text_en && (
          <p className="advice-card__text-en" lang="en">
            {advice.text_en}
          </p>
        )}
      </div>
    </div>
  );
}

// Scoped styles for AdviceCard
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style && !document.getElementById('advice-card-styles')) {
  style.id = 'advice-card-styles';
  style.textContent = `
.advice-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  border: 1px solid var(--border);
  border-left: 4px solid var(--brand);
}

.advice-card--empty {
  border-left-color: var(--border);
  padding: var(--space-4);
  background: var(--surface);
}

.advice-card__placeholder {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  font-style: italic;
  margin: 0;
}

.advice-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border);
}

.advice-card__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.advice-card__rule-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #EEF4FD;
  color: var(--nasa-blue);
  border: 1px solid #BFD5F8;
  border-radius: var(--radius-sm);
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
  font-family: var(--font-latin);
}

.advice-card__rule-prefix {
  color: var(--ink-muted);
  font-weight: 500;
}

.advice-card__hazard-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--ink);
}

.advice-card__hazard-name {
  color: var(--ink-muted);
}

.advice-card__audio-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--surface);
  color: var(--brand);
  border: 1px solid var(--brand);
  border-radius: var(--radius-full);
  padding: 4px 12px;
  font-size: var(--text-xs);
  font-weight: 600;
  min-height: 32px;
  cursor: pointer;
  transition: all var(--transition);
}

.advice-card__audio-btn:hover {
  background: var(--brand);
  color: #FFFFFF;
}

.advice-card__audio-btn:focus-visible {
  outline: 3px solid var(--brand-dark);
  outline-offset: 2px;
}

.advice-card__audio-btn--playing {
  background: var(--brand);
  color: #FFFFFF;
  animation: pulse-audio 1.5s infinite;
}

@keyframes pulse-audio {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

.advice-card__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.advice-card__text-bn {
  font-size: 18px !important;
  font-family: var(--font-bangla) !important;
  line-height: 1.6;
  color: var(--ink);
  margin: 0;
  font-weight: 500;
}

.advice-card__text-en {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  line-height: 1.5;
  margin: 0;
  font-family: var(--font-latin);
  border-top: 1px dashed var(--border);
  padding-top: var(--space-2);
}
`;
  document.head.appendChild(style);
}
