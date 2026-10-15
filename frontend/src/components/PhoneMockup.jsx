import React, { useRef, useEffect } from 'react';
import { useLang } from '../i18n/index.jsx';

/**
 * PhoneMockup — centered feature phone mockup (about 320 px wide)
 * with an authentic monochrome LCD screen, scrollable message list,
 * physical keypad detailing, and under-phone SMS input controls.
 *
 * Implements Section 8.2, Section 8.4, and Task 9.1:
 * - Centered ~320 px wide mockup
 * - Monochrome LCD screen styling
 * - Message list inside the screen
 * - Bangla text inside screen is at least 18 px in Noto Sans Bengali
 * - Under-the-phone input box with placeholder SYLHET AMAN, Send button, Call button
 * - Fully accessible with keyboard navigation, >=44px touch targets, visible focus rings
 *
 * @param {{
 *   messages: Array<{
 *     id: string|number,
 *     sender: 'farmer'|'krishi',
 *     text: string,
 *     time?: string,
 *     rule_id?: string
 *   }>,
 *   inputValue: string,
 *   onInputChange: (val: string) => void,
 *   onSend: (text: string) => void,
 *   onCall?: () => void,
 *   loading?: boolean,
 *   placeholder?: string
 * }} props
 */
export default function PhoneMockup({
  messages = [],
  inputValue = '',
  onInputChange,
  onSend,
  onCall,
  loading = false,
  placeholder = 'SYLHET AMAN',
}) {
  const { lang } = useLang();
  const screenEndRef = useRef(null);

  // Auto-scroll LCD screen to bottom on new messages
  useEffect(() => {
    if (screenEndRef.current) {
      screenEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputValue.trim() || loading) return;
    onSend(inputValue.trim());
  };

  const handleKeypadTap = (key) => {
    if (onInputChange) {
      onInputChange(inputValue + key);
    }
  };

  return (
    <div className="phone-wrapper" role="region" aria-label="Feature phone simulator">
      {/* Feature Phone Body Casing (~320px wide) */}
      <div className="phone-casing">
        {/* Top earpiece speaker grill */}
        <div className="phone-earpiece" aria-hidden="true">
          <div className="phone-earpiece__slit" />
        </div>

        {/* Brand label */}
        <div className="phone-brand" aria-hidden="true">
          KRISHI 100
        </div>

        {/* Monochrome LCD Screen Display */}
        <div className="phone-screen" role="log" aria-live="polite" aria-label="Phone LCD screen">
          {/* LCD Status Header */}
          <div className="phone-screen__status-bar" aria-hidden="true">
            <span className="phone-screen__signal" title="Signal: Full satellite coverage">
              ▲ ▌▌▌
            </span>
            <span className="phone-screen__carrier">KrishiNet</span>
            <span className="phone-screen__battery" title="Battery: 85%">
              [ 85% ]
            </span>
          </div>

          {/* LCD Screen Content / Message List */}
          <div className="phone-screen__viewport">
            {messages.length === 0 ? (
              <div className="phone-screen__empty">
                <p className="phone-screen__hint-cmd">&gt; {placeholder}</p>
                <p className="phone-screen__hint-desc" lang={lang === 'bn' ? 'bn' : undefined}>
                  {lang === 'bn'
                    ? 'কৃষি পরামর্শ পেতে নিচে জেলার নাম ও ফসলের নাম লিখে পাঠান।'
                    : 'Send district and crop name below for NASA-driven advice.'}
                </p>
                <div className="phone-screen__hint-tips">
                  <span>16200 SMS</span>
                </div>
              </div>
            ) : (
              <div className="phone-screen__message-list">
                {messages.map((msg, idx) => {
                  const isFarmer = msg.sender === 'farmer';
                  // Test if text contains Bengali unicode characters (0x0980 - 0x09FF)
                  const isBangla = /[\u0980-\u09FF]/.test(msg.text);

                  return (
                    <div
                      key={msg.id ?? idx}
                      className={`phone-msg ${isFarmer ? 'phone-msg--farmer' : 'phone-msg--krishi'}`}
                    >
                      <div className="phone-msg__header" aria-hidden="true">
                        <span className="phone-msg__sender">
                          {isFarmer ? 'ME' : 'KRISHI'}
                        </span>
                        {msg.time && <span className="phone-msg__time">{msg.time}</span>}
                      </div>

                      {/* Message text with mandatory >=18px Noto Sans Bengali for Bangla */}
                      <p
                        className={`phone-msg__body ${isBangla ? 'phone-msg__body--bangla' : 'phone-msg__body--latin'}`}
                        lang={isBangla ? 'bn' : 'en'}
                        style={
                          isBangla
                            ? { fontSize: '18px', fontFamily: 'var(--font-bangla)', lineHeight: '1.5' }
                            : undefined
                        }
                      >
                        {msg.text}
                      </p>
                    </div>
                  );
                })}

                {loading && (
                  <div className="phone-msg phone-msg--loading" aria-label="Loading response">
                    <span className="phone-screen__blink">
                      {lang === 'bn' ? 'যাচাই হচ্ছে…' : 'Receiving SMS…'}
                    </span>
                  </div>
                )}
                <div ref={screenEndRef} />
              </div>
            )}
          </div>

          {/* LCD Bottom Sub-bar */}
          <div className="phone-screen__footer" aria-hidden="true">
            <span>[Menu]</span>
            <span>SMS</span>
            <span>[Back]</span>
          </div>
        </div>

        {/* Physical feature phone keypad hardware elements */}
        <div className="phone-keypad" aria-hidden="true">
          <div className="phone-keypad__nav-row">
            <button
              type="button"
              tabIndex={-1}
              className="phone-key phone-key--call"
              onClick={onCall}
              title="Call button"
            >
              📞
            </button>
            <div className="phone-keypad__dpad">
              <div className="phone-keypad__dpad-center" />
            </div>
            <button
              type="button"
              tabIndex={-1}
              className="phone-key phone-key--end"
              title="End call"
            >
              📴
            </button>
          </div>

          <div className="phone-keypad__grid">
            {[
              { num: '1', sub: '.,-' },
              { num: '2', sub: 'ABC' },
              { num: '3', sub: 'DEF' },
              { num: '4', sub: 'GHI' },
              { num: '5', sub: 'JKL' },
              { num: '6', sub: 'MNO' },
              { num: '7', sub: 'PQRS' },
              { num: '8', sub: 'TUV' },
              { num: '9', sub: 'WXYZ' },
              { num: '*', sub: ' ' },
              { num: '0', sub: '+' },
              { num: '#', sub: '↑' },
            ].map((k) => (
              <button
                key={k.num}
                type="button"
                tabIndex={-1}
                className="phone-num-key"
                onClick={() => handleKeypadTap(k.num)}
              >
                <span className="phone-num-key__digit">{k.num}</span>
                <span className="phone-num-key__sub">{k.sub}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Under the phone: SMS input box, Send button, Call button */}
      <form
        className="phone-controls"
        onSubmit={handleSubmit}
        role="form"
        aria-label="SMS messaging controls"
      >
        <div className="phone-controls__input-row">
          <label htmlFor="phone-sms-input" className="sr-only">
            {lang === 'bn' ? 'এসএমএস বার্তা লিখুন' : 'Enter SMS text'}
          </label>
          <input
            id="phone-sms-input"
            type="text"
            className="phone-controls__input"
            placeholder={placeholder}
            value={inputValue}
            onChange={(e) => onInputChange && onInputChange(e.target.value)}
            disabled={loading}
            autoComplete="off"
            spellCheck="false"
          />
        </div>

        <div className="phone-controls__actions">
          <button
            type="submit"
            className="phone-btn phone-btn--send"
            disabled={loading || !inputValue.trim()}
            aria-label={lang === 'bn' ? 'এসএমএস পাঠান' : 'Send SMS'}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
            <span>{loading ? (lang === 'bn' ? 'পাঠানো হচ্ছে…' : 'Sending…') : (lang === 'bn' ? 'পাঠান' : 'Send')}</span>
          </button>

          <button
            type="button"
            className="phone-btn phone-btn--call"
            onClick={onCall}
            aria-label={lang === 'bn' ? 'কল করুন (লেভেল ২ ভয়েস)' : 'Call (Level 2 voice)'}
            title={lang === 'bn' ? 'বাটন ফোনে ভয়েস কল শুনুন' : 'Listen to voice advice on phone'}
          >
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
            </svg>
            <span>{lang === 'bn' ? 'কল করুন' : 'Call'}</span>
          </button>
        </div>
      </form>
    </div>
  );
}

// Scoped styles for PhoneMockup
const style = typeof document !== 'undefined' ? document.createElement('style') : null;
if (style && !document.getElementById('phone-mockup-styles')) {
  style.id = 'phone-mockup-styles';
  style.textContent = `
.phone-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  width: 100%;
  max-width: 320px;
  margin: 0 auto;
}

/* Feature Phone Outer Casing */
.phone-casing {
  width: 100%;
  max-width: 320px;
  background: #242926;
  background: linear-gradient(180deg, #2D3430 0%, #1F2421 100%);
  border: 4px solid #3F4742;
  border-radius: 36px;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.28), 0 2px 6px rgba(0, 0, 0, 0.15), inset 0 1px 1px rgba(255, 255, 255, 0.1);
  padding: 16px 14px 20px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  user-select: none;
}

/* Speaker slit */
.phone-earpiece {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  margin-bottom: 6px;
}

.phone-earpiece__slit {
  width: 50px;
  height: 4px;
  background: #111413;
  border-radius: 2px;
  box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.8), 0 1px 1px rgba(255, 255, 255, 0.1);
}

.phone-brand {
  font-family: var(--font-latin);
  font-size: 10px;
  letter-spacing: 2px;
  font-weight: 700;
  color: #7D8882;
  margin-bottom: 8px;
  text-transform: uppercase;
}

/* Monochrome LCD Screen */
.phone-screen {
  width: 100%;
  background: #C4D3AB;
  background: linear-gradient(180deg, #CAD7B0 0%, #BDCC9E 100%);
  border: 3px solid #141715;
  border-radius: 8px;
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.35), 0 1px 1px rgba(255, 255, 255, 0.15);
  display: flex;
  flex-direction: column;
  height: 290px;
  overflow: hidden;
  color: #142210;
  font-family: var(--font-latin);
}

/* LCD Header Status Bar */
.phone-screen__status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 6px;
  border-bottom: 1px dashed rgba(20, 34, 16, 0.35);
  font-size: 11px;
  font-weight: 700;
  color: #142210;
  letter-spacing: 0.5px;
}

.phone-screen__signal {
  font-size: 10px;
}

.phone-screen__carrier {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.phone-screen__battery {
  font-size: 10px;
}

/* LCD Screen Viewport */
.phone-screen__viewport {
  flex: 1;
  padding: 8px 6px;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  scroll-behavior: smooth;
}

.phone-screen__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  gap: 8px;
  padding: 8px;
}

.phone-screen__hint-cmd {
  font-family: monospace;
  font-size: 15px;
  font-weight: 700;
  color: #142210;
  background: rgba(20, 34, 16, 0.12);
  padding: 4px 10px;
  border-radius: 4px;
  letter-spacing: 1px;
}

.phone-screen__hint-desc {
  font-size: 12px;
  color: #21331B;
  line-height: 1.4;
  margin: 0;
}

.phone-screen__hint-tips {
  font-size: 10px;
  font-weight: 700;
  color: #3B5233;
  letter-spacing: 1px;
  text-transform: uppercase;
}

/* Message List */
.phone-screen__message-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.phone-msg {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 8px;
  border-radius: 6px;
  max-width: 95%;
  word-break: break-word;
}

.phone-msg--farmer {
  align-self: flex-end;
  background: rgba(20, 34, 16, 0.18);
  border: 1px solid rgba(20, 34, 16, 0.3);
  text-align: right;
}

.phone-msg--krishi {
  align-self: flex-start;
  background: rgba(255, 255, 255, 0.35);
  border: 1px solid rgba(20, 34, 16, 0.25);
  text-align: left;
}

.phone-msg__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 9px;
  font-weight: 700;
  opacity: 0.7;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.phone-msg__body {
  margin: 0;
  color: #121F0E;
}

/* Latin messages (English commands) */
.phone-msg__body--latin {
  font-size: 13px;
  font-weight: 600;
  line-height: 1.35;
  font-family: var(--font-latin);
}

/* Bangla message text guaranteed >= 18px in Noto Sans Bengali */
.phone-msg__body--bangla {
  font-size: 18px !important;
  font-family: var(--font-bangla) !important;
  font-weight: 500;
  line-height: 1.5;
  color: #0E1A0C;
}

.phone-msg--loading {
  align-self: center;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 8px;
  background: transparent;
  color: #1A2E14;
}

.phone-screen__blink {
  animation: lcd-blink 1s infinite alternate;
}

@keyframes lcd-blink {
  from { opacity: 0.3; }
  to { opacity: 1; }
}

/* LCD Footer */
.phone-screen__footer {
  display: flex;
  justify-content: space-between;
  padding: 3px 6px;
  border-top: 1px dashed rgba(20, 34, 16, 0.35);
  font-size: 9px;
  font-weight: 700;
  color: #142210;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* Feature Phone Hardware Keypad */
.phone-keypad {
  width: 100%;
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.phone-keypad__nav-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}

.phone-key {
  width: 44px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid #161A18;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4), inset 0 1px 1px rgba(255, 255, 255, 0.2);
  cursor: pointer;
}

.phone-key--call {
  background: #2E6838;
  color: #FFFFFF;
}

.phone-key--end {
  background: #8B2C2C;
  color: #FFFFFF;
}

.phone-keypad__dpad {
  width: 52px;
  height: 38px;
  background: #1A1F1C;
  border: 2px solid #3A443E;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
}

.phone-keypad__dpad-center {
  width: 22px;
  height: 16px;
  background: #4D5952;
  border-radius: 6px;
}

.phone-keypad__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
}

.phone-num-key {
  height: 32px;
  background: #313A35;
  border: 1px solid #1E2420;
  border-radius: 8px;
  color: #E2E8E4;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 3px rgba(0, 0, 0, 0.35), inset 0 1px 1px rgba(255, 255, 255, 0.12);
  transition: background 0.1s;
  cursor: pointer;
}

.phone-num-key:hover {
  background: #3D4842;
}

.phone-num-key:active {
  background: #222925;
  transform: translateY(1px);
}

.phone-num-key__digit {
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.phone-num-key__sub {
  font-size: 7px;
  color: #8C9891;
  letter-spacing: 0.5px;
  margin-top: 1px;
}

/* Under-Phone Input Controls Form */
.phone-controls {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.phone-controls__input-row {
  width: 100%;
}

.phone-controls__input {
  width: 100%;
  padding: 12px 14px;
  font-size: var(--text-base);
  font-family: var(--font-latin);
  font-weight: 600;
  letter-spacing: 0.5px;
  color: var(--ink);
  background: var(--surface);
  border: 2px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  transition: border-color var(--transition);
  min-height: 44px;
}

.phone-controls__input:focus-visible {
  border-color: var(--brand);
  outline: 3px solid var(--brand);
  outline-offset: 1px;
}

.phone-controls__actions {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--space-2);
}

.phone-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-base);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition);
}

.phone-btn--send {
  background: var(--brand);
  color: #FFFFFF;
  border: none;
}

.phone-btn--send:hover:not(:disabled) {
  background: var(--brand-dark);
}

.phone-btn--send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.phone-btn--send:focus-visible {
  outline: 3px solid var(--brand-dark);
  outline-offset: 2px;
}

.phone-btn--call {
  background: var(--surface);
  color: var(--brand);
  border: 2px solid var(--brand);
}

.phone-btn--call:hover {
  background: var(--brand);
  color: #FFFFFF;
}

.phone-btn--call:focus-visible {
  outline: 3px solid var(--brand-dark);
  outline-offset: 2px;
}
`;
  document.head.appendChild(style);
}
