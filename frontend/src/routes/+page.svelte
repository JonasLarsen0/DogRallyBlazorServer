<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { departures, alerts, connected, lastUpdated, goNowDepartures } from '$lib/stores/websocket';
  import { activeStopIndex, walkTimeSeconds, dismissedGoNow, disturbancePanelOpen } from '$lib/stores/config';

  import DepartureBoard    from '$lib/components/DepartureBoard.svelte';
  import GoNowAlert        from '$lib/components/GoNowAlert.svelte';
  import DisturbancePanel  from '$lib/components/DisturbancePanel.svelte';
  import ConnectionStatus  from '$lib/components/ConnectionStatus.svelte';

  // ── Live wall clock ──────────────────────────────────────────────────────────
  let clockHH = '--';
  let clockMM = '--';
  let clockSS = '--';

  function updateClock() {
    const now = new Date();
    clockHH = now.getHours().toString().padStart(2, '0');
    clockMM = now.getMinutes().toString().padStart(2, '0');
    clockSS = now.getSeconds().toString().padStart(2, '0');
  }
  updateClock();
  let clockTimer: ReturnType<typeof setInterval>;
  onMount(() => {
    clockTimer = setInterval(updateClock, 1000);
  });
  onDestroy(() => clearInterval(clockTimer));

  // ── Active stop ──────────────────────────────────────────────────────────────
  $: stops = $departures;
  $: activeStop = stops[$activeStopIndex] ?? null;

  // Clamp index if stops shrink
  $: if ($activeStopIndex >= stops.length && stops.length > 0) {
    activeStopIndex.set(0);
  }

  function selectStop(i: number) {
    activeStopIndex.set(i);
  }

  // ── GoNow filtering ──────────────────────────────────────────────────────────
  $: visibleGoNow = $goNowDepartures.filter(
    (d) => !$dismissedGoNow.has(d.journey_id ?? (d.line + d.planned_time))
  );
  $: currentGoNow = visibleGoNow[0] ?? null;

  // ── Walk time settings ───────────────────────────────────────────────────────
  let editingWalk = false;
  let walkInput: number = $walkTimeSeconds;
  $: walkDisplay = Math.round($walkTimeSeconds / 60);

  function saveWalk() {
    walkTimeSeconds.set(Math.max(30, Math.min(3600, walkInput)));
    editingWalk = false;
  }

  // ── Last updated display ─────────────────────────────────────────────────────
  $: lastUpdatedStr = $lastUpdated
    ? $lastUpdated.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : null;
</script>

<svelte:head>
  <title>RejseplanAPI Dashboard</title>
</svelte:head>

<div class="dashboard">

  <!-- ── Top bar ──────────────────────────────────────────────────────────── -->
  <header class="topbar">
    <!-- Brand -->
    <div class="brand">
      <span class="brand-icon" aria-hidden="true">🚊</span>
      <span class="brand-name">RejseplanAPI</span>
      <span class="brand-sub">Dashboard</span>
    </div>

    <!-- Stop tabs -->
    <nav class="stop-tabs" aria-label="Stop-faner">
      {#each stops as stop, i}
        <button
          class="stop-tab"
          class:active={i === $activeStopIndex}
          on:click={() => selectStop(i)}
          aria-current={i === $activeStopIndex ? 'page' : undefined}
          title={stop.stop_name}
        >
          <span class="tab-dot" aria-hidden="true"></span>
          {stop.stop_name}
        </button>
      {/each}
      {#if stops.length === 0}
        <span class="stop-tab-placeholder">Ingen stop konfigureret</span>
      {/if}
    </nav>

    <!-- Right section: clock + status + walk + disturbance -->
    <div class="topbar-right">
      <!-- Walk time -->
      <div class="walk-control" title="Gang-tid til stoppested">
        {#if editingWalk}
          <form class="walk-edit" on:submit|preventDefault={saveWalk}>
            <input
              type="number"
              bind:value={walkInput}
              min="30"
              max="3600"
              class="walk-input"
              aria-label="Gang-tid i sekunder"
              autofocus
            />
            <button type="submit" class="walk-save">OK</button>
            <button type="button" class="walk-cancel" on:click={() => editingWalk = false}>✕</button>
          </form>
        {:else}
          <button class="walk-display" on:click={() => { walkInput = $walkTimeSeconds; editingWalk = true; }}>
            <span class="walk-icon" aria-hidden="true">🚶</span>
            <span class="walk-val">{walkDisplay} min</span>
          </button>
        {/if}
      </div>

      <!-- Connection status -->
      <ConnectionStatus />

      <!-- Disturbance toggle (contains its own panel) -->
      <DisturbancePanel alerts={$alerts} />

      <!-- Live clock -->
      <div class="clock" aria-label="Klokken er {clockHH}:{clockMM}:{clockSS}" role="timer">
        <span class="clock-hh">{clockHH}</span>
        <span class="clock-sep" aria-hidden="true">:</span>
        <span class="clock-mm">{clockMM}</span>
        <span class="clock-sep clock-sep-sec" aria-hidden="true">:</span>
        <span class="clock-ss">{clockSS}</span>
      </div>
    </div>
  </header>

  <!-- ── Subtitle bar (stop name + last updated) ────────────────────────── -->
  {#if activeStop}
    <div class="subtitle-bar">
      <span class="subtitle-stop" aria-live="polite">{activeStop.stop_name}</span>
      {#if lastUpdatedStr}
        <span class="subtitle-updated">Sidst opdateret {lastUpdatedStr}</span>
      {/if}
    </div>
  {/if}

  <!-- ── Main area ─────────────────────────────────────────────────────────── -->
  <main class="main-area">
    {#if activeStop}
      <DepartureBoard
        stopDepartures={activeStop}
        walkSeconds={$walkTimeSeconds}
      />
    {:else if !$connected}
      <div class="no-connection">
        <div class="no-connection-icon" aria-hidden="true">📡</div>
        <h2>Opretter forbindelse…</h2>
        <p>Venter på data fra RejseplanAPI backend</p>
        <span class="spinner-large" aria-hidden="true"></span>
      </div>
    {:else}
      <div class="no-connection">
        <div class="no-connection-icon" aria-hidden="true">🔍</div>
        <h2>Ingen afgange fundet</h2>
        <p>Konfigurer stop i backend-konfigurationen</p>
      </div>
    {/if}
  </main>

  <!-- ── Alert ticker (multiple go-now) ──────────────────────────────────── -->
  {#if visibleGoNow.length > 1}
    <div class="go-now-ticker" aria-label="{visibleGoNow.length} afgange kræver din opmærksomhed">
      <span class="ticker-label" aria-hidden="true">⚠ Gå nu!</span>
      {#each visibleGoNow.slice(1) as dep}
        <span class="ticker-item">
          <strong>{dep.line}</strong> → {dep.direction}
        </span>
      {/each}
    </div>
  {/if}
</div>

<!-- ── GoNow overlay (rendered outside .dashboard for z-index) ─────────── -->
{#if currentGoNow}
  <GoNowAlert departure={currentGoNow} />
{/if}

<style>
  /* ── CSS custom properties (global theme) ── */
  :global(:root) {
    --color-bg:         #0a0e1a;
    --color-bg-2:       #0d1220;
    --color-bg-3:       #111827;
    --color-border:     rgba(0, 220, 232, 0.12);
    --color-cyan:       #00dce8;
    --color-cyan-dim:   rgba(0, 220, 232, 0.35);
    --color-amber:      #f59e0b;
    --color-red:        #dc2626;
    --color-green:      #22c55e;
    --color-text:       #e2e8f0;
    --color-text-muted: rgba(255,255,255,0.4);
    --font-mono: 'Courier New', 'Lucida Console', 'Roboto Mono', monospace;
  }

  :global(*, *::before, *::after) {
    box-sizing: border-box;
  }

  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--color-bg);
    color: var(--color-text);
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
    overflow: hidden;
  }

  /* ── Dashboard shell ── */
  .dashboard {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    background:
      radial-gradient(ellipse at 20% 0%, rgba(0, 220, 232, 0.04) 0%, transparent 60%),
      radial-gradient(ellipse at 80% 100%, rgba(124, 58, 237, 0.04) 0%, transparent 60%),
      var(--color-bg);
    overflow: hidden;
  }

  /* ── Top bar ── */
  .topbar {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.6rem 1.2rem;
    background: rgba(13, 18, 32, 0.95);
    border-bottom: 1px solid var(--color-border);
    backdrop-filter: blur(10px);
    flex-shrink: 0;
    z-index: 100;
    min-height: 54px;
  }

  /* Brand */
  .brand {
    display: flex;
    align-items: baseline;
    gap: 0.4rem;
    flex-shrink: 0;
    margin-right: 0.4rem;
  }
  .brand-icon {
    font-size: 1.2rem;
  }
  .brand-name {
    font-size: 1rem;
    font-weight: 800;
    color: var(--color-cyan);
    letter-spacing: 0.02em;
    text-shadow: 0 0 12px rgba(0, 220, 232, 0.5);
    white-space: nowrap;
  }
  .brand-sub {
    font-size: 0.65rem;
    color: var(--color-text-muted);
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }

  /* Stop tabs */
  .stop-tabs {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
    min-width: 0;
  }
  .stop-tabs::-webkit-scrollbar { display: none; }

  .stop-tab {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.75rem;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 5px;
    color: rgba(255,255,255,0.45);
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s ease;
    letter-spacing: 0.03em;
  }
  .stop-tab:hover {
    background: rgba(0, 220, 232, 0.08);
    color: rgba(255,255,255,0.75);
    border-color: rgba(0, 220, 232, 0.25);
  }
  .stop-tab.active {
    background: rgba(0, 220, 232, 0.12);
    border-color: rgba(0, 220, 232, 0.4);
    color: var(--color-cyan);
    text-shadow: 0 0 8px rgba(0, 220, 232, 0.4);
  }

  .tab-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.6;
    flex-shrink: 0;
  }
  .stop-tab.active .tab-dot {
    opacity: 1;
    box-shadow: 0 0 4px currentColor;
  }

  .stop-tab-placeholder {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.2);
    letter-spacing: 0.06em;
    padding: 0.3rem 0.5rem;
  }

  /* Right side */
  .topbar-right {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-shrink: 0;
    margin-left: auto;
  }

  /* Walk control */
  .walk-display {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.3rem 0.65rem;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 5px;
    color: rgba(255,255,255,0.45);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .walk-display:hover {
    background: rgba(255,255,255,0.09);
    color: rgba(255,255,255,0.75);
  }
  .walk-icon { font-size: 0.85rem; }
  .walk-val  { font-family: var(--font-mono); }

  .walk-edit {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .walk-input {
    width: 60px;
    padding: 0.25rem 0.4rem;
    background: rgba(0,0,0,0.4);
    border: 1px solid rgba(0, 220, 232, 0.4);
    border-radius: 4px;
    color: var(--color-cyan);
    font-size: 0.78rem;
    font-family: var(--font-mono);
    outline: none;
  }
  .walk-save, .walk-cancel {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    border: 1px solid;
    transition: all 0.15s;
  }
  .walk-save {
    background: rgba(0, 220, 232, 0.15);
    color: var(--color-cyan);
    border-color: rgba(0, 220, 232, 0.4);
  }
  .walk-save:hover {
    background: rgba(0, 220, 232, 0.25);
  }
  .walk-cancel {
    background: rgba(255,255,255,0.05);
    color: rgba(255,255,255,0.4);
    border-color: rgba(255,255,255,0.1);
  }
  .walk-cancel:hover {
    color: rgba(255,255,255,0.8);
  }

  /* ── Live clock ── */
  .clock {
    display: flex;
    align-items: baseline;
    font-family: var(--font-mono);
    font-weight: 900;
    letter-spacing: 0.04em;
    line-height: 1;
    color: var(--color-cyan);
    text-shadow: 0 0 16px rgba(0, 220, 232, 0.6);
    flex-shrink: 0;
  }
  .clock-hh, .clock-mm {
    font-size: 1.6rem;
  }
  .clock-ss {
    font-size: 0.95rem;
    color: rgba(0, 220, 232, 0.5);
    margin-top: 0.2rem;
  }
  .clock-sep {
    font-size: 1.4rem;
    color: rgba(0, 220, 232, 0.5);
    margin: 0 1px;
    animation: blink-sep 1s step-end infinite;
  }
  .clock-sep-sec {
    font-size: 0.85rem;
  }
  @keyframes blink-sep {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.15; }
  }

  /* ── Subtitle bar ── */
  .subtitle-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.3rem 1.2rem;
    background: rgba(0, 220, 232, 0.03);
    border-bottom: 1px solid rgba(0, 220, 232, 0.07);
    flex-shrink: 0;
  }
  .subtitle-stop {
    font-size: 0.88rem;
    font-weight: 700;
    color: rgba(255,255,255,0.55);
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }
  .subtitle-updated {
    font-size: 0.68rem;
    color: rgba(255,255,255,0.2);
    font-family: var(--font-mono);
  }

  /* ── Main area ── */
  .main-area {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 0.75rem 1.2rem 0.75rem;
    overflow: hidden;
  }

  /* ── No-connection / empty states ── */
  .no-connection {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    color: rgba(255,255,255,0.25);
    text-align: center;
  }
  .no-connection-icon {
    font-size: 3.5rem;
    filter: grayscale(0.5);
  }
  .no-connection h2 {
    margin: 0;
    font-size: 1.2rem;
    font-weight: 700;
    color: rgba(255,255,255,0.35);
  }
  .no-connection p {
    margin: 0;
    font-size: 0.82rem;
    color: rgba(255,255,255,0.2);
  }
  .spinner-large {
    width: 32px;
    height: 32px;
    border: 3px solid rgba(0, 220, 232, 0.1);
    border-top-color: rgba(0, 220, 232, 0.5);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }
  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* ── Go-now ticker (when multiple go-now departures exist) ── */
  .go-now-ticker {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.35rem 1.2rem;
    background: rgba(245, 158, 11, 0.12);
    border-top: 1px solid rgba(245, 158, 11, 0.25);
    flex-shrink: 0;
    overflow: hidden;
  }
  .ticker-label {
    font-size: 0.72rem;
    font-weight: 800;
    color: #f59e0b;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    flex-shrink: 0;
  }
  .ticker-item {
    font-size: 0.78rem;
    color: rgba(245, 158, 11, 0.75);
    white-space: nowrap;
    font-family: var(--font-mono);
  }
  .ticker-item strong {
    color: #f59e0b;
  }
</style>
