<script lang="ts">
  /** Line identifier, e.g. "5A", "M1", "IC", "RE 17" */
  export let line: string = '';
  /** Transport type: BUS | TRAIN | METRO | S | REG | IC | RE */
  export let type: string = 'BUS';

  interface BadgeCfg {
    bg:    string;
    text:  string;
    glow:  string;
    label: string;
  }

  const TYPE_COLORS: Record<string, BadgeCfg> = {
    IC:    { bg: '#b8860b', text: '#fff8e1', glow: 'rgba(255,184,0,0.45)',   label: 'InterCity' },
    TRAIN: { bg: '#166534', text: '#dcfce7', glow: 'rgba(0,230,118,0.35)',   label: 'Tog' },
    RE:    { bg: '#0e7490', text: '#cffafe', glow: 'rgba(0,212,255,0.4)',    label: 'Regional Ekspres' },
    REG:   { bg: '#0f766e', text: '#ccfbf1', glow: 'rgba(20,184,166,0.38)', label: 'Regional' },
    S:     { bg: '#c2410c', text: '#fff7ed', glow: 'rgba(249,115,22,0.45)',  label: 'S-tog' },
    METRO: { bg: '#6d28d9', text: '#ede9fe', glow: 'rgba(168,85,247,0.45)', label: 'Metro' },
    BUS:   { bg: '#1d4ed8', text: '#dbeafe', glow: 'rgba(59,130,246,0.4)',  label: 'Bus' },
  };

  const FALLBACK: BadgeCfg = {
    bg: '#1e2a3a', text: '#94a3b8', glow: 'rgba(148,163,184,0.2)', label: 'Transport',
  };

  $: cfg = TYPE_COLORS[(type ?? 'BUS').toUpperCase()] ?? FALLBACK;
</script>

<span
  class="badge"
  style="
    --badge-bg:   {cfg.bg};
    --badge-text: {cfg.text};
    --badge-glow: {cfg.glow};
  "
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
    font-family: 'Courier New', 'SF Mono', monospace;
    font-size: 0.7rem;
    font-weight: 900;
    letter-spacing: 0.04em;
    padding: 3px 8px;
    border-radius: 6px;
    min-width: 2.6rem;
    max-width: 4rem;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 0;
    user-select: none;
    /* Inner glow + shadow for depth */
    box-shadow:
      0 0 10px var(--badge-glow),
      0 0 0 1px rgba(255, 255, 255, 0.08) inset,
      0 1px 0 rgba(255, 255, 255, 0.12) inset,
      0 2px 6px rgba(0, 0, 0, 0.5);
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
    transition: box-shadow 0.25s ease;
  }

  .badge:hover {
    box-shadow:
      0 0 16px var(--badge-glow),
      0 0 0 1px rgba(255, 255, 255, 0.1) inset,
      0 1px 0 rgba(255, 255, 255, 0.14) inset,
      0 3px 10px rgba(0, 0, 0, 0.5);
  }
</style>
