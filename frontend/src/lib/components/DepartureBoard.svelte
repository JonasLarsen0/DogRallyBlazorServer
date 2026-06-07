<script lang="ts">
  import type { StopDepartures } from '$lib/stores/websocket';
  import { formatTime } from '$lib/utils/time';
  import DepartureRow from './DepartureRow.svelte';

  export let stopDepartures: StopDepartures | null = null;
  export let walkSeconds: number = 300;

  const MAX_ROWS = 12;

  $: departures = stopDepartures?.departures?.slice(0, MAX_ROWS) ?? [];
  $: fetchedAt  = stopDepartures?.fetched_at
    ? formatTime(stopDepartures.fetched_at)
    : null;
</script>

<section class="board" aria-label="Afgangstavle for {stopDepartures?.stop_name ?? 'stop'}">

  <!-- Board header -->
  <header class="board-header">
    <div class="header-labels">
      <span class="col-label lbl-line">Linje</span>
      <span class="col-label lbl-dir">Retning</span>
      <span class="col-label lbl-plan">Plan.</span>
      <span class="col-label lbl-exp">Forv.</span>
      <span class="col-label lbl-delay">Forsink.</span>
      <span class="col-label lbl-track">Spor</span>
      <span class="col-label lbl-cdwn">Afgang</span>
    </div>
    {#if fetchedAt}
      <span class="updated-at" aria-label="Sidst opdateret {fetchedAt}">
        Opdateret {fetchedAt}
      </span>
    {/if}
  </header>

  <!-- Departure rows -->
  <div class="rows" role="list">
    {#if departures.length === 0}
      <div class="empty-state" role="listitem">
        <span class="spinner" aria-hidden="true"></span>
        <span>Ingen afgange</span>
      </div>
    {:else}
      {#each departures as dep (dep.journey_id ?? dep.planned_time + dep.line)}
        <div role="listitem">
          <DepartureRow departure={dep} {walkSeconds} />
        </div>
      {/each}
    {/if}
  </div>

  <!-- Gradient fade at bottom when there are more than MAX_ROWS -->
  {#if (stopDepartures?.departures?.length ?? 0) > MAX_ROWS}
    <div class="more-fade" aria-hidden="true">
      +{(stopDepartures?.departures?.length ?? 0) - MAX_ROWS} afgange mere
    </div>
  {/if}
</section>

<style>
  /* ── Board container ── */
  .board {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    background: rgba(10, 14, 26, 0.6);
    border: 1px solid rgba(0, 220, 232, 0.1);
    border-radius: 8px;
    overflow: hidden;
    backdrop-filter: blur(12px);
    box-shadow:
      0 0 0 1px rgba(0, 220, 232, 0.05),
      0 4px 32px rgba(0, 0, 0, 0.6),
      inset 0 1px 0 rgba(255,255,255,0.04);
  }

  /* ── Header bar ── */
  .board-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 1rem;
    background: rgba(0, 220, 232, 0.06);
    border-bottom: 1px solid rgba(0, 220, 232, 0.12);
    flex-shrink: 0;
  }

  .header-labels {
    display: grid;
    grid-template-columns:
      3.5rem 1fr 5.5rem 5.5rem 4.5rem 3rem 5.5rem;
    column-gap: 0.6rem;
    flex: 1;
  }

  .col-label {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: rgba(0, 220, 232, 0.55);
    white-space: nowrap;
  }

  .lbl-plan,
  .lbl-exp   { text-align: center; }
  .lbl-delay { text-align: center; }
  .lbl-track { text-align: center; }
  .lbl-cdwn  { text-align: right;  }

  .updated-at {
    font-size: 0.65rem;
    color: rgba(255,255,255,0.25);
    margin-left: 1rem;
    white-space: nowrap;
    flex-shrink: 0;
  }

  /* ── Rows ── */
  .rows {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    /* Custom scrollbar */
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 220, 232, 0.2) transparent;
  }
  .rows::-webkit-scrollbar {
    width: 4px;
  }
  .rows::-webkit-scrollbar-track {
    background: transparent;
  }
  .rows::-webkit-scrollbar-thumb {
    background: rgba(0, 220, 232, 0.2);
    border-radius: 2px;
  }

  /* ── Empty state ── */
  .empty-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.8rem;
    padding: 3rem 1rem;
    color: rgba(255,255,255,0.2);
    font-size: 0.9rem;
    letter-spacing: 0.05em;
  }

  .spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(0, 220, 232, 0.15);
    border-top-color: rgba(0, 220, 232, 0.6);
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── More fade ── */
  .more-fade {
    padding: 0.4rem 1rem;
    font-size: 0.7rem;
    color: rgba(0, 220, 232, 0.4);
    text-align: center;
    background: linear-gradient(
      to bottom,
      transparent,
      rgba(10, 14, 26, 0.8)
    );
    border-top: 1px solid rgba(255,255,255,0.04);
    letter-spacing: 0.06em;
  }
</style>
