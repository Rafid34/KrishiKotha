// Vitest tests for utils/risk.js — Section 9, task 7.7
import { describe, it, expect } from 'vitest';
import {
  levelColor,
  levelLabel,
  levelIcon,
  scoreToLevel,
  hazardLabel,
  LEVEL_META,
} from '../utils/risk.js';

describe('LEVEL_META', () => {
  it('has entries for low, moderate, high', () => {
    expect(Object.keys(LEVEL_META)).toEqual(
      expect.arrayContaining(['low', 'moderate', 'high']),
    );
  });

  it('each level has color, label, labelBn, icon', () => {
    for (const meta of Object.values(LEVEL_META)) {
      expect(typeof meta.color).toBe('string');
      expect(typeof meta.label).toBe('string');
      expect(typeof meta.labelBn).toBe('string');
      expect(['circle', 'triangle', 'square']).toContain(meta.icon);
    }
  });

  it('icon shapes are distinct (never colour alone)', () => {
    const icons = Object.values(LEVEL_META).map(m => m.icon);
    expect(new Set(icons).size).toBe(3);
  });
});

describe('levelColor', () => {
  it('returns low colour for low', () => {
    expect(levelColor('low')).toBe('var(--risk-low)');
  });
  it('returns moderate colour for moderate', () => {
    expect(levelColor('moderate')).toBe('var(--risk-moderate)');
  });
  it('returns high colour for high', () => {
    expect(levelColor('high')).toBe('var(--risk-high)');
  });
  it('falls back to low for unknown level', () => {
    expect(levelColor('unknown')).toBe('var(--risk-low)');
  });
});

describe('levelLabel', () => {
  it('returns English label for en', () => {
    expect(levelLabel('low', 'en')).toBe('Low');
    expect(levelLabel('moderate', 'en')).toBe('Moderate');
    expect(levelLabel('high', 'en')).toBe('High');
  });
  it('returns Bangla label for bn', () => {
    expect(levelLabel('low', 'bn')).toBe('কম');
    expect(levelLabel('moderate', 'bn')).toBe('মাঝারি');
    expect(levelLabel('high', 'bn')).toBe('বেশি');
  });
  it('defaults to English when lang omitted', () => {
    expect(levelLabel('high')).toBe('High');
  });
});

describe('levelIcon', () => {
  it('low → circle', () => expect(levelIcon('low')).toBe('circle'));
  it('moderate → triangle', () => expect(levelIcon('moderate')).toBe('triangle'));
  it('high → square', () => expect(levelIcon('high')).toBe('square'));
  it('unknown → circle fallback', () => expect(levelIcon('xyz')).toBe('circle'));
});

describe('scoreToLevel', () => {
  it('score < 40 → low', () => {
    expect(scoreToLevel(0)).toBe('low');
    expect(scoreToLevel(39.99)).toBe('low');
  });
  it('score 40 → moderate', () => {
    expect(scoreToLevel(40)).toBe('moderate');
  });
  it('score 69.99 → moderate', () => {
    expect(scoreToLevel(69.99)).toBe('moderate');
  });
  it('score 70 → high', () => {
    expect(scoreToLevel(70)).toBe('high');
  });
  it('score 100 → high', () => {
    expect(scoreToLevel(100)).toBe('high');
  });
});

describe('hazardLabel', () => {
  it('returns English labels', () => {
    expect(hazardLabel('drought', 'en')).toBe('Drought');
    expect(hazardLabel('flood', 'en')).toBe('Flood');
    expect(hazardLabel('salt', 'en')).toBe('Salinity');
  });
  it('returns Bangla labels', () => {
    expect(hazardLabel('drought', 'bn')).toBe('খরা');
    expect(hazardLabel('flood', 'bn')).toBe('বন্যা');
    expect(hazardLabel('salt', 'bn')).toBe('লবণাক্ততা');
  });
  it('returns raw key for unknown hazard', () => {
    expect(hazardLabel('unknown', 'en')).toBe('unknown');
  });
});
