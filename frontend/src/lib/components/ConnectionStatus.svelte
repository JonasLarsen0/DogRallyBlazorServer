<script lang="ts">
  import { connected } from '$lib/stores/websocket';

  type Status = 'connected' | 'reconnecting' | 'disconnected';

  export let status: Status = 'disconnected';

  // Derive status from the shared store unless a prop override is given
  let internalStatus: Status;
  $: {
    internalStatus = $connected ? 'connected' : 'reconnecting';
  }
  $: displayStatus = status !== 'disconnected' ? status : internalStatus;

  const LABELS: Record<Status, string> = {
    connected:    'Tilsluttet',
    reconnecting: 'Forbinder…',
    disconnected: 'Afbrudt',
  };
</script>

<span class="connection-status status-{displayStatus}" role="status" aria-live="polite">
  <span class="dot" aria-hidden="true"></span>
  <span class="label">{LABELS[displayStatus]}</span>
</span>

<style>
  .connection-status {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    padding: 0.3rem 0.7rem;
    border-radius: 20px;
    border: 1px solid transparent;
    white-space: nowrap;
    transition: all 0.3s ease;
    user-select: none;
  }

  /* ── Connected ── */
  .status-connected {
    color: #22c55e;
    background: rgba(34, 197, 94, 0.1);
    border-color: rgba(34, 197, 94, 0.25);
  }
  .status-connected .dot {
    background: #22c55e;
    box-shadow: 0 0 6px rgba(34, 197, 94, 0.8);
  }

  /* ── Reconnecting ── */
  .status-reconnecting {
    color: #f59e0b;
    background: rgba(245, 158, 11, 0.1);
    border-color: rgba(245, 158, 11, 0.25);
  }
  .status-reconnecting .dot {
    background: #f59e0b;
    animation: spin-ring 1s linear infinite;
    border-radius: 50%;
    box-shadow: 0 0 6px rgba(245, 158, 11, 0.6);
  }

  /* ── Disconnected ── */
  .status-disconnected {
    color: #dc2626;
    background: rgba(220, 38, 38, 0.1);
    border-color: rgba(220, 38, 38, 0.25);
  }
  .status-disconnected .dot {
    background: #dc2626;
    box-shadow: 0 0 6px rgba(220, 38, 38, 0.6);
  }

  /* ── Dot base ── */
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  /* Reconnecting spinner: fake spin via box-shadow */
  @keyframes spin-ring {
    0%   { box-shadow: 2px 0 6px rgba(245, 158, 11, 0.8), -2px 0 0 rgba(245,158,11,0); }
    50%  { box-shadow: -2px 0 6px rgba(245, 158, 11, 0.8), 2px 0 0 rgba(245,158,11,0); }
    100% { box-shadow: 2px 0 6px rgba(245, 158, 11, 0.8), -2px 0 0 rgba(245,158,11,0); }
  }
</style>
