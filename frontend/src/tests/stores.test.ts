import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

// ── localStorage mock ─────────────────────────────────────────────────────────
// jsdom provides a real localStorage implementation, but we want a fresh store
// for each test so state doesn't leak between tests.

function clearLocalStorage() {
  localStorage.clear();
}

beforeEach(() => {
  clearLocalStorage();
  // Reset module registry so each test gets a fresh store instance with the
  // current (cleared) localStorage state.
  vi.resetModules();
});

afterEach(() => {
  clearLocalStorage();
});

// ── config store ──────────────────────────────────────────────────────────────

describe('walkTimeSeconds store', () => {
  it('defaults to 300 when localStorage is empty', async () => {
    const { walkTimeSeconds } = await import('../lib/stores/config');

    let value: number | undefined;
    const unsub = walkTimeSeconds.subscribe((v) => { value = v; });
    expect(value).toBe(300);
    unsub();
  });

  it('persists updates to localStorage', async () => {
    const { walkTimeSeconds } = await import('../lib/stores/config');

    walkTimeSeconds.set(420);

    const stored = localStorage.getItem('rp_walk_time');
    expect(stored).toBe('420');
  });

  it('reads initial value from localStorage when present', async () => {
    // Write a value before importing the module
    localStorage.setItem('rp_walk_time', '600');

    const { walkTimeSeconds } = await import('../lib/stores/config');

    let value: number | undefined;
    const unsub = walkTimeSeconds.subscribe((v) => { value = v; });
    expect(value).toBe(600);
    unsub();
  });

  it('falls back to default for invalid JSON in localStorage', async () => {
    localStorage.setItem('rp_walk_time', 'not-valid-json{{{');

    const { walkTimeSeconds } = await import('../lib/stores/config');

    let value: number | undefined;
    const unsub = walkTimeSeconds.subscribe((v) => { value = v; });
    expect(value).toBe(300);
    unsub();
  });
});

// ── activeStopIndex store ─────────────────────────────────────────────────────

describe('activeStopIndex store', () => {
  it('defaults to 0', async () => {
    const { activeStopIndex } = await import('../lib/stores/config');

    let value: number | undefined;
    const unsub = activeStopIndex.subscribe((v) => { value = v; });
    expect(value).toBe(0);
    unsub();
  });
});

// ── dismissedGoNow store ──────────────────────────────────────────────────────

describe('dismissedGoNow store', () => {
  it('defaults to an empty Set', async () => {
    const { dismissedGoNow } = await import('../lib/stores/config');

    let value: Set<string> | undefined;
    const unsub = dismissedGoNow.subscribe((v) => { value = v; });
    expect(value).toBeInstanceOf(Set);
    expect(value?.size).toBe(0);
    unsub();
  });

  it('can add dismissed journey IDs', async () => {
    const { dismissedGoNow } = await import('../lib/stores/config');

    dismissedGoNow.update((s) => {
      const next = new Set(s);
      next.add('journey-123');
      return next;
    });

    let value: Set<string> | undefined;
    const unsub = dismissedGoNow.subscribe((v) => { value = v; });
    expect(value?.has('journey-123')).toBe(true);
    unsub();
  });
});
