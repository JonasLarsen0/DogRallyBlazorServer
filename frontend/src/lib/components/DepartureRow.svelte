<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Departure } from '$lib/stores/websocket';
  import { formatTime, formatCountdown, formatDelay, secondsUntil, parseDate, isGoNow } from '$lib/utils/time';
  import FlipClock from './FlipClock.svelte';
  import LineTypeBadge from './LineTypeBadge.svelte';

  export let departure: Departure;
  export let walkSeconds: number = 300;

  $: planned     = formatTime(departure.planned_time);
  $: expected    = formatTime(departure.expected_time);
  $: isDelayed   = departure.delay_seconds >= 60;
  $: isCancelled = departure.cancelled;
  $: delayBadge  = formatDelay(departure.delay_seconds);

  let goNow    = false;
  let countdown = '';
  let secsLeft  = Infinity;

  function recalc() {
    countdown = formatCountdown(departure.expected_time);
    goNow     = isGoNow(departure.expected_time, walkSeconds) && !departure.cancelled;
    const d   = parseDate(departure.expected_time as string);
    secsLeft  = d ? secondsUntil(d) : Infinity;
  }
  $: departure, walkSeconds, recalc();

  let timer: ReturnType<typeof setInterval>;
  onMount(() => { timer = setInterval(recalc, 1000); });
  onDestroy(() => clearInterval(timer));

  // Truncate long direction strings
  $: direction = departure.direction?.length > 26
    ? departure.direction.slice(0, 24) + '…'
    : (departure.direction ?? '—');

  // Countdown colour class
  $: countdownCls =
    isCancelled                                  ? 'cdwn-cancelled' :
    countdown === 'Afgået'                        ? 'cdwn-gone'     :
    goNow || countdown === 'Går nu!'              ? 'cdwn-gonow'    :
    secsLeft <= 300                               ? 'cdwn-soon'     :
    secsLeft <= 600                               ? 'cdwn-medium'   :
    'cdwn-normal';

  // Left accent bar colour by transport type
  const TYPE_ACCENT: Record<string, string> = {
    IC:    'var(--accent-amber)',
    RE:    'var(--accent-cyan)',
    REG:   '#14b8a6',
    S:     '#f97316',
    BUS:   '#3b82f6',
    METRO: '#a855f7',
    TRAIN: 'var(--accent-green)',
  };
  $: accentColor = TYPE_ACCENT[(departure.transport_type ?? 'BUS').toUpperCase()] ?? 'var(--text-muted)';
</script>

<div
  class="row"
  class:go-now={goNow}
  class:cancelled={isCancelled}
  class:delayed={isDelayed && !isCancelled}
  style="--row-accent: {accentColor};"
  aria-label="{departure.line} mod {departure.direction}, {isCancelled ? 'aflyst' : countdown}"
>
  <!-- Left accent bar (transport-type colour) -->
  <span class="accent-bar" aria-hidden="true"></span>

  <!-- Line badge -->
  <span class="col col-line">
    <LineTypeBadge line={departure.line} type={departure.transport_type} />
  </span>

  <!-- Direction -->
  <span class="col col-direction" title={departure.direction}>
    {#if isCancelled}
      <span class="cancelled-label">AFLYST</span>
    {/if}
    <span class:strikethrough={isCancelled}>{direction}</span>
  </span>

  <!-- Planned time — muted when realtime differs -->
  <span class="col col-planned">
    <span class="time-mono {isDelayed ? 'planned-delayed' : 'planned-ontime'}">
      <FlipClock time={planned} />
    </span>
  </span>

  <!-- Realtime expected time with coloured glow -->
  <span class="col col-expected">
    {#if isCancelled}
      <span class="time-mono time-cancelled">
        <FlipClock time={expected} />
      </span>
    {:else if isDelayed}
      <span class="time-mono time-delayed">
        <FlipClock time={expected} />
      </span>
    {:else}
      <span class="time-mono time-ontime">
        <FlipClock time={planned} />
      </span>
    {/if}
  </span>

  <!-- Delay badge -->
  <span class="col col-delay">
    {#if delayBadge && !isCancelled}
      <span class="delay-badge" class:severe={departure.delay_seconds >= 600}>{delayBadge}</span>
    {/if}
  </span>

  <!-- Track / Platform -->
  <span class="col col-track">
    {#if departure.track}
      <span class="track-pill">{departure.track}</span>
    {:else}
      <span class="track-empty">—</span>
    {/if}
  </span>

  <!-- Countdown — right-aligned, colour-coded urgency -->
  <span class="col col-countdown">
    <span class="countdown {countdownCls}">
      {#if isCancelled}
        <span>AFLYST</span>
      {:else}
        {countdown}
      {/if}
    </span>
  </span>
</div>

<style>
  /* ── Row grid ── */
  .row {
    display: grid;
    grid-template-columns:
      /* accent */    3px
      /* line */      4rem
      /* direction */ 1fr
      /* planned */   5rem
      /* expected */  5.5rem
      /* delay */     4.5rem
      /* track */     3.2rem
      /* countdown */ 6rem;
    column-gap: 0.55rem;
    align-items: center;
    padding: 0.6rem 1rem 0.6rem 0;
    border-bottom: 1px solid var(--border-subtle);
    transition:
      background 0.25s ease,
      box-shadow 0.25s ease;
    cursor: default;
    position: relative;
    overflow: hidden;
  }

  /* Hover: subtle lift + left-border cyan glow */
  .row:hover {
    background: rgba(0, 212, 255, 0.03);
    box-shadow: inset 3px 0 0 rgba(0, 212, 255, 0.35);
  }

  /* ── Left accent bar ── */
  .accent-bar {
    display: block;
    width: 3px;
    height: 100%;
    background: var(--row-accent, var(--text-muted));
    border-radius: 0 1px 1px 0;
    align-self: stretch;
    min-height: 100%;
    box-shadow: 1px 0 8px color-mix(in srgb, var(--row-accent, #8892a4) 60%, transparent);
    transition: background 0.3s ease;
  }

  /* ── State: go-now ── */
  .row.go-now {
    background: rgba(255, 184, 0, 0.07);
    animation: row-pulse 1.4s ease-in-out infinite;
  }
  .row.go-now .accent-bar {
    background: var(--accent-amber);
    box-shadow: 1px 0 12px rgba(255, 184, 0, 0.6);
  }
  @keyframes row-pulse {
    0%, 100% { background: rgba(255, 184, 0, 0.07); }
    50%       { background: rgba(255, 184, 0, 0.14); }
  }

  /* ── State: cancelled ── */
  .row.cancelled {
    opacity: 0.55;
    background: rgba(255, 59, 92, 0.05);
  }
  .row.cancelled .accent-bar {
    background: var(--accent-red);
    box-shadow: 1px 0 10px rgba(255, 59, 92, 0.5);
  }

  /* ── State: delayed ── */
  .row.delayed .accent-bar {
    background: var(--accent-amber);
    box-shadow: 1px 0 10px rgba(255, 184, 0, 0.4);
  }

  /* ── Columns ── */
  .col {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .col-direction {
    font-size: 0.9rem;
    font-weight: 500;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    gap: 0.4rem;
    font-family: system-ui, 'Inter', -apple-system, sans-serif;
  }

  .col-planned  { justify-content: center; font-size: 0.78rem; }
  .col-expected { justify-content: center; font-size: 1rem; }
  .col-delay    { justify-content: center; }
  .col-track    { justify-content: center; }
  .col-countdown { justify-content: flex-end; padding-right: 0.25rem; }

  /* ── Time displays ── */
  .time-mono {
    font-family: 'Courier New', 'SF Mono', monospace;
    font-weight: 700;
    letter-spacing: 0.02em;
    line-height: 1;
  }

  .planned-ontime {
    font-size: 0.78rem;
    --color-time: var(--text-muted);
    --color-time-glow: transparent;
  }
  .planned-delayed {
    font-size: 0.78rem;
    --color-time: rgba(136, 146, 164, 0.5);
    --color-time-glow: transparent;
    text-decoration: line-through;
    opacity: 0.65;
  }

  .time-ontime {
    font-size: 1rem;
    --color-time: var(--accent-cyan);
    --color-time-glow: rgba(0, 212, 255, 0.35);
  }
  .time-delayed {
    font-size: 1rem;
    --color-time: var(--accent-amber);
    --color-time-glow: rgba(255, 184, 0, 0.4);
  }
  .time-cancelled {
    font-size: 1rem;
    --color-time: var(--accent-red);
    --color-time-glow: rgba(255, 59, 92, 0.3);
    text-decoration: line-through;
  }

  /* ── Delay badge ── */
  .delay-badge {
    display: inline-block;
    background: rgba(255, 184, 0, 0.15);
    color: var(--accent-amber);
    border: 1px solid rgba(255, 184, 0, 0.35);
    border-radius: 20px;
    font-size: 0.66rem;
    font-weight: 800;
    font-family: 'Courier New', monospace;
    padding: 2px 7px;
    white-space: nowrap;
    letter-spacing: 0.04em;
    box-shadow: 0 0 6px rgba(255, 184, 0, 0.2);
  }
  .delay-badge.severe {
    background: rgba(255, 59, 92, 0.15);
    color: var(--accent-red);
    border-color: rgba(255, 59, 92, 0.35);
    box-shadow: 0 0 6px rgba(255, 59, 92, 0.2);
  }

  /* ── Track pill ── */
  .track-pill {
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 2px 8px;
    letter-spacing: 0.04em;
    white-space: nowrap;
  }
  .track-empty {
    color: rgba(136, 146, 164, 0.25);
    font-size: 0.75rem;
  }

  /* ── Countdown ── */
  .countdown {
    font-size: 0.88rem;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    text-align: right;
    white-space: nowrap;
    transition: color 0.4s ease, text-shadow 0.4s ease;
  }

  .cdwn-normal   { color: var(--text-muted); }
  .cdwn-medium   { color: var(--accent-amber); }
  .cdwn-soon     {
    color: var(--accent-amber);
    text-shadow: 0 0 10px rgba(255, 184, 0, 0.7);
    animation: cdwn-amber-pulse 1s ease-in-out infinite;
  }
  .cdwn-gonow {
    font-size: 0.9rem;
    color: var(--accent-amber);
    text-shadow:
      0 0 12px rgba(255, 184, 0, 0.9),
      0 0 24px rgba(255, 184, 0, 0.5);
    animation: cdwn-gonow-bounce 0.7s ease-in-out infinite alternate;
  }
  .cdwn-gone {
    color: rgba(136, 146, 164, 0.3);
    text-decoration: line-through;
    font-size: 0.78rem;
  }
  .cdwn-cancelled {
    color: var(--accent-red);
    font-size: 0.7rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    text-shadow: 0 0 8px rgba(255, 59, 92, 0.5);
  }

  @keyframes cdwn-amber-pulse {
    0%, 100% { text-shadow: 0 0 6px rgba(255, 184, 0, 0.5); }
    50%       { text-shadow: 0 0 14px rgba(255, 184, 0, 0.9); }
  }
  @keyframes cdwn-gonow-bounce {
    0%   { transform: scale(1);    text-shadow: 0 0 12px rgba(255, 184, 0, 0.9); }
    100% { transform: scale(1.08); text-shadow: 0 0 22px rgba(255, 184, 0, 1.0); }
  }

  /* ── Misc ── */
  .cancelled-label {
    display: inline-block;
    color: var(--accent-red);
    font-size: 0.6rem;
    font-weight: 900;
    letter-spacing: 0.1em;
    margin-right: 0.35rem;
    flex-shrink: 0;
    font-family: 'Courier New', monospace;
  }

  .strikethrough {
    text-decoration: line-through;
    opacity: 0.5;
  }
</style>
