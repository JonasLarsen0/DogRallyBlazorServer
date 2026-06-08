<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
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

  // Transport type → emoji
  const TYPE_ICONS: Record<string, string> = {
    BUS:   '🚌',
    TRAIN: '🚆',
    METRO: '🚇',
    S:     '🚈',
    REG:   '🚄',
    IC:    '🚄',
    RE:    '🚆',
  };
  $: icon = TYPE_ICONS[(departure.transport_type ?? 'BUS').toUpperCase()] ?? '🚌';

  // Line badge colour
  const TYPE_COLORS: Record<string, string> = {
    BUS:   '#3b82f6',
    TRAIN: '#00e676',
    METRO: '#a855f7',
    S:     '#f97316',
    REG:   '#14b8a6',
    IC:    '#ffb800',
    RE:    '#00d4ff',
  };
  $: lineColor = TYPE_COLORS[(departure.transport_type ?? 'BUS').toUpperCase()] ?? '#3b82f6';

  // 3-beep alert on mount
  onMount(() => {
    try {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      [0, 0.18, 0.36].forEach((offset) => {
        const osc  = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 880;
        osc.type = 'sine';
        gain.gain.setValueAtTime(0.18, ctx.currentTime + offset);
        gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + offset + 0.09);
        osc.start(ctx.currentTime + offset);
        osc.stop(ctx.currentTime + offset + 0.1);
      });
    } catch { /* AudioContext not available — silent */ }
  });
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="overlay"
  on:click={dismiss}
  role="alertdialog"
  aria-modal="true"
  aria-live="assertive"
  aria-label="Gå nu! {departure.line} mod {departure.direction} afgår {countdown}"
>
  <!-- Radial pulse rings (purely decorative, GPU-animated) -->
  <div class="pulse-ring ring-1" aria-hidden="true"></div>
  <div class="pulse-ring ring-2" aria-hidden="true"></div>
  <div class="pulse-ring ring-3" aria-hidden="true"></div>

  <!-- Main alert card — stopPropagation keeps click-outside-to-dismiss working -->
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <div class="alert-card" on:click|stopPropagation>

    <!-- Transport icon -->
    <div class="transport-icon" aria-hidden="true">{icon}</div>

    <!-- "AFGANG OM" headline -->
    <p class="headline">AFGANG OM</p>

    <!-- Giant countdown number -->
    <div class="countdown" aria-label="Afgang om {countdown}">
      {countdown}
    </div>

    <!-- Line badge + direction -->
    <div class="meta-row">
      <span class="line-badge" style="background:{lineColor}; box-shadow: 0 0 16px {lineColor}88;">
        {departure.line}
      </span>
      <span class="direction-text">{departure.direction}</span>
    </div>

    {#if departure.stop_name}
      <p class="stop-label">Fra <strong>{departure.stop_name}</strong></p>
    {/if}

    <!-- Dismiss button — subtle, bottom-right -->
    <button class="dismiss-btn" on:click={dismiss} aria-label="Afvis alarm">
      Afvis ✕
    </button>

    <p class="hint-text">Klik udenfor for at afvise</p>
  </div>
</div>

<style>
  /* ── Full-screen overlay with radial glow from centre ── */
  .overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
    background: radial-gradient(
      ellipse 60% 60% at 50% 50%,
      rgba(255, 59, 92, 0.22) 0%,
      rgba(255, 59, 92, 0.1) 40%,
      rgba(10, 14, 26, 0.9) 100%
    );
    backdrop-filter: blur(6px);
    animation: overlay-breathe 1.6s ease-in-out infinite;
    cursor: pointer;
  }

  @keyframes overlay-breathe {
    0%, 100% {
      background: radial-gradient(
        ellipse 60% 60% at 50% 50%,
        rgba(255, 59, 92, 0.20) 0%,
        rgba(255, 59, 92, 0.08) 40%,
        rgba(10, 14, 26, 0.88) 100%
      );
    }
    50% {
      background: radial-gradient(
        ellipse 70% 70% at 50% 50%,
        rgba(255, 59, 92, 0.32) 0%,
        rgba(255, 59, 92, 0.14) 45%,
        rgba(10, 14, 26, 0.92) 100%
      );
    }
  }

  /* ── Pulsing concentric rings ── */
  .pulse-ring {
    position: absolute;
    top: 50%;
    left: 50%;
    border-radius: 50%;
    border: 1px solid rgba(255, 59, 92, 0.4);
    transform: translate(-50%, -50%) scale(0);
    animation: ring-expand 2.4s ease-out infinite;
    pointer-events: none;
  }
  .ring-1 { width: 320px; height: 320px; animation-delay: 0s; }
  .ring-2 { width: 480px; height: 480px; animation-delay: 0.6s; border-color: rgba(255, 59, 92, 0.25); }
  .ring-3 { width: 640px; height: 640px; animation-delay: 1.2s; border-color: rgba(255, 59, 92, 0.12); }

  @keyframes ring-expand {
    0%   { transform: translate(-50%, -50%) scale(0.3); opacity: 1; }
    100% { transform: translate(-50%, -50%) scale(1);   opacity: 0; }
  }

  /* ── Alert card ── */
  .alert-card {
    position: relative;
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 3rem 4rem 2rem;
    border-radius: 24px;
    background: rgba(10, 14, 26, 0.92);
    border: 1.5px solid rgba(255, 59, 92, 0.55);
    box-shadow:
      0 0 0 1px rgba(255, 59, 92, 0.15),
      0 0 60px rgba(255, 59, 92, 0.4),
      0 0 120px rgba(255, 59, 92, 0.15),
      0 24px 80px rgba(0, 0, 0, 0.8),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
    backdrop-filter: blur(24px);
    cursor: default;
    min-width: 380px;
    max-width: 520px;
    text-align: center;
    animation: card-appear 0.4s cubic-bezier(0.16, 1, 0.3, 1) both;
  }

  @keyframes card-appear {
    from { transform: scale(0.88); opacity: 0; }
    to   { transform: scale(1);    opacity: 1; }
  }

  /* ── Transport icon ── */
  .transport-icon {
    font-size: 3.5rem;
    line-height: 1;
    filter: drop-shadow(0 0 16px rgba(255, 59, 92, 0.9));
    animation: icon-float 2s ease-in-out infinite alternate;
  }

  @keyframes icon-float {
    0%   { transform: translateY(0px); }
    100% { transform: translateY(-6px); }
  }

  /* ── "AFGANG OM" ── */
  .headline {
    margin: 0;
    font-size: 1rem;
    font-weight: 900;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, 0.45);
    font-family: 'Courier New', monospace;
  }

  /* ── Countdown — massive neon number ── */
  .countdown {
    font-family: 'Courier New', 'SF Mono', monospace;
    font-size: clamp(80px, 10vw, 128px);
    font-weight: 900;
    line-height: 1;
    color: #ff3b5c;
    text-shadow:
      0 0 20px rgba(255, 59, 92, 0.9),
      0 0 40px rgba(255, 59, 92, 0.6),
      0 0 80px rgba(255, 59, 92, 0.3);
    letter-spacing: -0.02em;
    animation: countdown-pulse 0.9s ease-in-out infinite;
  }

  @keyframes countdown-pulse {
    0%, 100% {
      text-shadow:
        0 0 20px rgba(255, 59, 92, 0.9),
        0 0 40px rgba(255, 59, 92, 0.6),
        0 0 80px rgba(255, 59, 92, 0.3);
    }
    50% {
      text-shadow:
        0 0 30px rgba(255, 59, 92, 1.0),
        0 0 60px rgba(255, 59, 92, 0.8),
        0 0 100px rgba(255, 59, 92, 0.4);
    }
  }

  /* ── Line + direction row ── */
  .meta-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    justify-content: center;
  }

  .line-badge {
    display: inline-block;
    color: #fff;
    font-family: 'Courier New', monospace;
    font-size: 1.1rem;
    font-weight: 900;
    padding: 6px 18px;
    border-radius: 8px;
    letter-spacing: 0.06em;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4);
    flex-shrink: 0;
  }

  .direction-text {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: 0.02em;
    font-family: system-ui, 'Inter', sans-serif;
    max-width: 300px;
    line-height: 1.2;
  }

  /* ── Stop name ── */
  .stop-label {
    margin: 0;
    font-size: 0.82rem;
    color: rgba(255, 59, 92, 0.65);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-family: 'Courier New', monospace;
  }
  .stop-label strong {
    color: rgba(255, 59, 92, 0.85);
    font-weight: 700;
  }

  /* ── Dismiss button — subtle, bottom right ── */
  .dismiss-btn {
    position: absolute;
    bottom: 1rem;
    right: 1.2rem;
    padding: 0.4rem 1rem;
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    cursor: pointer;
    transition: all 0.2s ease;
    font-family: system-ui, sans-serif;
  }
  .dismiss-btn:hover {
    background: rgba(255, 59, 92, 0.15);
    color: rgba(255, 59, 92, 0.8);
    border-color: rgba(255, 59, 92, 0.35);
  }

  /* ── Hint text ── */
  .hint-text {
    margin: 0;
    padding-bottom: 0.5rem;
    font-size: 0.66rem;
    color: rgba(255, 255, 255, 0.15);
    letter-spacing: 0.06em;
    font-family: system-ui, sans-serif;
  }
</style>
