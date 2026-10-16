import React, { useState, useEffect, useCallback } from 'react';
import PhoneMockup from '../components/PhoneMockup.jsx';
import AdviceCard from '../components/AdviceCard.jsx';
import RiskBadge from '../components/RiskBadge.jsx';
import { useLang, t } from '../i18n/index.jsx';
import { postSimSms, postAdvice, getRisk, getDistricts } from '../api/client.js';
import { hazardLabel } from '../utils/risk.js';
import { playAudio } from '../utils/audio.js';
import { formatNumber, formatDate } from '../utils/format.js';

// Client-side dictionary matching backend parser.py tokens
const DISTRICT_MAP = {
  sylhet: 'sylhet',
  'সিলেট': 'sylhet',
  sunamganj: 'sunamganj',
  'সুনামগঞ্জ': 'sunamganj',
  khulna: 'khulna',
  'খুলনা': 'khulna',
  satkhira: 'satkhira',
  'সাতক্ষীরা': 'satkhira',
  barishal: 'barishal',
  'বরিশাল': 'barishal',
  rajshahi: 'rajshahi',
  'রাজশাহী': 'rajshahi',
  rangpur: 'rangpur',
  'রংপুর': 'rangpur',
  chattogram: 'chattogram',
  chittagong: 'chattogram',
  'চট্টগ্রাম': 'chattogram',
};

const CROP_MAP = {
  aman: 'aman',
  'আমন': 'aman',
  boro: 'boro',
  'বোরো': 'boro',
  aus: 'aus',
  'আউশ': 'aus',
};

/** Parse SMS body into command structure */
function parseSmsText(raw) {
  if (!raw) return { command: 'unknown' };
  const trimmed = raw.trim().toLowerCase();
  if (['help', 'সাহায্য'].includes(trimmed)) return { command: 'help' };
  if (['stop', 'বন্ধ'].includes(trimmed)) return { command: 'stop' };
  if (['1', '১', '2', '২'].includes(trimmed)) return { command: 'feedback', value: trimmed };

  const tokens = trimmed.split(/\s+/).filter(tok => !['ধান', 'rice'].includes(tok));
  let district_id = null;
  let crop_id = null;

  for (const tok of tokens) {
    if (DISTRICT_MAP[tok] && !district_id) district_id = DISTRICT_MAP[tok];
    else if (CROP_MAP[tok] && !crop_id) crop_id = CROP_MAP[tok];
  }

  if (district_id && crop_id) {
    return { command: 'register', district_id, crop_id };
  }
  return { command: 'unknown' };
}

/**
 * Simulator — Farmer SMS & Voice Simulator page.
 * Implements Section 8.2, 8.4, and Tasks 9.1–9.4:
 * - Centered phone mockup (~320 px wide) with monochrome LCD screen
 * - Message list inside the screen (Bangla text >= 18px in Noto Sans Bengali)
 * - Under-the-phone input box, Send button, Call button
 * - Quick-fill buttons for SYLHET AMAN, KHULNA BORO, RAJSHAHI AMAN
 * - Advisory Diagnosis side panel with rule id, hazard, level, and underlying scores
 * - AdviceCard displaying Bangla and English text and rule id
 * - Mandatory disclaimer
 */
export default function Simulator({ initialDate = '' } = {}) {
  const { lang } = useLang();

  // State
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [simDate, setSimDate] = useState(initialDate);
  const [loading, setLoading] = useState(false);
  const [callNotice, setCallNotice] = useState(null);
  const [districts, setDistricts] = useState([]);

  // Active diagnosis metadata
  const [diagnosis, setDiagnosis] = useState(null);

  const [districtError, setDistrictError] = useState(null);

  // Default to the date returned by GET /api/risk without date parameter
  useEffect(() => {
    if (!initialDate) {
      getRisk()
        .then(res => {
          if (res?.date) {
            setSimDate(prev => prev || res.date);
          }
        })
        .catch(() => {});
    }
  }, [initialDate]);

  // Load districts metadata for labels
  const loadDistricts = useCallback(() => {
    setDistrictError(null);
    getDistricts()
      .then(setDistricts)
      .catch(err => setDistrictError(err.message || 'Failed to load districts'));
  }, []);

  useEffect(() => {
    loadDistricts();
  }, [loadDistricts]);

  /** Core SMS send handler */
  const handleSendMessage = useCallback(async (textToSend) => {
    const text = (textToSend || inputValue).trim();
    if (!text || loading) return;

    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'farmer',
      text,
      time: timestamp,
    };

    setMessages(prev => [...prev, userMsg]);
    setInputValue('');
    setLoading(true);
    setCallNotice(null);

    const parsed = parseSmsText(text);

    try {
      // 1. Call backend simulator endpoint
      const response = await postSimSms({
        from: '+8801700000000',
        body: text,
        date: simDate,
      });

      // 2. Add incoming replies to message list
      if (response?.replies && Array.isArray(response.replies)) {
        const replyMsgs = response.replies.map((r, i) => ({
          id: `krishi-${Date.now()}-${i}`,
          sender: 'krishi',
          text: r.text,
          time: timestamp,
        }));
        setMessages(prev => [...prev, ...replyMsgs]);
      }

      // 3. Update side panel diagnosis based on parsed command
      if (parsed.command === 'register') {
        const [adviceRes, riskRes] = await Promise.all([
          postAdvice({
            district_id: parsed.district_id,
            crop_id: parsed.crop_id,
            date: simDate,
            language: lang,
          }).catch(() => null),
          getRisk({ date: simDate }).catch(() => null),
        ]);

        const districtRisk = riskRes?.districts?.find(
          d => d.district_id === parsed.district_id
        );

        setDiagnosis({
          command: 'register',
          district_id: parsed.district_id,
          crop_id: parsed.crop_id,
          rule_id: adviceRes?.rule_id || 'none_low',
          hazard: adviceRes?.hazard || null,
          level: adviceRes?.level || 'low',
          scores: districtRisk ? {
            drought: districtRisk.drought,
            flood: districtRisk.flood,
            salt: districtRisk.salt,
          } : null,
          advice: adviceRes,
          subscriber_id: response?.subscriber_id,
          date: simDate,
        });
      } else if (parsed.command === 'help') {
        setDiagnosis({
          command: 'help',
          rule_id: 'help',
          hazard: null,
          level: null,
          scores: null,
          advice: null,
          statusText: t('simulator.statusHelp', lang),
          date: simDate,
        });
      } else if (parsed.command === 'stop') {
        setDiagnosis({
          command: 'stop',
          rule_id: 'stopped',
          hazard: null,
          level: null,
          scores: null,
          advice: null,
          statusText: t('simulator.statusStopped', lang),
          date: simDate,
        });
      } else {
        setDiagnosis({
          command: 'unknown',
          rule_id: 'help',
          hazard: null,
          level: null,
          scores: null,
          advice: null,
          statusText: t('simulator.statusUnrecognized', lang),
          date: simDate,
        });
      }
    } catch (err) {
      const errorMsg = {
        id: `err-${Date.now()}`,
        sender: 'krishi',
        text: lang === 'bn' ? 'সার্ভারে সংযোগ ব্যর্থ হয়েছে।' : 'Connection error. Please try again.',
        time: timestamp,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }, [inputValue, loading, simDate, lang]);

  /** Quick-fill helper */
  const handleQuickFill = useCallback((cmd) => {
    setInputValue(cmd);
    handleSendMessage(cmd);
  }, [handleSendMessage]);

  /** Voice Call handler (F2.4): plays the Bangla MP3 for the current advice, else text only. */
  const handleVoiceCall = useCallback(async () => {
    const advice = diagnosis?.advice;
    if (!advice) {
      setCallNotice(t('simulator.callNeedAdvice', lang));
      return;
    }

    setCallNotice(t('simulator.callNotice', lang));
    try {
      await playAudio(advice.audio_url);
      setCallNotice(null);
    } catch {
      setCallNotice(t('simulator.callUnavailable', lang));
    }
  }, [diagnosis, lang]);

  const handleClearChat = useCallback(() => {
    setMessages([]);
    setDiagnosis(null);
    setCallNotice(null);
  }, []);

  const activeDistrictMeta = diagnosis?.district_id
    ? districts.find(d => d.id === diagnosis.district_id)
    : null;

  return (
    <div className="simulator-page">
      {/* Page Title & Context Header */}
      <div className="simulator-header">
        <div className="simulator-header__titles">
          <h1 lang={lang === 'bn' ? 'bn' : undefined}>
            {t('simulator.title', lang)}
          </h1>
          <p className="simulator-header__subtitle" lang={lang === 'bn' ? 'bn' : undefined}>
            {t('simulator.subtitle', lang)}
          </p>
        </div>

        {/* Simulation Controls: Date picker & Reset */}
        <div className="simulator-header__controls">
          <label className="simulator-date-label">
            <span className="simulator-date-label__text">
              {t('simulator.dateLabel', lang)}:
            </span>
            <input
              type="date"
              className="simulator-date-input"
              value={simDate}
              onChange={(e) => setSimDate(e.target.value)}
              aria-label={t('simulator.dateLabel', lang)}
            />
          </label>

          <button
            type="button"
            className="simulator-demopick-btn"
            onClick={() => setSimDate('2022-06-16')}
            title={lang === 'bn' ? '১৬ জুন ২০২২ বন্যা ডেমো' : 'June 2022 flood demo'}
          >
            {lang === 'bn' ? 'জুন ২০২২ বন্যা ডেমো' : 'June 2022 flood demo'}
          </button>

          {messages.length > 0 && (
            <button
              type="button"
              className="simulator-clear-btn"
              onClick={handleClearChat}
              title={t('simulator.clearChat', lang)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              <span>{t('simulator.clearChat', lang)}</span>
            </button>
          )}
        </div>
      </div>

      {districtError && (
        <div className="simulator-error-banner" role="alert">
          <span>{lang === 'bn' ? 'জেলা তথ্য লোড করতে ব্যর্থ হয়েছে' : 'Failed to load districts'}: {districtError}</span>
          <button type="button" className="simulator-retry-btn" onClick={loadDistricts}>
            {lang === 'bn' ? 'পুনরায় চেষ্টা করুন' : 'Retry'}
          </button>
        </div>
      )}

      {/* Main 2-Column Grid (Desktop) / Stacked (Mobile) */}
      <div className="simulator-grid">
        {/* Left Column: Feature Phone Mockup & Quick-Fills */}
        <div className="simulator-phone-col">
          {/* Quick-fill command chips (Task 9.4) */}
          <div className="simulator-quickfills" role="group" aria-label={t('simulator.quickFillsTitle', lang)}>
            <span className="simulator-quickfills__label">
              {t('simulator.quickFillsTitle', lang)}:
            </span>
            <div className="simulator-quickfills__list">
              <button
                type="button"
                className="quickfill-chip quickfill-chip--flood"
                onClick={() => handleQuickFill('SYLHET AMAN')}
                disabled={loading}
              >
                SYLHET AMAN
                <span className="quickfill-chip__tag">{lang === 'bn' ? 'বন্যা' : 'Flood'}</span>
              </button>
              <button
                type="button"
                className="quickfill-chip quickfill-chip--salt"
                onClick={() => handleQuickFill('KHULNA BORO')}
                disabled={loading}
              >
                KHULNA BORO
                <span className="quickfill-chip__tag">{lang === 'bn' ? 'লবণ' : 'Salinity'}</span>
              </button>
              <button
                type="button"
                className="quickfill-chip quickfill-chip--drought"
                onClick={() => handleQuickFill('RAJSHAHI AMAN')}
                disabled={loading}
              >
                RAJSHAHI AMAN
                <span className="quickfill-chip__tag">{lang === 'bn' ? 'খরা' : 'Drought'}</span>
              </button>
              <button
                type="button"
                className="quickfill-chip quickfill-chip--cmd"
                onClick={() => handleQuickFill('HELP')}
                disabled={loading}
              >
                HELP
              </button>
              <button
                type="button"
                className="quickfill-chip quickfill-chip--cmd"
                onClick={() => handleQuickFill('STOP')}
                disabled={loading}
              >
                STOP
              </button>
            </div>
          </div>

          {/* Centered Phone Mockup */}
          <PhoneMockup
            messages={messages}
            inputValue={inputValue}
            onInputChange={setInputValue}
            onSend={handleSendMessage}
            onCall={handleVoiceCall}
            loading={loading}
            placeholder="SYLHET AMAN"
          />

          {callNotice && (
            <div className="simulator-call-notice" role="status">
              <span aria-hidden="true">🔊</span>
              <span>{callNotice}</span>
            </div>
          )}
        </div>

        {/* Right Column: Advisory Diagnosis Side Panel */}
        <div className="simulator-side-col">
          <div className="side-panel card" role="region" aria-label={t('simulator.sidePanelTitle', lang)}>
            <div className="side-panel__header">
              <h2 className="side-panel__title" lang={lang === 'bn' ? 'bn' : undefined}>
                {t('simulator.sidePanelTitle', lang)}
              </h2>
              <p className="side-panel__desc">
                {t('simulator.sidePanelDesc', lang)}
              </p>
            </div>

            {diagnosis ? (
              <div className="side-panel__content">
                {/* Rule & Trigger Hazard Row */}
                <div className="diagnosis-meta-grid">
                  <div className="diagnosis-meta-card">
                    <span className="diagnosis-meta-card__label">
                      {t('simulator.ruleId', lang)}
                    </span>
                    <span className="diagnosis-rule-badge">
                      {diagnosis.rule_id}
                    </span>
                  </div>

                  <div className="diagnosis-meta-card">
                    <span className="diagnosis-meta-card__label">
                      {t('simulator.triggerHazard', lang)}
                    </span>
                    <div className="diagnosis-hazard-row">
                      {diagnosis.hazard ? (
                        <>
                          <span className="diagnosis-hazard-name">
                            {hazardLabel(diagnosis.hazard, lang)}
                          </span>
                          <RiskBadge level={diagnosis.level} size="sm" />
                        </>
                      ) : (
                        <span className="diagnosis-hazard-none">
                          {diagnosis.statusText || 'None'}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Underlying Scores Cards (Section 8.2) */}
                {diagnosis.scores && (
                  <div className="diagnosis-scores-section">
                    <h3 className="diagnosis-section-title">
                      {t('simulator.underlyingScores', lang)}
                    </h3>
                    <div className="diagnosis-scores-grid">
                      {/* Drought */}
                      <div className="score-mini-card">
                        <div className="score-mini-card__head">
                          <span className="score-mini-card__title">
                            {hazardLabel('drought', lang)}
                          </span>
                          <RiskBadge level={diagnosis.scores.drought.level} size="sm" />
                        </div>
                        <div className="score-mini-card__value">
                          {formatNumber(diagnosis.scores.drought.score, lang, 1)}
                          <span className="score-mini-card__max">/100</span>
                        </div>
                      </div>

                      {/* Flood */}
                      <div className="score-mini-card">
                        <div className="score-mini-card__head">
                          <span className="score-mini-card__title">
                            {hazardLabel('flood', lang)}
                          </span>
                          <RiskBadge level={diagnosis.scores.flood.level} size="sm" />
                        </div>
                        <div className="score-mini-card__value">
                          {formatNumber(diagnosis.scores.flood.score, lang, 1)}
                          <span className="score-mini-card__max">/100</span>
                        </div>
                      </div>

                      {/* Salinity */}
                      <div className="score-mini-card">
                        <div className="score-mini-card__head">
                          <span className="score-mini-card__title">
                            {hazardLabel('salt', lang)}
                          </span>
                          <RiskBadge level={diagnosis.scores.salt.level} size="sm" />
                        </div>
                        <div className="score-mini-card__value">
                          {formatNumber(diagnosis.scores.salt.score, lang, 1)}
                          <span className="score-mini-card__max">/100</span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Advice Card (Bangla & English + Rule ID) */}
                {diagnosis.advice && (
                  <div className="diagnosis-advice-section">
                    <AdviceCard advice={diagnosis.advice} />
                  </div>
                )}

                {/* Context Footer: District, Crop & Date */}
                {activeDistrictMeta && (
                  <div className="diagnosis-context-footer">
                    <span>
                      {lang === 'bn' ? activeDistrictMeta.name_bn : activeDistrictMeta.name_en}
                    </span>
                    <span>•</span>
                    <span className="diagnosis-crop-pill">
                      {diagnosis.crop_id?.toUpperCase()}
                    </span>
                    <span>•</span>
                    <time dateTime={diagnosis.date}>
                      {formatDate(diagnosis.date, lang)}
                    </time>
                  </div>
                )}
              </div>
            ) : (
              <div className="side-panel__empty" role="status">
                <div className="side-panel__empty-icon" aria-hidden="true">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="var(--ink-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                    <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                    <line x1="6" y1="6" x2="6.01" y2="6" />
                    <line x1="6" y1="18" x2="6.01" y2="18" />
                  </svg>
                </div>
                <p className="side-panel__empty-text" lang={lang === 'bn' ? 'bn' : undefined}>
                  {t('simulator.emptyDiagnosis', lang)}
                </p>
                <div className="side-panel__empty-actions">
                  <button
                    type="button"
                    className="side-panel__try-btn"
                    onClick={() => handleQuickFill('SYLHET AMAN')}
                  >
                    {lang === 'bn' ? 'SYLHET AMAN দিয়ে পরীক্ষা করুন' : 'Try SYLHET AMAN'}
                  </button>
                </div>
              </div>
            )}

            {/* Mandatory NASA Disclaimer */}
            <p className="side-panel__disclaimer" lang={lang === 'bn' ? 'bn' : undefined}>
              {t('disclaimer', lang)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Scoped styles for Simulator Page
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style && !document.getElementById('simulator-page-styles')) {
  style.id = 'simulator-page-styles';
  style.textContent = `
.simulator-page {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--space-4) var(--space-4) var(--space-10) var(--space-4);
  width: 100%;
}

.simulator-error-banner {
  padding: var(--space-2) var(--space-4);
  background: #FEE2E2;
  border: 1px solid #F87171;
  color: #B91C1C;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: var(--text-xs);
}

.simulator-retry-btn {
  padding: 4px 12px;
  background: var(--brand);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
}
.simulator-retry-btn:hover {
  background: var(--brand-dark);
}

/* Header */
.simulator-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  flex-wrap: wrap;
  gap: var(--space-4);
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--space-4);
}

.simulator-header__titles {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.simulator-header__subtitle {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  margin: 0;
}

.simulator-header__controls {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.simulator-date-label {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--ink-muted);
}

.simulator-demopick-btn {
  padding: 6px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--ink);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--transition), border-color var(--transition);
}
.simulator-demopick-btn:hover {
  background: var(--surface-alt);
  border-color: var(--brand);
}

.simulator-date-input {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 6px 10px;
  font-size: var(--text-xs);
  background: var(--surface);
  color: var(--ink);
  font-family: inherit;
}

.simulator-date-input:focus-visible {
  outline: 3px solid var(--brand);
}

.simulator-clear-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 6px 12px;
  font-size: var(--text-xs);
  font-weight: 500;
  color: var(--ink-muted);
  cursor: pointer;
  transition: all var(--transition);
}

.simulator-clear-btn:hover {
  background: #FEE2E2;
  border-color: #F87171;
  color: #B91C1C;
}

.simulator-clear-btn:focus-visible {
  outline: 3px solid var(--brand);
}

/* Main Grid Layout */
.simulator-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-8);
  align-items: start;
}

@media (min-width: 1024px) {
  .simulator-grid {
    grid-template-columns: 360px 1fr;
  }
}

/* Left Column: Phone */
.simulator-phone-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  width: 100%;
}

/* Quick Fill Buttons */
.simulator-quickfills {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  width: 100%;
  max-width: 320px;
}

.simulator-quickfills__label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.simulator-quickfills__list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quickfill-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 11px;
  font-weight: 700;
  font-family: var(--font-latin);
  color: var(--ink);
  cursor: pointer;
  transition: all var(--transition);
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}

.quickfill-chip:hover:not(:disabled) {
  border-color: var(--brand);
  background: #F0F7F4;
  transform: translateY(-1px);
}

.quickfill-chip:focus-visible {
  outline: 3px solid var(--brand);
}

.quickfill-chip__tag {
  font-size: 9px;
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 600;
}

.quickfill-chip--flood .quickfill-chip__tag {
  background: #E0F2FE;
  color: #0369A1;
}

.quickfill-chip--salt .quickfill-chip__tag {
  background: #FEF3C7;
  color: #92400E;
}

.quickfill-chip--drought .quickfill-chip__tag {
  background: #FEE2E2;
  color: #B91C1C;
}

.quickfill-chip--cmd {
  background: #F3F4F6;
  color: #4B5563;
}

.simulator-call-notice {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-radius: var(--radius-md);
  padding: 8px 12px;
  font-size: var(--text-xs);
  color: #1E40AF;
  max-width: 320px;
  width: 100%;
}

/* Right Column: Advisory Diagnosis Side Panel */
.simulator-side-col {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  border: 1px solid var(--border);
}

.side-panel__header {
  display: flex;
  flex-direction: column;
  gap: 4px;
  border-bottom: 1px solid var(--border);
  padding-bottom: var(--space-3);
}

.side-panel__title {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
}

.side-panel__desc {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  margin: 0;
}

.side-panel__content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

/* Diagnosis Meta Cards */
.diagnosis-meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-3);
}

.diagnosis-meta-card {
  background: #F9F9F7;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-3) var(--space-4);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.diagnosis-meta-card__label {
  font-size: 11px;
  font-weight: 600;
  color: var(--ink-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.diagnosis-rule-badge {
  font-family: monospace;
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--nasa-blue);
  word-break: break-all;
}

.diagnosis-hazard-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.diagnosis-hazard-name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--ink);
}

.diagnosis-hazard-none {
  font-size: var(--text-xs);
  color: var(--ink-muted);
}

/* Scores Section */
.diagnosis-scores-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.diagnosis-section-title {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--ink);
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.diagnosis-scores-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-3);
}

@media (max-width: 600px) {
  .diagnosis-scores-grid {
    grid-template-columns: 1fr;
  }
}

.score-mini-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: var(--shadow-sm);
}

.score-mini-card__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
}

.score-mini-card__title {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--ink-muted);
}

.score-mini-card__value {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--ink);
  line-height: 1;
}

.score-mini-card__max {
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--ink-muted);
  margin-left: 2px;
}

/* Context Footer */
.diagnosis-context-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-xs);
  color: var(--ink-muted);
  border-top: 1px solid var(--border);
  padding-top: var(--space-3);
  font-weight: 500;
}

.diagnosis-crop-pill {
  background: #E8F5E9;
  color: #2E7D32;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 700;
}

/* Empty State */
.side-panel__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--space-3);
  padding: var(--space-8) var(--space-4);
  background: #FAF9F6;
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
}

.side-panel__empty-icon {
  opacity: 0.6;
}

.side-panel__empty-text {
  font-size: var(--text-sm);
  color: var(--ink-muted);
  max-width: 320px;
  margin: 0;
  line-height: 1.5;
}

.side-panel__empty-actions {
  margin-top: var(--space-2);
}

.side-panel__try-btn {
  background: var(--brand);
  color: #FFFFFF;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: var(--text-xs);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--transition);
}

.side-panel__try-btn:hover {
  background: var(--brand-dark);
}

.side-panel__try-btn:focus-visible {
  outline: 3px solid var(--brand-dark);
}

/* Disclaimer */
.side-panel__disclaimer {
  font-size: 11px;
  color: var(--ink-muted);
  border-top: 1px solid var(--border);
  padding-top: var(--space-3);
  margin: 0;
  line-height: 1.4;
}
`;
  document.head.appendChild(style);
}
