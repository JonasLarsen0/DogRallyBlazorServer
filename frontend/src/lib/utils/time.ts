/**
 * time.ts — lightweight date/time helpers for the Rejseplan dashboard.
 * No external dependencies, fully tree-shakeable.
 */

/**
 * Parse an ISO 8601 string (or already-Date value) into a Date.
 * Returns null for invalid input rather than throwing.
 */
export function parseDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  if (value instanceof Date) return value;
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

/**
 * Format an ISO 8601 timestamp as "HH:MM" (local time).
 * Returns "--:--" for invalid input.
 */
export function formatTime(isoString: string | null | undefined): string {
  const d = parseDate(isoString);
  if (!d) return '--:--';
  return d.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit', hour12: false });
}

/**
 * Calculate seconds until a given date from now.
 * Positive = in the future, negative = in the past.
 */
export function secondsUntil(target: Date): number {
  return Math.round((target.getTime() - Date.now()) / 1000);
}

/**
 * Format a human-readable countdown string (Danish).
 *
 * Rules:
 *   - < -60 s in the past   → "Afgået"
 *   - -60 s … 0 s           → "Går nu!"
 *   - 0 … 60 s              → "Går nu!"  (imminent)
 *   - 1–59 min              → "X min"
 *   - ≥ 60 min              → "HH:MM"  (absolute time is more useful)
 */
export function formatCountdown(expectedTime: Date | string | null | undefined): string {
  const d = parseDate(expectedTime as string);
  if (!d) return '--';

  const secs = secondsUntil(d);

  if (secs < -60) return 'Afgået';
  if (secs <= 60)  return 'Går nu!';

  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins} min`;

  // Fall back to absolute time for far-future departures
  return formatTime(d.toISOString());
}

/**
 * Returns true when the departure should trigger the "Go Now" alert.
 * The threshold is: expectedTime ≤ now + walkSeconds.
 */
export function isGoNow(
  expectedTime: Date | string | null | undefined,
  walkSeconds: number
): boolean {
  const d = parseDate(expectedTime as string);
  if (!d) return false;
  const secs = secondsUntil(d);
  // Only fire if departure is still in the future (or just gone, ≤ 30 s past)
  return secs >= -30 && secs <= walkSeconds;
}

/**
 * Format a delay in seconds as a short badge string.
 * Returns null when there is no meaningful delay (< 60 s).
 */
export function formatDelay(delaySeconds: number): string | null {
  if (Math.abs(delaySeconds) < 60) return null;
  const mins = Math.round(delaySeconds / 60);
  return mins > 0 ? `+${mins} min` : `${mins} min`;
}

/**
 * Returns a CSS-friendly countdown class for coloring:
 *   'go-now'    → within walk time
 *   'imminent'  → < 5 min
 *   'soon'      → < 15 min
 *   'normal'    → everything else
 */
export function countdownClass(
  expectedTime: Date | string | null | undefined,
  walkSeconds: number
): 'go-now' | 'imminent' | 'soon' | 'normal' {
  const d = parseDate(expectedTime as string);
  if (!d) return 'normal';
  const secs = secondsUntil(d);
  if (secs <= walkSeconds) return 'go-now';
  if (secs <= 300)         return 'imminent';
  if (secs <= 900)         return 'soon';
  return 'normal';
}
