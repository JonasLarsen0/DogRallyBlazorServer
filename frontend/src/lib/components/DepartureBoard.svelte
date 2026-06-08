<script lang="ts">
  import type { StopDepartures } from '$lib/stores/websocket';
  import { formatTime } from '$lib/utils/time';
  import DepartureRow from './DepartureRow.svelte';

  export let stopDepartures: StopDepartures | null = null;
  export let walkSeconds: number = 300;

  const MAX_ROWS = 10;

  $: departures = stopDepartures?.departures?.slice(0, MAX_ROWS) ?? [];

  function getFetchedAt(s: StopDepartures | null): string | null {
    const ts = s?.fetched_at ?? s?.timestamp ?? null;
    return ts ? formatTime(ts) : null;
  }
  $: fetchedAt = getFetchedAt(stopDepartures);
  $: overflow  = (stopDepartures?.departures?.length ?? 0) - MAX_ROWS;
</script>

<section
  class="board"
  aria-label="Afgangstavle for {stopDepartures?.stop_name ?? 'stop'}"
>
  <!-- ── Board header ── -->
  <header class="board-header">
    <div class="stop-identity">
      <span class="stop-name">{stopDepartures?.stop_name ?? '—'}</span>
      <span class="stop-sub">Afgange</span>
    </div>

    <div class="header-labels" aria-hidden="true">
      <span class="lbl lbl-line">Linje</span>
      <span class="lbl lbl-dir">Retning</span>
      <span class="lbl lbl-plan">Plan.</span>
      <span class="lbl lbl-exp">Forv.</span>
      <span class="lbl lbl-delay">Forsink.</span>
      <span class="lbl lbl-track">Spor</span>
      <span class="lbl lbl-cdwn">Afgang</span>
    </div>

    {#if fetchedAt}
      <span class="updated-at" aria-label="Sidst opdateret {fetchedAt}">
        ↻ {fetchedAt}
      </span>
    {/if}
  </header>

  <!-- ── Row divider line ── -->
  <div class="header-rule" aria-hidden="true"></div>

  <!-- ── Departure rows ── -->
  <div class="rows" role="list">
    {#if departures.length === 0}
      <div class="empty-state" role="listitem">
        <span class="spinner" aria-hidden="true"></span>
        <span class="empty-text">Henter afgange…</span>
      </div>
    {:else}
      {#each departures as dep, i (dep.journey_id ?? dep.planned_time + dep.line)}
        <div
          role="listitem"
          class="row-wrapper"
          style="animation-delay: {i * 50}ms"
        >
          <DepartureRow departure={dep} {walkSeconds} />
        </div>
      {/each}
    {/if}
  </div>

  <!-- ── Bottom overflow indicator ── -->
  {#if overflow > 0}
    <div class="overflow-bar" aria-hidden="true">
      <span class="overflow-dots">• • •</span>
      <span class="overflow-text">+{overflow} afgange mere</span>
      <span class="overflow-dots">• • •</span>
    </div>
  {/if}
</section>

<style>
  /* ── Board card ── */
  .board {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    background: var(--bg-board);
    border: 1px solid var(--border-subtle);
    border-top: 1px solid rgba(0, 212, 255, 0.12);
    border-radius: 10px;
    overflow: hidden;
    backdrop-filter: blur(12px);
    box-shadow:
      0 0 0 1px rgba(0, 212, 255, 0.04),
      0 8px 48px rgba(0, 0, 0, 0.7),
      inset 0 1px 0 rgba(255, 255, 255, 0.04);
  }

  /* ── Header ── */
  .board-header {
    display: flex;
    align-items: center;
    padding: 0.65rem 1rem 0.65rem 1.1rem;
    background: rgba(0, 212, 255, 0.04);
    flex-shrink: 0;
    gap: 0.8rem;
    min-height: 52px;
  }

  .stop-identity {
    display: flex;
    flex-direction: column;
    gap: 1px;
    flex-shrink: 0;
    min-width: 120px;
  }

  .stop-name {
    font-size: 1rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: 0.02em;
    white-space: nowrap;
    line-height: 1.2;
  }

  .stop-sub {
    font-size: 0.6rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--text-muted);
  }

  /* Column header labels — match DepartureRow grid exactly */
  .header-labels {
    display: grid;
    grid-template-columns:
      /* accent skip */  3px
      /* line */         4rem
      /* direction */    1fr
      /* planned */      5rem
      /* expected */     5.5rem
      /* delay */        4.5rem
      /* track */        3.2rem
      /* countdown */    6rem;
    column-gap: 0.55rem;
    flex: 1;
    /* Align with rows (rows have 1rem right-pad, 0 left because accent-bar is col 1) */
    padding: 0 1rem 0 0;
  }

  .lbl {
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: rgba(0, 212, 255, 0.45);
    white-space: nowrap;
  }

  /* Skip the accent-bar column */
  .lbl:first-child { display: none; }
  .lbl-line  { /* naturally at col 2 after skip */ }
  .lbl-plan,
  .lbl-exp,
  .lbl-delay,
  .lbl-track { text-align: center; }
  .lbl-cdwn  { text-align: right; }

  .updated-at {
    font-size: 0.62rem;
    color: rgba(255, 255, 255, 0.2);
    font-family: 'Courier New', monospace;
    white-space: nowrap;
    flex-shrink: 0;
    letter-spacing: 0.04em;
  }

  /* ── Separator line below header ── */
  .header-rule {
    height: 1px;
    background: linear-gradient(
      to right,
      transparent 0%,
      rgba(0, 212, 255, 0.18) 10%,
      rgba(0, 212, 255, 0.18) 90%,
      transparent 100%
    );
    flex-shrink: 0;
  }

  /* ── Rows container ── */
  .rows {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 212, 255, 0.18) transparent;
  }
  .rows::-webkit-scrollbar       { width: 3px; }
  .rows::-webkit-scrollbar-track { background: transparent; }
  .rows::-webkit-scrollbar-thumb {
    background: rgba(0, 212, 255, 0.18);
    border-radius: 2px;
  }

  /* Staggered slide-in entrance for each row */
  .row-wrapper {
    animation: row-enter 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
  }
  @keyframes row-enter {
    from {
      opacity: 0;
      transform: translateX(-8px);
    }
    to {
      opacity: 1;
      transform: translateX(0);
    }
  }

  /* ── Empty state ── */
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.9rem;
    padding: 4rem 1rem;
    color: rgba(255, 255, 255, 0.18);
    font-size: 0.88rem;
    letter-spacing: 0.08em;
    font-family: system-ui, sans-serif;
  }

  .empty-text {
    color: var(--text-muted);
    opacity: 0.5;
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid rgba(0, 212, 255, 0.12);
    border-top-color: rgba(0, 212, 255, 0.55);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    flex-shrink: 0;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ── Overflow bar ── */
  .overflow-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 0.45rem 1rem;
    border-top: 1px solid var(--border-subtle);
    background: rgba(0, 0, 0, 0.2);
    flex-shrink: 0;
  }

  .overflow-text {
    font-size: 0.65rem;
    color: rgba(0, 212, 255, 0.35);
    letter-spacing: 0.1em;
    text-transform: uppercase;
    font-weight: 600;
    font-family: 'Courier New', monospace;
  }

  .overflow-dots {
    font-size: 0.5rem;
    color: rgba(0, 212, 255, 0.2);
    letter-spacing: 0.3em;
  }
</style>
