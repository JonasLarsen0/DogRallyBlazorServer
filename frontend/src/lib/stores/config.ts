import { writable } from 'svelte/store';

// ── Walk-time threshold (seconds) ─────────────────────────────────────────────
// Persisted to localStorage so the setting survives a page refresh.

function persistedWritable<T>(key: string, defaultValue: T) {
  let initial = defaultValue;

  if (typeof window !== 'undefined') {
    const stored = localStorage.getItem(key);
    if (stored !== null) {
      try {
        initial = JSON.parse(stored) as T;
      } catch {
        initial = defaultValue;
      }
    }
  }

  const store = writable<T>(initial);

  if (typeof window !== 'undefined') {
    store.subscribe((value) => {
      localStorage.setItem(key, JSON.stringify(value));
    });
  }

  return store;
}

/** Seconds of walk time to the stop. "Go Now" fires when departure ≤ walkTimeSeconds away. */
export const walkTimeSeconds = persistedWritable<number>('rp_walk_time', 300);

/** Which stop tab is currently selected (index into the departures array). */
export const activeStopIndex = writable<number>(0);

/** Whether the disturbance panel is open. */
export const disturbancePanelOpen = writable<boolean>(false);

/** Journey IDs that the user has manually dismissed from the Go-Now overlay. */
export const dismissedGoNow = writable<Set<string>>(new Set());
