import { readable, writable, derived, get } from 'svelte/store';

// ── Type definitions ──────────────────────────────────────────────────────────

export interface Departure {
  journey_id: string;
  line: string;
  transport_type: string; // BUS | TRAIN | METRO | S | REG
  direction: string;
  planned_time: string;    // ISO 8601
  expected_time: string;   // ISO 8601
  delay_seconds: number;
  cancelled: boolean;
  track?: string;
  go_now?: boolean;
  stop_name?: string;
}

export interface StopDepartures {
  stop_id: string;
  stop_name: string;
  departures: Departure[];
  fetched_at: string; // ISO 8601
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
  type: 'update' | 'alert' | 'ping' | 'error';
  stops?: StopDepartures[];
  alerts?: Alert[];
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

    if (msg.type === 'update' && msg.stops) {
      departures.set(msg.stops);
      lastUpdated.set(new Date());
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
