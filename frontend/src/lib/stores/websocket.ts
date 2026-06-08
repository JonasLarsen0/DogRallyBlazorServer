import { writable, derived } from 'svelte/store';

// ── Type definitions ──────────────────────────────────────────────────────────

export interface Departure {
  journey_id: string;
  line: string;
  /** Backend field: vehicle_type (BUS | TRAIN | METRO | S | REG).
   *  Aliased locally as transport_type for component compatibility. */
  vehicle_type?: string;
  /** Normalised alias — populated from vehicle_type in the message handler. */
  transport_type: string;
  direction: string;
  planned_time: string;    // ISO 8601
  expected_time: string;   // ISO 8601
  /** Backend sends delay_minutes; we convert to delay_seconds on receipt. */
  delay_minutes?: number;
  delay_seconds: number;
  cancelled: boolean;
  track?: string;
  /** Seconds until departure (live, from backend). */
  seconds_until?: number;
  go_now?: boolean;
  stop_name?: string;
}

export interface StopDepartures {
  stop_id: string;
  stop_name: string;
  departures: Departure[];
  /** ISO 8601 timestamp — backend may send as fetched_at or timestamp. */
  fetched_at?: string;
  timestamp?: string;
}

export interface Alert {
  id: string;
  title: string;
  description?: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  affected_lines?: string[];
  valid_from?: string;
  valid_to?: string;
}

export interface WsMessage {
  /** Backend sends "departures_update"; legacy support for "update" kept. */
  type: 'departures_update' | 'update' | 'alert' | 'ping' | 'error';
  stops?: StopDepartures[];
  alerts?: Alert[];
  /** Walk time in seconds, sent alongside departures. */
  walk_seconds?: number;
  /** Top-level timestamp on the message. */
  timestamp?: string;
  message?: string;
}

// ── State stores ──────────────────────────────────────────────────────────────

export const departures = writable<StopDepartures[]>([]);
export const alerts     = writable<Alert[]>([]);
export const connected  = writable<boolean>(false);
export const lastUpdated = writable<Date | null>(null);

// ── WebSocket manager ─────────────────────────────────────────────────────────

const WS_URL = (typeof window !== 'undefined' && (import.meta.env.VITE_WS_URL as string)) ||
               'ws://localhost:8000/ws';

const BACKOFF_STEPS = [1000, 2000, 4000, 8000, 15000, 30000];

let socket: WebSocket | null = null;
let retryCount = 0;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
let destroyed = false;
let pingInterval: ReturnType<typeof setInterval> | null = null;

function clearPingInterval() {
  if (pingInterval !== null) {
    clearInterval(pingInterval);
    pingInterval = null;
  }
}

function scheduleReconnect() {
  if (destroyed) return;
  const delay = BACKOFF_STEPS[Math.min(retryCount, BACKOFF_STEPS.length - 1)];
  retryCount++;
  retryTimer = setTimeout(connect, delay);
}

function connect() {
  if (destroyed) return;
  if (retryTimer !== null) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }

  try {
    socket = new WebSocket(WS_URL);
  } catch (e) {
    scheduleReconnect();
    return;
  }

  socket.addEventListener('open', () => {
    retryCount = 0;
    connected.set(true);

    // Send a ping every 25 s to keep the connection alive
    clearPingInterval();
    pingInterval = setInterval(() => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25_000);
  });

  socket.addEventListener('message', (event: MessageEvent) => {
    let msg: WsMessage;
    try {
      msg = JSON.parse(event.data as string) as WsMessage;
    } catch {
      return;
    }

    // Accept both "departures_update" (current backend) and legacy "update"
    if ((msg.type === 'departures_update' || msg.type === 'update') && msg.stops) {
      // Normalise per-departure fields so components use a consistent shape
      const normalised = msg.stops.map((stop) => ({
        ...stop,
        // Prefer fetched_at, fall back to message-level timestamp
        fetched_at: stop.fetched_at ?? stop.timestamp ?? msg.timestamp,
        departures: stop.departures.map((dep) => ({
          ...dep,
          // Normalise vehicle_type → transport_type
          transport_type: dep.transport_type ?? dep.vehicle_type ?? 'BUS',
          // Normalise delay_minutes → delay_seconds
          delay_seconds: dep.delay_seconds ?? (dep.delay_minutes != null ? dep.delay_minutes * 60 : 0),
        })),
      }));
      departures.set(normalised);
      lastUpdated.set(new Date());
    }
    // Backend may bundle alerts in the same departures_update message
    if (msg.alerts && msg.alerts.length > 0) {
      alerts.set(msg.alerts);
    }
    if (msg.type === 'alert' && msg.alerts) {
      alerts.set(msg.alerts);
    }
    if (msg.type === 'error') {
      console.warn('[WS] Server error:', msg.message);
    }
  });

  socket.addEventListener('close', () => {
    connected.set(false);
    clearPingInterval();
    if (!destroyed) scheduleReconnect();
  });

  socket.addEventListener('error', () => {
    // The 'close' event will fire right after; let that handle reconnect
    connected.set(false);
    clearPingInterval();
  });
}

// ── Bootstrap (client-side only) ─────────────────────────────────────────────

if (typeof window !== 'undefined') {
  connect();

  // Clean up when the tab is closed
  window.addEventListener('beforeunload', () => {
    destroyed = true;
    clearPingInterval();
    socket?.close();
  });
}

// ── Derived helpers ───────────────────────────────────────────────────────────

/** Flat list of all go_now departures across all stops */
export const goNowDepartures = derived(departures, ($stops) =>
  $stops.flatMap((s) =>
    s.departures
      .filter((d) => d.go_now && !d.cancelled)
      .map((d) => ({ ...d, stop_name: d.stop_name ?? s.stop_name }))
  )
);

/** Total alert count */
export const alertCount = derived(alerts, ($a) => $a.length);
