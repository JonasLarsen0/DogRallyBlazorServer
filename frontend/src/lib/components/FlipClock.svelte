<script lang="ts">
  import FlipDigit from './FlipDigit.svelte';

  /**
   * Time string in "HH:MM" format (e.g. "14:32" or "--:--").
   * Each character is fed into its own FlipDigit so they animate independently.
   */
  export let time: string = '--:--';

  // Normalise to exactly 5 chars: "HH:MM"
  $: chars = (time ?? '--:--').padStart(5, '-').slice(0, 5).split('');
</script>

<span class="flip-clock" role="timer" aria-label={time}>
  {#each chars as char, i (i)}
    <FlipDigit digit={char} />
  {/each}
</span>

<style>
  .flip-clock {
    display: inline-flex;
    align-items: center;
    /* Monospace so every digit has the same width */
    font-family: 'Courier New', 'Lucida Console', 'Roboto Mono', monospace;
    font-size: inherit;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--color-time, #e8f0fe);
    /* Add a subtle glow that matches the on-time/delayed accent */
    filter: drop-shadow(0 0 4px var(--color-time-glow, rgba(0, 220, 255, 0.4)));
    line-height: 1;
  }
</style>
