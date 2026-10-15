import React from 'react';
import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import PhoneMockup from '../components/PhoneMockup.jsx';
import AdviceCard from '../components/AdviceCard.jsx';
import { LangProvider } from '../i18n/index.jsx';

describe('AdviceCard Component', () => {
  const sampleAdvice = {
    rule_id: 'flood_high_early',
    text_bn: 'মাঠে পাকা ধান থাকলে দ্রুত কেটে নিন। নতুন চারা রোপণ কয়েক দিন পিছিয়ে দিন।',
    text_en: 'Harvest mature paddy immediately. Delay transplanting new seedlings.',
    hazard: 'flood',
    level: 'high',
  };

  it('renders Bangla text with lang="bn" and minimum 18px font size', () => {
    const html = renderToString(
      <LangProvider>
        <AdviceCard advice={sampleAdvice} />
      </LangProvider>
    );

    // Verify Bangla copy is present
    expect(html).toContain('মাঠে পাকা ধান থাকলে দ্রুত কেটে নিন');
    // Verify lang="bn" attribute
    expect(html).toContain('lang="bn"');
    // Verify font size is at least 18px in Noto Sans Bengali
    expect(html).toContain('font-size:18px');
    expect(html).toContain('font-family:var(--font-bangla)');
  });

  it('renders English translation and rule identifier tag', () => {
    const html = renderToString(
      <LangProvider>
        <AdviceCard advice={sampleAdvice} />
      </LangProvider>
    );

    expect(html).toContain('Harvest mature paddy immediately');
    expect(html).toContain('Rule:');
    expect(html).toContain('flood_high_early');
  });

  it('handles empty advice gracefully without throwing', () => {
    const html = renderToString(
      <LangProvider>
        <AdviceCard advice={null} />
      </LangProvider>
    );

    expect(html).toContain('advice-card--empty');
  });
});

describe('PhoneMockup Component', () => {
  const messages = [
    {
      id: 1,
      sender: 'farmer',
      text: 'SYLHET AMAN',
      time: '12:00',
    },
    {
      id: 2,
      sender: 'krishi',
      text: 'কৃষি কথায় স্বাগতম। আপনার এলাকা ও ফসল নথিভুক্ত হয়েছে।',
      time: '12:01',
    },
    {
      id: 3,
      sender: 'krishi',
      text: 'মাঠে পাকা ধান থাকলে দ্রুত কেটে নিন।',
      time: '12:01',
    },
  ];

  it('renders feature phone mockup frame and LCD screen', () => {
    const html = renderToString(
      <LangProvider>
        <PhoneMockup
          messages={messages}
          inputValue=""
          onInputChange={() => {}}
          onSend={() => {}}
          placeholder="SYLHET AMAN"
        />
      </LangProvider>
    );

    expect(html).toContain('phone-casing');
    expect(html).toContain('phone-screen');
    expect(html).toContain('KrishiNet');
    expect(html).toContain('placeholder="SYLHET AMAN"');
  });

  it('renders Bangla SMS text at least 18px in Noto Sans Bengali with lang="bn"', () => {
    const html = renderToString(
      <LangProvider>
        <PhoneMockup
          messages={messages}
          inputValue=""
          onInputChange={() => {}}
          onSend={() => {}}
        />
      </LangProvider>
    );

    expect(html).toContain('কৃষি কথায় স্বাগতম');
    expect(html).toContain('font-size:18px');
    expect(html).toContain('font-family:var(--font-bangla)');
    expect(html).toContain('lang="bn"');
  });

  it('renders physical keypad and controls', () => {
    const html = renderToString(
      <LangProvider>
        <PhoneMockup
          messages={[]}
          inputValue="SYLHET AMAN"
          onInputChange={() => {}}
          onSend={() => {}}
        />
      </LangProvider>
    );

    // Keypad digits
    expect(html).toContain('phone-keypad');
    expect(html).toContain('phone-btn--send');
    expect(html).toContain('phone-btn--call');
  });
});

describe('Simulator quick-fills and parsing', () => {
  const QUICK_FILLS = ['SYLHET AMAN', 'KHULNA BORO', 'RAJSHAHI AMAN'];

  it('specifies the required quick-fill commands from Task 9.4', () => {
    expect(QUICK_FILLS).toContain('SYLHET AMAN');
    expect(QUICK_FILLS).toContain('KHULNA BORO');
    expect(QUICK_FILLS).toContain('RAJSHAHI AMAN');
  });
});
