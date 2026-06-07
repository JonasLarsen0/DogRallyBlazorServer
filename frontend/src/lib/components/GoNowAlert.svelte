<script lang="ts">
  import { onDestroy } from 'svelte';
  import type { Departure } from '$lib/stores/websocket';
  import { dismissedGoNow } from '$lib/stores/config';
  import { formatCountdown } from '$lib/utils/time';

  export let departure: Departure;

  let countdown = formatCountdown(departure.expected_time);
  const timer = setInterval(() => {
    countdown = formatCountdown(departure.expected_time);
  }, 500);
  onDestroy(() => clearInterval(timer));

  function dismiss() {
    dismissedGoNow.update((s) => {
      const next = new Set(s);
      next.add(departure.journey_id ?? (departure.line + departure.planned_time));
      return next;
    });
  }

  // Transport type → emoji + label
  const TYPE_ICONS: Record<string, string> = {
    BUS:   '🚌',
    TRAIN: '🚆',
    METRO: '🚇',
    S:     '🚈',
    REG:   '🚄',
  };
  $: icon = TYPE_ICONS[departure.transport_type?.toUpperCase()] ?? '🚌';

  // Line type badge colours (inline for the overlay)
  const TYPE_COLORS: Record<string, string> = {
    BUS:   '#2563eb',
    TRAIN: '#16a34a',
    METRO: '#7c3aed',
    S:     '#ea580c',
    REG:   '#0891b2',
  };
  $: lineColor = TYPE_COLORS[departure.transport_type?.toUpperCase()] ?? '#2563eb';
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="overlay" on:click={dismiss} role="alertdialog" aria-modal="true" aria-live="assertive">
  <div class="alert-box" on:click|stopPropagation>
    <!-- Pulsing ring -->
    <div class="ring" aria-hidden="true"></div>

    <!-- Icon -->
    <div class="transport-icon" aria-hidden="true">{icon}</div>

    <!-- Line badge -->
    <div class="line-badge" style="background:{lineColor}">
      {departure.line}
    </div>

    <!-- Main text -->
    <div class="direction">{departure.direction}</div>

    {#if departure.stop_name}
      <div class="stop-name">Fra {departure.stop_name}</div>
    {/if}

    <!-- Countdown -->
    <div class="countdown" aria-label="Afgang om {countdown}">
      {countdown}
    </div>

    <button class="dismiss-btn" on:click={dismiss} aria-label="Afvis alarm">
      Afvis
    </button>

    <p class="hint">Klik udenfor for at afvise</p>
  </div>
</div>

<style>
  /* ── Full-screen overlay ── */
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(245, 158, 11, 0.18);
    backdrop-filter: blur(4px);
    animation: pulse-bg 1.2s ease-in-out infinite;
    cursor: pointer;
  }

  @keyframes pulse-bg {
    0%, 100% { background: rgba(245, 158, 11, 0.18); }
    50%       { background: rgba(245, 158, 11, 0.30); }
  }

  /* ── Alert box (glassmorphism card) ── */
  .alert-box {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 2.5rem 3rem;
    border-radius: 20px;
    background: rgba(10, 14, 26, 0.88);
    border: 2px solid rgba(245, 158, 11, 0.6);
    box-shadow:
      0 0 60px rgba(245, 158, 11, 0.35),
      0 0 120px rgba(245, 158, 11, 0.15),
      inset 0 1px 0 rgba(255,255,255,0.08);
    backdrop-filter: blur(20px);
    cursor: default;
    min-width: 340px;
    text-align: center;
    overflow: hidden;
  }

  /* ── Pulsing glow ring ── */
  .ring {
    position: absolute;
    inset: -2px;
    border-radius: 22px;
    border: 2px solid rgba(245, 158, 11, 0.5);
    animation: ring-pulse 1.2s ease-out infinite;
    pointer-events: none;
  }

  @keyframes ring-pulse {
    0%   { transform: scale(1);    opacity: 1;   }
    100% { transform: scale(1.05); opacity: 0;   }
  }

  /* ── Content ── */
  .transport-icon {
    font-size: 3rem;
    line-height: 1;
    filter: drop-shadow(0 0 12px rgba(245, 158, 11, 0.8));
  }

  .line-badge {
    display: inline-block;
    color: #fff;
    font-family: 'Courier New', monospace;
    font-size: 1rem;
    font-weight: 800;
    padding: 4px 16px;
    border-radius: 6px;
    box-shadow: 0 0 12px rgba(0,0,0,0.4);
    letter-spacing: 0.05em;
  }

  .direction {
    font-size: 1.5rem;
    font-weight: 700;
    color: #f1f5f9;
    letter-spacing: 0.02em;
    max-width: 420px;
  }

  .stop-name {
    font-size: 0.85rem;
    color: rgba(245, 158, 11, 0.75);
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  .countdown {
    font-family: 'Courier New', 'Lucida Console', monospace;
    font-size: 3.5rem;
    font-weight: 900;
    color: #f59e0b;
    text-shadow:
      0 0 20px rgba(245, 158, 11, 0.9),
      0 0 40px rgba(245, 158, 11, 0.5);
    letter-spacing: 0.06em;
    animation: text-pulse 1.0s ease-in-out infinite;
  }

  @keyframes text-pulse {
    0%, 100% { text-shadow: 0 0 20px rgba(245, 158, 11, 0.9), 0 0 40px rgba(245, 158, 11, 0.5); }
    50%       { text-shadow: 0 0 30px rgba(245, 158, 11, 1.0), 0 0 70px rgba(245, 158, 11, 0.7); }
  }

  /* ── Dismiss button ── */
  .dismiss-btn {
    margin-top: 0.5rem;
    padding: 0.5rem 1.5rem;
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
  }
  .dismiss-btn:hover {
    background: rgba(245, 158, 11, 0.28);
    border-color: rgba(245, 158, 11, 0.7);
  }

  .hint {
    margin: 0;
    font-size: 0.7rem;
    color: rgba(255,255,255,0.2);
    letter-spacing: 0.04em;
  }
</style>
