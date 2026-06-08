<script lang="ts">
  import FlipDigit from './FlipDigit.svelte';

  /**
   * Time string in "HH:MM" format (e.g. "14:32" or "--:--").
   * Each character feeds its own FlipDigit so they animate independently.
   */
  export let time: string = '--:--';

  // Normalise to exactly 5 chars: HH:MM
  $: chars = (time ?? '--:--').padStart(5, '-').slice(0, 5).split('');
</script>

<span class="flip-clock" role="timer" aria-label={time}>
  <!-- HH -->
  <span class="digit-group">
    <FlipDigit digit={chars[0]} />
    <FlipDigit digit={chars[1]} />
  </span>

  <!-- Blinking colon separator -->
  <span class="colon" aria-hidden="true">:</span>

  <!-- MM -->
  <span class="digit-group">
    <FlipDigit digit={chars[3]} />
    <FlipDigit digit={chars[4]} />
  </span>
</span>

<style>
  .flip-clock {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    font-family: 'Courier New', 'SF Mono', 'Roboto Mono', monospace;
    font-size: inherit;
    font-weight: 700;
    letter-spacing: 0;
    line-height: 1;
    color: var(--color-time, #e8f4ff);
    filter: drop-shadow(0 0 6px var(--color-time-glow, rgba(0, 212, 255, 0.4)));
  }

  .digit-group {
    display: inline-flex;
    align-items: center;
    gap: 1px;
  }

  /* Colon that blinks in sync with wall-clock seconds */
  .colon {
    font-size: 0.85em;
    font-weight: 900;
    color: var(--color-time, #e8f4ff);
    opacity: 0.9;
    margin: 0 1px;
    line-height: 1;
    animation: colon-blink 1s step-end infinite;
    /* Vertically nudge the colon to optical centre */
    position: relative;
    top: -0.06em;
  }

  @keyframes colon-blink {
    0%, 100% { opacity: 0.9; }
    50%       { opacity: 0.15; }
  }
</style>
