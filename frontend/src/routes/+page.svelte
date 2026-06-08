<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    departures, alerts, connected, lastUpdated, goNowDepartures,
  } from '$lib/stores/websocket';
  import {
    activeStopIndex, walkTimeSeconds, dismissedGoNow, disturbancePanelOpen,
  } from '$lib/stores/config';

  import DepartureBoard    from '$lib/components/DepartureBoard.svelte';
  import GoNowAlert        from '$lib/components/GoNowAlert.svelte';
  import DisturbancePanel  from '$lib/components/DisturbancePanel.svelte';
  import ConnectionStatus  from '$lib/components/ConnectionStatus.svelte';

  // ── Live wall clock ──────────────────────────────────────────────────────────
  let clockHH = '--';
  let clockMM = '--';
  let clockSS = '--';
  let colonVisible = true;

  function updateClock() {
    const now  = new Date();
    clockHH    = now.getHours().toString().padStart(2, '0');
    clockMM    = now.getMinutes().toString().padStart(2, '0');
    clockSS    = now.getSeconds().toString().padStart(2, '0');
    colonVisible = now.getSeconds() % 2 === 0;
  }
  updateClock();

  let clockTimer: ReturnType<typeof setInterval>;
  onMount(() => { clockTimer = setInterval(updateClock, 1000); });
  onDestroy(() => clearInterval(clockTimer));

  // ── Active stop ──────────────────────────────────────────────────────────────
  $: stops      = $departures;
  $: activeStop = stops[$activeStopIndex] ?? null;

  $: if ($activeStopIndex >= stops.length && stops.length > 0) {
    activeStopIndex.set(0);
  }

  function selectStop(i: number) { activeStopIndex.set(i); }

  // ── GoNow filtering ──────────────────────────────────────────────────────────
  $: visibleGoNow = $goNowDepartures.filter(
    (d) => !$dismissedGoNow.has(d.journey_id ?? (d.line + d.planned_time))
  );
  $: currentGoNow = visibleGoNow[0] ?? null;

  // ── Walk time control ────────────────────────────────────────────────────────
  let editingWalk = false;
  let walkInput: number = $walkTimeSeconds;
  $: walkDisplay = Math.round($walkTimeSeconds / 60);

  function saveWalk() {
    walkTimeSeconds.set(Math.max(30, Math.min(3600, walkInput)));
    editingWalk = false;
  }

  // ── Last updated display ─────────────────────────────────────────────────────
  $: lastUpdatedStr = $lastUpdated
    ? $lastUpdated.toLocaleTimeString('da-DK', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      })
    : null;

  // ── Disturbance ticker text ──────────────────────────────────────────────────
  $: tickerText = $alerts.map((a) => `${a.title}`).join('   ·   ');

  function onWalkSliderChange(e: Event) {
    const val = parseInt((e.target as HTMLInputElement).value);
    walkTimeSeconds.set(val * 60);
  }
</script>

<svelte:head>
  <title>RejseplanAPI Dashboard</title>
  <link
    rel="preconnect"
    href="https://fonts.googleapis.com"
  />
  <link
    rel="preconnect"
    href="https://fonts.gstatic.com"
    crossorigin=""
  />
  <link
    href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap"
    rel="stylesheet"
  />
</svelte:head>

<div class="dashboard">

  <!-- ── Disturbance ticker bar (only shown when alerts exist) ── -->
  {#if $alerts.length > 0}
    <div class="ticker-bar" role="marquee" aria-label="Driftsforstyrrelser">
      <span class="ticker-tag" aria-hidden="true">⚠ DRIFTSTATUS</span>
      <div class="ticker-track">
        <span class="ticker-content">{tickerText}&nbsp;&nbsp;&nbsp;&nbsp;{tickerText}</span>
      </div>
    </div>
  {/if}

  <!-- ── Top bar ──────────────────────────────────────────────────────────── -->
  <header class="topbar">

    <!-- Brand -->
    <div class="brand" aria-label="RejseplanAPI Dashboard">
      <span class="brand-icon" aria-hidden="true">
        <svg width="22" height="22" viewBox="0 0 22 22" fill="none" aria-hidden="true">
          <rect x="1" y="6" width="20" height="10" rx="2.5" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <circle cx="5.5"  cy="16" r="2" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <circle cx="16.5" cy="16" r="2" stroke="currentColor" stroke-width="1.5" fill="none"/>
          <path d="M1 10h20M8 6V4M14 6V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </span>
      <span class="brand-name">
        <span class="brand-r">R</span>ejseplanAPI
      </span>
    </div>

    <!-- Stop tabs (centre) -->
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

    <!-- Right: walk time + connection + disturbance + clock -->
    <div class="topbar-right">

      <!-- Walk time control -->
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
            <button type="button" class="walk-cancel" on:click={() => (editingWalk = false)}>✕</button>
          </form>
        {:else}
          <button
            class="walk-display"
            on:click={() => { walkInput = $walkTimeSeconds; editingWalk = true; }}
          >
            <span class="walk-icon" aria-hidden="true">🚶</span>
            <span class="walk-val">{walkDisplay} min</span>
          </button>
        {/if}
      </div>

      <!-- Connection status -->
      <ConnectionStatus />

      <!-- Disturbance panel toggle -->
      <DisturbancePanel alerts={$alerts} />

      <!-- Live HH:MM:SS clock -->
      <div class="clock" aria-label="Klokken er {clockHH}:{clockMM}:{clockSS}" role="timer">
        <span class="clock-hm">{clockHH}</span>
        <span class="clock-sep" class:dim={!colonVisible} aria-hidden="true">:</span>
        <span class="clock-hm">{clockMM}</span>
        <span class="clock-sep clock-sep-small" class:dim={!colonVisible} aria-hidden="true">:</span>
        <span class="clock-ss">{clockSS}</span>
      </div>
    </div>
  </header>

  <!-- ── Main content area ──────────────────────────────────────────────── -->
  <main class="main-area">
    {#if activeStop}
      <DepartureBoard
        stopDepartures={activeStop}
        walkSeconds={$walkTimeSeconds}
      />
    {:else if !$connected}
      <div class="splash">
        <div class="splash-icon" aria-hidden="true">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <circle cx="28" cy="28" r="26" stroke="rgba(0,212,255,0.2)" stroke-width="2"/>
            <circle cx="28" cy="28" r="18" stroke="rgba(0,212,255,0.3)" stroke-width="2" stroke-dasharray="4 4"/>
            <circle cx="28" cy="28" r="5"  fill="rgba(0,212,255,0.5)"/>
          </svg>
        </div>
        <h2 class="splash-title">Opretter forbindelse…</h2>
        <p class="splash-sub">Venter på data fra RejseplanAPI backend</p>
        <span class="spinner-large" aria-hidden="true"></span>
      </div>
    {:else}
      <div class="splash">
        <div class="splash-icon" aria-hidden="true">
          <svg width="56" height="56" viewBox="0 0 56 56" fill="none">
            <circle cx="28" cy="28" r="26" stroke="rgba(0,212,255,0.15)" stroke-width="2"/>
            <path d="M18 28h20M28 18l10 10-10 10" stroke="rgba(0,212,255,0.4)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        <h2 class="splash-title">Ingen afgange fundet</h2>
        <p class="splash-sub">Konfigurer stop i backend-konfigurationen</p>
      </div>
    {/if}
  </main>

  <!-- ── Bottom bar: walk slider + last-updated ── -->
  <footer class="bottom-bar">
    <div class="bottom-left">
      {#if lastUpdatedStr}
        <span class="last-updated">↻ {lastUpdatedStr}</span>
      {/if}
    </div>

    <div class="bottom-center">
      <!-- Walk time slider -->
      <label class="walk-slider-wrap" aria-label="Gangtid til stop">
        <span class="walk-slider-icon" aria-hidden="true">🚶</span>
        <span class="walk-slider-label">Gangtid:</span>
        <input
          class="walk-slider"
          type="range"
          min="1"
          max="30"
          step="1"
          value={walkDisplay}
          on:change={onWalkSliderChange}
          aria-label="Gangtid i minutter"
        />
        <span class="walk-slider-val">{walkDisplay} min</span>
      </label>
    </div>

    <div class="bottom-right">
      <!-- Multiple go-now ticker -->
      {#if visibleGoNow.length > 1}
        <div class="go-ticker" aria-label="{visibleGoNow.length} afgange kræver opmærksomhed">
          <span class="go-ticker-icon" aria-hidden="true">⚡</span>
          <span class="go-ticker-label">GÅ NU!</span>
          {#each visibleGoNow.slice(1) as dep}
            <span class="go-ticker-item">
              <strong>{dep.line}</strong> → {dep.direction}
            </span>
          {/each}
        </div>
      {/if}
    </div>
  </footer>

</div>

<!-- GoNow overlay rendered outside dashboard for proper z-index stacking -->
{#if currentGoNow}
  <GoNowAlert departure={currentGoNow} />
{/if}

<style>
  /* ════════════════════════════════════════════════════════════
     DESIGN SYSTEM — CSS CUSTOM PROPERTIES
     Applied globally via :global(:root)
  ════════════════════════════════════════════════════════════ */
  :global(:root) {
    /* Backgrounds */
    --bg-primary:   #0a0e1a;
    --bg-card:      #111827;
    --bg-board:     #0d1117;

    /* Accents */
    --accent-cyan:  #00d4ff;
    --accent-amber: #ffb800;
    --accent-red:   #ff3b5c;
    --accent-green: #00e676;

    /* Typography */
    --text-primary: #f0f4ff;
    --text-muted:   #8892a4;

    /* Borders & glows */
    --border-subtle: rgba(255, 255, 255, 0.06);
    --glow-cyan:     0 0 20px rgba(0, 212, 255, 0.3);
    --glow-amber:    0 0 20px rgba(255, 184, 0, 0.4);

    /* Flip tile */
    --flip-bg:   #161b2e;
    --flip-text: #e8f4ff;

    /* Legacy compatibility */
    --color-bg:         var(--bg-primary);
    --color-bg-2:       #0d1220;
    --color-bg-3:       var(--bg-card);
    --color-border:     rgba(0, 212, 255, 0.12);
    --color-cyan:       var(--accent-cyan);
    --color-cyan-dim:   rgba(0, 212, 255, 0.35);
    --color-amber:      var(--accent-amber);
    --color-red:        var(--accent-red);
    --color-green:      var(--accent-green);
    --color-text:       var(--text-primary);
    --color-text-muted: var(--text-muted);
    --font-mono: 'Courier New', 'SF Mono', 'Roboto Mono', monospace;
  }

  :global(*, *::before, *::after) { box-sizing: border-box; }

  :global(body) {
    margin: 0;
    padding: 0;
    background: var(--bg-primary);
    color: var(--text-primary);
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    overflow: hidden;
  }

  /* ── Dashboard shell ── */
  .dashboard {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    position: relative;
    /* Deep space gradient base */
    background:
      radial-gradient(ellipse 55% 40% at 15%  5%,  rgba(0,212,255,0.05)  0%, transparent 60%),
      radial-gradient(ellipse 45% 35% at 85% 95%, rgba(168,85,247,0.04) 0%, transparent 55%),
      radial-gradient(ellipse 40% 30% at 80%  10%, rgba(0,230,118,0.03)  0%, transparent 50%),
      var(--bg-primary);
  }

  /* Subtle dot-grid pattern overlay */
  .dashboard::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image: radial-gradient(circle, rgba(255,255,255,0.03) 1px, transparent 1px);
    background-size: 32px 32px;
    pointer-events: none;
    z-index: 0;
  }

  /* All direct children sit above the dot-grid */
  .dashboard > * { position: relative; z-index: 1; }

  /* ══════════════════════════════════════════
     DISTURBANCE TICKER BAR
  ══════════════════════════════════════════ */
  .ticker-bar {
    display: flex;
    align-items: center;
    height: 26px;
    background: rgba(255, 184, 0, 0.1);
    border-bottom: 1px solid rgba(255, 184, 0, 0.25);
    overflow: hidden;
    flex-shrink: 0;
  }

  .ticker-tag {
    flex-shrink: 0;
    padding: 0 0.9rem;
    font-size: 0.62rem;
    font-weight: 900;
    letter-spacing: 0.12em;
    color: var(--accent-amber);
    border-right: 1px solid rgba(255, 184, 0, 0.25);
    height: 100%;
    display: flex;
    align-items: center;
    background: rgba(255, 184, 0, 0.08);
    white-space: nowrap;
    font-family: 'Courier New', monospace;
  }

  .ticker-track {
    flex: 1;
    overflow: hidden;
    position: relative;
    height: 100%;
    display: flex;
    align-items: center;
  }

  .ticker-content {
    display: inline-block;
    white-space: nowrap;
    font-size: 0.7rem;
    font-weight: 600;
    color: rgba(255, 184, 0, 0.75);
    letter-spacing: 0.05em;
    font-family: system-ui, sans-serif;
    animation: ticker-scroll 28s linear infinite;
    padding-left: 100%;
  }

  @keyframes ticker-scroll {
    from { transform: translateX(0); }
    to   { transform: translateX(-50%); }
  }

  /* ══════════════════════════════════════════
     TOP BAR
  ══════════════════════════════════════════ */
  .topbar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0 1.5rem;
    height: 56px;
    background: rgba(10, 14, 26, 0.96);
    border-bottom: 1px solid rgba(0, 212, 255, 0.1);
    backdrop-filter: blur(12px);
    flex-shrink: 0;
    z-index: 100;
    /* Top edge glow line */
    box-shadow: 0 1px 0 rgba(0, 212, 255, 0.06), 0 4px 24px rgba(0, 0, 0, 0.4);
  }

  /* Brand */
  .brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
    color: var(--accent-cyan);
    text-decoration: none;
  }

  .brand-icon {
    display: flex;
    align-items: center;
    color: var(--accent-cyan);
    filter: drop-shadow(0 0 6px rgba(0, 212, 255, 0.5));
  }

  .brand-name {
    font-size: 0.95rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: 0.01em;
    white-space: nowrap;
    text-shadow: none;
    font-family: 'Inter', system-ui, sans-serif;
  }

  /* The R gets the cyan accent treatment */
  .brand-r {
    color: var(--accent-cyan);
    text-shadow: 0 0 14px rgba(0, 212, 255, 0.7);
    font-weight: 900;
  }

  /* Stop tabs — centred flex fill */
  .stop-tabs {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    flex: 1;
    overflow-x: auto;
    scrollbar-width: none;
    min-width: 0;
    justify-content: center;
  }
  .stop-tabs::-webkit-scrollbar { display: none; }

  .stop-tab {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.3rem 0.85rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 20px;
    color: var(--text-muted);
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.2s ease;
    letter-spacing: 0.03em;
    font-family: 'Inter', system-ui, sans-serif;
  }
  .stop-tab:hover {
    background: rgba(0, 212, 255, 0.07);
    color: var(--text-primary);
    border-color: rgba(0, 212, 255, 0.2);
  }
  .stop-tab.active {
    background: rgba(0, 212, 255, 0.1);
    border-color: rgba(0, 212, 255, 0.4);
    color: var(--accent-cyan);
    text-shadow: 0 0 10px rgba(0, 212, 255, 0.4);
    box-shadow: var(--glow-cyan);
  }

  .tab-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.55;
    flex-shrink: 0;
  }
  .stop-tab.active .tab-dot {
    opacity: 1;
    box-shadow: 0 0 5px currentColor;
  }

  .stop-tab-placeholder {
    font-size: 0.74rem;
    color: rgba(255, 255, 255, 0.2);
    letter-spacing: 0.06em;
    padding: 0.3rem 0.5rem;
    font-style: italic;
  }

  /* Right cluster */
  .topbar-right {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    flex-shrink: 0;
    margin-left: auto;
  }

  /* Walk control */
  .walk-display {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.28rem 0.65rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 20px;
    color: var(--text-muted);
    font-size: 0.74rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
    font-family: 'Inter', system-ui, sans-serif;
  }
  .walk-display:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary);
  }
  .walk-icon { font-size: 0.9rem; }
  .walk-val  { font-family: var(--font-mono); font-size: 0.72rem; }

  .walk-edit {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .walk-input {
    width: 60px;
    padding: 0.25rem 0.4rem;
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(0, 212, 255, 0.4);
    border-radius: 6px;
    color: var(--accent-cyan);
    font-size: 0.78rem;
    font-family: var(--font-mono);
    outline: none;
    transition: border-color 0.2s;
  }
  .walk-input:focus { border-color: var(--accent-cyan); }
  .walk-save, .walk-cancel {
    padding: 0.25rem 0.5rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    cursor: pointer;
    border: 1px solid;
    transition: all 0.15s;
  }
  .walk-save {
    background: rgba(0, 212, 255, 0.12);
    color: var(--accent-cyan);
    border-color: rgba(0, 212, 255, 0.4);
  }
  .walk-save:hover { background: rgba(0, 212, 255, 0.22); }
  .walk-cancel {
    background: transparent;
    color: var(--text-muted);
    border-color: rgba(255, 255, 255, 0.1);
  }
  .walk-cancel:hover { color: var(--text-primary); }

  /* Live clock */
  .clock {
    display: flex;
    align-items: baseline;
    gap: 0;
    font-family: var(--font-mono);
    font-weight: 900;
    letter-spacing: 0.02em;
    line-height: 1;
    color: var(--accent-cyan);
    text-shadow: 0 0 18px rgba(0, 212, 255, 0.65);
    flex-shrink: 0;
    user-select: none;
  }

  .clock-hm {
    font-size: 1.65rem;
    letter-spacing: -0.01em;
  }

  .clock-ss {
    font-size: 0.95rem;
    color: rgba(0, 212, 255, 0.45);
    margin-top: 0.25rem;
  }

  .clock-sep {
    font-size: 1.45rem;
    color: rgba(0, 212, 255, 0.6);
    margin: 0 1px;
    transition: opacity 0.1s;
  }
  .clock-sep.dim { opacity: 0.12; }
  .clock-sep-small { font-size: 0.9rem; }

  /* ══════════════════════════════════════════
     MAIN AREA
  ══════════════════════════════════════════ */
  .main-area {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    padding: 0.75rem 1.5rem 0.5rem;
    overflow: hidden;
  }

  /* ── Splash / empty / connecting states ── */
  .splash {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.8rem;
    color: var(--text-muted);
    text-align: center;
  }

  .splash-icon {
    opacity: 0.6;
    animation: splash-float 3s ease-in-out infinite alternate;
  }
  @keyframes splash-float {
    from { transform: translateY(0); }
    to   { transform: translateY(-8px); }
  }

  .splash-title {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    color: rgba(240, 244, 255, 0.3);
    letter-spacing: 0.02em;
    font-family: 'Inter', system-ui, sans-serif;
  }
  .splash-sub {
    margin: 0;
    font-size: 0.82rem;
    color: rgba(136, 146, 164, 0.5);
    font-family: system-ui, sans-serif;
  }

  .spinner-large {
    width: 30px;
    height: 30px;
    border: 2.5px solid rgba(0, 212, 255, 0.1);
    border-top-color: rgba(0, 212, 255, 0.5);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-top: 0.5rem;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  /* ══════════════════════════════════════════
     BOTTOM BAR
  ══════════════════════════════════════════ */
  .bottom-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 40px;
    padding: 0 1.5rem;
    background: rgba(10, 14, 26, 0.85);
    border-top: 1px solid var(--border-subtle);
    flex-shrink: 0;
    gap: 1rem;
    backdrop-filter: blur(8px);
  }

  .bottom-left,
  .bottom-right {
    flex: 1;
    display: flex;
    align-items: center;
  }
  .bottom-right { justify-content: flex-end; }

  .bottom-center {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .last-updated {
    font-size: 0.62rem;
    color: rgba(255, 255, 255, 0.18);
    font-family: var(--font-mono);
    letter-spacing: 0.04em;
    white-space: nowrap;
  }

  /* Walk-time slider */
  .walk-slider-wrap {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    user-select: none;
  }

  .walk-slider-icon { font-size: 0.85rem; }

  .walk-slider-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    letter-spacing: 0.06em;
    white-space: nowrap;
    font-family: system-ui, sans-serif;
  }

  .walk-slider {
    -webkit-appearance: none;
    appearance: none;
    width: 110px;
    height: 3px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    accent-color: var(--accent-cyan);
  }
  .walk-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 13px;
    height: 13px;
    border-radius: 50%;
    background: var(--accent-cyan);
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.6);
    cursor: pointer;
    transition: transform 0.15s ease;
  }
  .walk-slider::-webkit-slider-thumb:hover {
    transform: scale(1.3);
  }
  .walk-slider::-moz-range-thumb {
    width: 13px;
    height: 13px;
    border-radius: 50%;
    background: var(--accent-cyan);
    border: none;
    box-shadow: 0 0 8px rgba(0, 212, 255, 0.6);
    cursor: pointer;
  }

  .walk-slider-val {
    font-size: 0.65rem;
    font-family: var(--font-mono);
    color: var(--accent-cyan);
    min-width: 3rem;
    text-align: left;
    white-space: nowrap;
  }

  /* Multiple go-now mini-ticker */
  .go-ticker {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 320px;
    overflow: hidden;
  }
  .go-ticker-icon { font-size: 0.8rem; }
  .go-ticker-label {
    font-size: 0.62rem;
    font-weight: 900;
    color: var(--accent-amber);
    letter-spacing: 0.12em;
    font-family: var(--font-mono);
    flex-shrink: 0;
  }
  .go-ticker-item {
    font-size: 0.7rem;
    color: rgba(255, 184, 0, 0.7);
    font-family: var(--font-mono);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .go-ticker-item strong { color: var(--accent-amber); }
</style>
