<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import type { Departure } from '$lib/stores/websocket';
  import { formatTime, formatCountdown, formatDelay, isGoNow } from '$lib/utils/time';
  import FlipClock from './FlipClock.svelte';
  import LineTypeBadge from './LineTypeBadge.svelte';

  export let departure: Departure;
  export let walkSeconds: number = 300;

  // Reactive derived values (depend on prop changes)
  $: planned     = formatTime(departure.planned_time);
  $: expected    = formatTime(departure.expected_time);
  $: isDelayed   = departure.delay_seconds >= 60;
  $: isCancelled = departure.cancelled;
  $: delayBadge  = formatDelay(departure.delay_seconds);

  // Live countdown + goNow — recalculated every second by the interval.
  // Also recalculated whenever the `departure` prop changes (Svelte reactive statement).
  let goNow    = false;
  let countdown = '';

  function recalc() {
    countdown = formatCountdown(departure.expected_time);
    goNow     = isGoNow(departure.expected_time, walkSeconds) && !departure.cancelled;
  }
  $: departure, walkSeconds, recalc(); // re-run when props change

  let timer: ReturnType<typeof setInterval>;

  function updateCountdown() {
    recalc();
  }

  onMount(() => {
    timer = setInterval(updateCountdown, 1000);
  });
  onDestroy(() => clearInterval(timer));

  // Direction: truncate long strings
  $: direction = departure.direction?.length > 24
    ? departure.direction.slice(0, 22) + '…'
    : (departure.direction ?? '—');
</script>

<div
  class="row"
  class:go-now={goNow}
  class:cancelled={isCancelled}
  class:delayed={isDelayed && !isCancelled}
  aria-label="{departure.line} mod {departure.direction}, {isCancelled ? 'aflyst' : countdown}"
>
  <!-- Line badge -->
  <span class="col col-line">
    <LineTypeBadge line={departure.line} type={departure.transport_type} />
  </span>

  <!-- Direction -->
  <span class="col col-direction" title={departure.direction}>
    {#if isCancelled}
      <span class="cancelled-label">AFLYST</span>
    {/if}
    {direction}
  </span>

  <!-- Planned time -->
  <span class="col col-planned">
    <span class="time-mono planned">
      <FlipClock time={planned} />
    </span>
  </span>

  <!-- Real-time / expected time (shown only if different from planned) -->
  <span class="col col-expected">
    {#if isDelayed && !isCancelled}
      <span class="time-mono expected-delayed">
        <FlipClock time={expected} />
      </span>
    {:else if isCancelled}
      <span class="time-mono cancelled-time">
        <FlipClock time={expected} />
      </span>
    {:else}
      <span class="time-mono on-time">
        <FlipClock time={planned} />
      </span>
    {/if}
  </span>

  <!-- Delay badge -->
  <span class="col col-delay">
    {#if delayBadge && !isCancelled}
      <span class="delay-badge">{delayBadge}</span>
    {/if}
  </span>

  <!-- Track / Platform -->
  <span class="col col-track">
    {#if departure.track}
      <span class="track">{departure.track}</span>
    {:else}
      <span class="track empty">—</span>
    {/if}
  </span>

  <!-- Countdown -->
  <span class="col col-countdown">
    <span
      class="countdown"
      class:go-now-text={goNow}
      class:countdown-soon={!goNow && countdown !== 'Afgået'}
    >
      {countdown}
    </span>
  </span>
</div>

<style>
  /* ── Row layout ─────────────────────────────────────────────────────────── */
  .row {
    display: grid;
    grid-template-columns:
      /* line */      3.5rem
      /* direction */ 1fr
      /* planned */   5.5rem
      /* expected */  5.5rem
      /* delay */     4.5rem
      /* track */     3rem
      /* countdown */ 5.5rem;
    column-gap: 0.6rem;
    align-items: center;
    padding: 0.55rem 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    transition:
      background 0.3s ease,
      box-shadow 0.3s ease;
    cursor: default;
    position: relative;
    overflow: hidden;
  }

  .row::before {
    /* Left accent stripe */
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 3px;
    background: transparent;
    transition: background 0.3s ease;
  }

  .row:hover {
    background: rgba(255, 255, 255, 0.04);
  }

  /* ── State variants ── */
  .row.go-now {
    background: rgba(245, 158, 11, 0.12);
    animation: pulse-amber 1.4s ease-in-out infinite;
  }
  .row.go-now::before {
    background: #f59e0b;
  }

  .row.cancelled {
    background: rgba(220, 38, 38, 0.08);
    opacity: 0.7;
  }
  .row.cancelled::before {
    background: #dc2626;
  }

  .row.delayed::before {
    background: #f59e0b;
  }

  @keyframes pulse-amber {
    0%, 100% { background: rgba(245, 158, 11, 0.12); }
    50%       { background: rgba(245, 158, 11, 0.22); }
  }

  /* ── Columns ── */
  .col {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .col-direction {
    font-size: 0.88rem;
    color: #c9d5f0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    gap: 0.4rem;
  }

  .col-planned,
  .col-expected {
    justify-content: center;
    font-size: 1rem;
  }

  .col-delay {
    justify-content: center;
  }

  .col-track {
    justify-content: center;
  }

  .col-countdown {
    justify-content: flex-end;
  }

  /* ── Time displays ── */
  .time-mono {
    font-family: 'Courier New', 'Lucida Console', monospace;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    --color-time: #00dce8;
    --color-time-glow: rgba(0, 220, 232, 0.35);
  }

  .time-mono.planned {
    --color-time: #64748b;
    --color-time-glow: transparent;
    font-size: 0.82rem;
    font-weight: 500;
  }

  .time-mono.expected-delayed {
    --color-time: #f59e0b;
    --color-time-glow: rgba(245, 158, 11, 0.4);
  }

  .time-mono.on-time {
    --color-time: #00dce8;
    --color-time-glow: rgba(0, 220, 232, 0.35);
  }

  .time-mono.cancelled-time {
    --color-time: #dc2626;
    --color-time-glow: rgba(220, 38, 38, 0.3);
    text-decoration: line-through;
  }

  /* ── Delay badge ── */
  .delay-badge {
    display: inline-block;
    background: rgba(245, 158, 11, 0.2);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    padding: 1px 5px;
    white-space: nowrap;
  }

  /* ── Track ── */
  .track {
    font-size: 0.78rem;
    font-weight: 600;
    color: #94a3b8;
    font-family: 'Courier New', monospace;
    background: rgba(255,255,255,0.06);
    border-radius: 3px;
    padding: 1px 5px;
  }
  .track.empty {
    background: transparent;
    color: #334155;
  }

  /* ── Countdown ── */
  .countdown {
    font-size: 0.85rem;
    font-weight: 700;
    font-family: 'Courier New', monospace;
    color: #94a3b8;
    text-align: right;
    white-space: nowrap;
  }

  .countdown.go-now-text {
    color: #f59e0b;
    font-size: 0.9rem;
    text-shadow: 0 0 8px rgba(245, 158, 11, 0.7);
    animation: blink-now 0.8s step-end infinite;
  }

  .countdown.countdown-soon {
    color: #00dce8;
  }

  @keyframes blink-now {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.5; }
  }

  /* ── Cancelled label ── */
  .cancelled-label {
    display: inline-block;
    color: #dc2626;
    font-size: 0.65rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    margin-right: 0.3rem;
    flex-shrink: 0;
  }
</style>
