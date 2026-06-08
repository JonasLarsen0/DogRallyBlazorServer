import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { formatCountdown, isGoNow, formatTime, formatDelay } from '../lib/utils/time';

// We pin "now" to a fixed point so tests are deterministic.
const FIXED_NOW = new Date('2024-06-01T12:00:00.000Z').getTime();

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(FIXED_NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

// ── formatCountdown ───────────────────────────────────────────────────────────

describe('formatCountdown', () => {
  it('returns "--" for null / undefined input', () => {
    expect(formatCountdown(null)).toBe('--');
    expect(formatCountdown(undefined)).toBe('--');
    expect(formatCountdown('')).toBe('--');
  });

  it('returns "Afgået" when departure is more than 60 s in the past', () => {
    // 90 seconds ago
    const past = new Date(FIXED_NOW - 90_000).toISOString();
    expect(formatCountdown(past)).toBe('Afgået');
  });

  it('returns "Går nu!" when departure is 0 seconds away (exactly now)', () => {
    const now = new Date(FIXED_NOW).toISOString();
    expect(formatCountdown(now)).toBe('Går nu!');
  });

  it('returns "Går nu!" when departure is within 0–60 seconds', () => {
    const imminent = new Date(FIXED_NOW + 30_000).toISOString();
    expect(formatCountdown(imminent)).toBe('Går nu!');

    const boundary = new Date(FIXED_NOW + 60_000).toISOString();
    expect(formatCountdown(boundary)).toBe('Går nu!');
  });

  it('returns "Går nu!" when departure just passed (within grace -60 s)', () => {
    // 30 seconds in the past — still within the -60 s grace window
    const justGone = new Date(FIXED_NOW - 30_000).toISOString();
    expect(formatCountdown(justGone)).toBe('Går nu!');
  });

  it('returns "1 min" for 65 seconds', () => {
    const t = new Date(FIXED_NOW + 65_000).toISOString();
    expect(formatCountdown(t)).toBe('1 min');
  });

  it('returns "2 min" for 125 seconds', () => {
    const t = new Date(FIXED_NOW + 125_000).toISOString();
    expect(formatCountdown(t)).toBe('2 min');
  });

  it('returns absolute time (HH:MM) when departure is ≥ 60 minutes away', () => {
    // 61 minutes from now in ISO — result should be a time string like "13:01"
    const farFuture = new Date(FIXED_NOW + 61 * 60_000).toISOString();
    const result = formatCountdown(farFuture);
    // Should NOT contain "min" and should look like a time
    expect(result).not.toContain('min');
    expect(result).toMatch(/^\d{2}:\d{2}$/);
  });
});

// ── isGoNow ───────────────────────────────────────────────────────────────────

describe('isGoNow', () => {
  it('returns false for null / undefined', () => {
    expect(isGoNow(null, 300)).toBe(false);
    expect(isGoNow(undefined, 300)).toBe(false);
  });

  it('returns true when seconds_until equals walkSeconds exactly', () => {
    const t = new Date(FIXED_NOW + 300_000).toISOString(); // exactly 300 s away
    expect(isGoNow(t, 300)).toBe(true);
  });

  it('returns true when departure is within walk time', () => {
    const t = new Date(FIXED_NOW + 120_000).toISOString(); // 2 min away
    expect(isGoNow(t, 300)).toBe(true);
  });

  it('returns false when departure is beyond walk time', () => {
    const t = new Date(FIXED_NOW + 600_000).toISOString(); // 10 min away
    expect(isGoNow(t, 300)).toBe(false);
  });

  it('returns true when departure just passed (within -30 s grace)', () => {
    const t = new Date(FIXED_NOW - 20_000).toISOString(); // 20 s ago
    expect(isGoNow(t, 300)).toBe(true);
  });

  it('returns false when departure is more than 30 s in the past', () => {
    const t = new Date(FIXED_NOW - 60_000).toISOString(); // 60 s ago
    expect(isGoNow(t, 300)).toBe(false);
  });
});

// ── formatTime ────────────────────────────────────────────────────────────────

describe('formatTime', () => {
  it('returns "--:--" for null / undefined / empty string', () => {
    expect(formatTime(null)).toBe('--:--');
    expect(formatTime(undefined)).toBe('--:--');
    expect(formatTime('')).toBe('--:--');
  });

  it('returns "--:--" for an invalid date string', () => {
    expect(formatTime('not-a-date')).toBe('--:--');
  });

  it('formats a valid ISO datetime to HH:MM (da-DK locale)', () => {
    // Using a UTC timestamp; result depends on local offset, so just check shape
    const iso = '2024-06-01T09:30:00.000Z';
    const result = formatTime(iso);
    // Should match HH:MM pattern
    expect(result).toMatch(/^\d{2}:\d{2}$/);
  });
});

// ── formatDelay ───────────────────────────────────────────────────────────────

describe('formatDelay', () => {
  it('returns null for delay < 60 s (not meaningful)', () => {
    expect(formatDelay(0)).toBeNull();
    expect(formatDelay(59)).toBeNull();
    expect(formatDelay(-30)).toBeNull();
  });

  it('returns "+X min" for positive delay', () => {
    expect(formatDelay(120)).toBe('+2 min');
    expect(formatDelay(90)).toBe('+2 min'); // rounds to 2
  });

  it('returns "-X min" for negative delay (early)', () => {
    expect(formatDelay(-120)).toBe('-2 min');
  });
});
