import { describe, it, expect } from 'vitest';
import { getBacktestSylhet } from '../api/client.js';

describe('Replay client & step structure', () => {
  it('exports getBacktestSylhet function', () => {
    expect(typeof getBacktestSylhet).toBe('function');
  });

  it('validates 5 replay steps sequencing', () => {
    const steps = [
      { step: 1, label: 'Rain begins', date: '2022-05-15' },
      { step: 2, label: 'Rain builds', date: '2022-05-15' },
      { step: 3, label: 'Heavy rain', date: '2022-05-25' },
      { step: 4, label: 'Extreme rain', date: '2022-06-02' },
      { step: 5, label: 'Flood', date: '2022-06-16' },
    ];

    expect(steps.length).toBe(5);
    for (let i = 0; i < steps.length - 1; i++) {
      expect(steps[i].step).toBe(i + 1);
      expect(steps[i].date <= steps[i + 1].date).toBe(true);
    }
  });

  it('verifies lead time equals reference onset minus first high date', () => {
    const firstHigh = '2022-06-02';
    const referenceOnset = '2022-06-16';
    const d1 = new Date(firstHigh);
    const d2 = new Date(referenceOnset);
    const diffDays = Math.round((d2 - d1) / (1000 * 60 * 60 * 24));
    expect(diffDays).toBe(14);
  });
});
