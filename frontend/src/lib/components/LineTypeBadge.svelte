<script lang="ts">
  /** Line number or name, e.g. "5A", "M1", "IC" */
  export let line: string = '';
  /** Transport type: BUS | TRAIN | METRO | S | REG */
  export let type: string = 'BUS';

  const TYPE_COLORS: Record<string, { bg: string; text: string; label: string }> = {
    BUS:   { bg: '#2563eb', text: '#ffffff', label: 'Bus' },
    TRAIN: { bg: '#16a34a', text: '#ffffff', label: 'Tog' },
    METRO: { bg: '#7c3aed', text: '#ffffff', label: 'Metro' },
    S:     { bg: '#ea580c', text: '#ffffff', label: 'S-tog' },
    REG:   { bg: '#0891b2', text: '#ffffff', label: 'Regional' },
  };

  $: cfg = TYPE_COLORS[type?.toUpperCase()] ?? TYPE_COLORS['BUS'];
</script>

<span
  class="badge"
  style="--badge-bg:{cfg.bg};--badge-text:{cfg.text};"
  title="{cfg.label} {line}"
  aria-label="{cfg.label} linje {line}"
>
  {line}
</span>

<style>
  .badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--badge-bg);
    color: var(--badge-text);
    font-family: 'Courier New', 'Lucida Console', monospace;
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.03em;
    padding: 2px 7px;
    border-radius: 4px;
    min-width: 2.4rem;
    text-align: center;
    white-space: nowrap;
    flex-shrink: 0;
    box-shadow:
      0 0 8px color-mix(in srgb, var(--badge-bg) 60%, transparent),
      inset 0 1px 0 rgba(255,255,255,0.15);
    text-shadow: 0 1px 2px rgba(0,0,0,0.4);
    user-select: none;
  }
</style>
