<script lang="ts">
  import { connected } from '$lib/stores/websocket';

  type Status = 'connected' | 'reconnecting' | 'disconnected';

  export let status: Status = 'disconnected';

  let internalStatus: Status;
  $: internalStatus = $connected ? 'connected' : 'reconnecting';
  $: displayStatus  = status !== 'disconnected' ? status : internalStatus;

  const LABELS: Record<Status, string> = {
    connected:    'Live',
    reconnecting: 'Forbinder…',
    disconnected: 'Afbrudt',
  };
</script>

<span
  class="status status-{displayStatus}"
  role="status"
  aria-live="polite"
  title="{{ connected: 'Tilsluttet til server', reconnecting: 'Forsøger at genoprette forbindelsen', disconnected: 'Forbindelsen er afbrudt' }[displayStatus]}"
>
  <span class="indicator" aria-hidden="true">
    {#if displayStatus === 'disconnected'}
      <span class="x-mark">✕</span>
    {:else}
      <span class="dot"></span>
    {/if}
  </span>
  <span class="label">{LABELS[displayStatus]}</span>
</span>

<style>
  .status {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 0.28rem 0.65rem;
    border-radius: 20px;
    border: 1px solid transparent;
    white-space: nowrap;
    transition: all 0.35s ease;
    user-select: none;
    font-family: system-ui, sans-serif;
    text-transform: uppercase;
  }

  /* ── Connected — green heartbeat ── */
  .status-connected {
    color: var(--accent-green);
    background: rgba(0, 230, 118, 0.08);
    border-color: rgba(0, 230, 118, 0.2);
  }
  .status-connected .dot {
    background: var(--accent-green);
    box-shadow: 0 0 0 0 rgba(0, 230, 118, 0.6);
    animation: heartbeat 2s ease-out infinite;
  }

  @keyframes heartbeat {
    0%   { box-shadow: 0 0 0 0   rgba(0, 230, 118, 0.7); }
    40%  { box-shadow: 0 0 0 5px rgba(0, 230, 118, 0);   }
    100% { box-shadow: 0 0 0 0   rgba(0, 230, 118, 0);   }
  }

  /* ── Reconnecting — amber spinning ring ── */
  .status-reconnecting {
    color: var(--accent-amber);
    background: rgba(255, 184, 0, 0.07);
    border-color: rgba(255, 184, 0, 0.2);
  }
  .status-reconnecting .dot {
    width: 9px !important;
    height: 9px !important;
    background: transparent !important;
    border: 2px solid var(--accent-amber);
    border-top-color: transparent;
    animation: spin-ring 0.8s linear infinite;
  }

  @keyframes spin-ring {
    to { transform: rotate(360deg); }
  }

  /* ── Disconnected — red X with shake ── */
  .status-disconnected {
    color: var(--accent-red);
    background: rgba(255, 59, 92, 0.08);
    border-color: rgba(255, 59, 92, 0.2);
    animation: shake 0.5s ease 0s 1;
  }

  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    20%      { transform: translateX(-3px); }
    40%      { transform: translateX(3px); }
    60%      { transform: translateX(-2px); }
    80%      { transform: translateX(2px); }
  }

  .x-mark {
    font-size: 0.65rem;
    font-weight: 900;
    color: var(--accent-red);
    line-height: 1;
  }

  /* ── Shared dot base ── */
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
    display: block;
  }

  .indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 10px;
    height: 10px;
    flex-shrink: 0;
  }

  .label {
    font-size: 0.68rem;
  }
</style>
