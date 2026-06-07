<script lang="ts">
  import type { Alert } from '$lib/stores/websocket';
  import { disturbancePanelOpen } from '$lib/stores/config';

  export let alerts: Alert[] = [];

  const SEVERITY_CONFIG = {
    CRITICAL: { color: '#dc2626', bg: 'rgba(220, 38, 38, 0.12)', label: 'Kritisk',  icon: '⛔' },
    WARNING:  { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.10)', label: 'Advarsel', icon: '⚠️' },
    INFO:     { color: '#0891b2', bg: 'rgba(8, 145, 178, 0.10)',   label: 'Info',     icon: 'ℹ️' },
  } as const;

  $: isOpen = $disturbancePanelOpen;

  function toggle() {
    disturbancePanelOpen.update((v) => !v);
  }

  function severityCfg(sev: string) {
    return SEVERITY_CONFIG[sev as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG['INFO'];
  }

  function formatLines(lines?: string[]) {
    if (!lines || lines.length === 0) return null;
    return lines.join(', ');
  }
</script>

<!-- Toggle button — always visible in the top-bar -->
<button
  class="toggle-btn"
  class:has-alerts={alerts.length > 0}
  class:panel-open={isOpen}
  on:click={toggle}
  aria-expanded={isOpen}
  aria-label="Driftstatus {alerts.length > 0 ? `(${alerts.length} aktive alarmer)` : ''}"
>
  <span class="toggle-icon" aria-hidden="true">
    {#if alerts.length > 0}⚠️{:else}✅{/if}
  </span>
  <span class="toggle-label">Driftstatus</span>
  {#if alerts.length > 0}
    <span class="badge" aria-label="{alerts.length} alarmer">{alerts.length}</span>
  {/if}
</button>

<!-- Slide-in panel -->
{#if isOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="backdrop" on:click={toggle}></div>

  <aside class="panel" aria-label="Driftsforstyrrelser">
    <div class="panel-header">
      <h2 class="panel-title">Driftsforstyrrelser</h2>
      <button class="close-btn" on:click={toggle} aria-label="Luk panel">✕</button>
    </div>

    <div class="panel-body">
      {#if alerts.length === 0}
        <div class="no-alerts">
          <span aria-hidden="true">✅</span>
          <span>Ingen aktive forstyrrelser</span>
        </div>
      {:else}
        {#each alerts as alert (alert.id)}
          {@const cfg = severityCfg(alert.severity)}
          {@const lines = formatLines(alert.affected_lines)}
          <div
            class="alert-card"
            style="border-left-color:{cfg.color};background:{cfg.bg};"
          >
            <div class="alert-top">
              <span class="sev-icon" aria-hidden="true">{cfg.icon}</span>
              <span class="sev-label" style="color:{cfg.color}">{cfg.label}</span>
              {#if lines}
                <span class="affected-lines">Linje {lines}</span>
              {/if}
            </div>
            <p class="alert-title">{alert.title}</p>
            {#if alert.description}
              <p class="alert-desc">{alert.description}</p>
            {/if}
            {#if alert.valid_from || alert.valid_to}
              <p class="alert-validity">
                {#if alert.valid_from}Fra {new Date(alert.valid_from).toLocaleString('da-DK', { dateStyle: 'short', timeStyle: 'short' })}{/if}
                {#if alert.valid_to} til {new Date(alert.valid_to).toLocaleString('da-DK', { dateStyle: 'short', timeStyle: 'short' })}{/if}
              </p>
            {/if}
          </div>
        {/each}
      {/if}
    </div>
  </aside>
{/if}

<style>
  /* ── Toggle button ── */
  .toggle-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.8rem;
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 6px;
    color: rgba(255,255,255,0.6);
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    letter-spacing: 0.04em;
    position: relative;
  }

  .toggle-btn:hover {
    background: rgba(255,255,255,0.1);
    color: rgba(255,255,255,0.9);
  }

  .toggle-btn.has-alerts {
    border-color: rgba(245, 158, 11, 0.4);
    color: #f59e0b;
  }

  .toggle-btn.panel-open {
    background: rgba(0, 220, 232, 0.1);
    border-color: rgba(0, 220, 232, 0.4);
    color: #00dce8;
  }

  .toggle-icon {
    font-size: 1rem;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: #f59e0b;
    color: #0a0e1a;
    font-size: 0.65rem;
    font-weight: 900;
    border-radius: 50%;
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    animation: badge-pop 0.3s ease-out;
  }

  @keyframes badge-pop {
    0%   { transform: scale(0); }
    70%  { transform: scale(1.2); }
    100% { transform: scale(1); }
  }

  /* ── Backdrop ── */
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 400;
    background: rgba(0,0,0,0.4);
    backdrop-filter: blur(2px);
    animation: fade-in 0.2s ease;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to   { opacity: 1; }
  }

  /* ── Panel ── */
  .panel {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 360px;
    max-width: 90vw;
    z-index: 500;
    display: flex;
    flex-direction: column;
    background: #0d1220;
    border-left: 1px solid rgba(0, 220, 232, 0.15);
    box-shadow: -4px 0 40px rgba(0,0,0,0.7);
    animation: slide-in 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes slide-in {
    from { transform: translateX(100%); }
    to   { transform: translateX(0); }
  }

  /* ── Panel header ── */
  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 1.2rem;
    border-bottom: 1px solid rgba(0, 220, 232, 0.12);
    background: rgba(0, 220, 232, 0.05);
    flex-shrink: 0;
  }

  .panel-title {
    margin: 0;
    font-size: 0.9rem;
    font-weight: 700;
    color: #00dce8;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .close-btn {
    background: none;
    border: none;
    color: rgba(255,255,255,0.4);
    font-size: 1rem;
    cursor: pointer;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    transition: color 0.2s ease, background 0.2s ease;
  }
  .close-btn:hover {
    color: #fff;
    background: rgba(255,255,255,0.08);
  }

  /* ── Panel body ── */
  .panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 220, 232, 0.2) transparent;
  }

  /* ── No alerts ── */
  .no-alerts {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    padding: 2rem;
    color: rgba(255,255,255,0.25);
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    text-align: center;
  }
  .no-alerts span:first-child {
    font-size: 2rem;
  }

  /* ── Alert card ── */
  .alert-card {
    border-left: 3px solid;
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .alert-top {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .sev-icon {
    font-size: 0.85rem;
  }

  .sev-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }

  .affected-lines {
    margin-left: auto;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.4);
    font-family: 'Courier New', monospace;
    background: rgba(255,255,255,0.06);
    padding: 1px 6px;
    border-radius: 4px;
  }

  .alert-title {
    margin: 0;
    font-size: 0.85rem;
    font-weight: 600;
    color: #e2e8f0;
    line-height: 1.35;
  }

  .alert-desc {
    margin: 0;
    font-size: 0.78rem;
    color: rgba(255,255,255,0.45);
    line-height: 1.4;
  }

  .alert-validity {
    margin: 0;
    font-size: 0.68rem;
    color: rgba(255,255,255,0.28);
    font-family: 'Courier New', monospace;
  }
</style>
