<script lang="ts">
  import { onMount, afterUpdate } from 'svelte';

  /** The character to display: 0-9 or ':' */
  export let digit: string = '0';

  let prevDigit = digit;
  let currentDigit = digit;
  let flipping = false;
  let flipStage: 'top-fold' | 'bottom-reveal' | 'idle' = 'idle';

  // Staged flip: first the top half folds down, then bottom half of new digit reveals.
  let pendingDigit: string | null = null;

  function triggerFlip(next: string) {
    if (flipping) {
      // Queue it – will be picked up after current flip
      pendingDigit = next;
      return;
    }
    if (next === currentDigit) return;

    prevDigit = currentDigit;
    flipping = true;
    flipStage = 'top-fold';

    // After top half has folded (180ms) switch the digit and reveal bottom half
    setTimeout(() => {
      currentDigit = next;
      flipStage = 'bottom-reveal';

      setTimeout(() => {
        flipping = false;
        flipStage = 'idle';

        if (pendingDigit !== null && pendingDigit !== currentDigit) {
          const p = pendingDigit;
          pendingDigit = null;
          triggerFlip(p);
        }
      }, 180);
    }, 180);
  }

  $: if (digit !== currentDigit) {
    triggerFlip(digit);
  }
</script>

<!--
  Layout:
  ┌──────────┐  ← static top half (shows currentDigit top)
  ├──────────┤  ← centre gap (the physical crease)
  └──────────┘  ← static bottom half (shows currentDigit bottom)

  Overlays during flip:
  • .flip-top   : top half of prevDigit that folds DOWN  (rotateX 0→-90)
  • .flip-bottom: bottom half of currentDigit that unfolds from 90→0
-->
<span class="flip-digit" class:colon={digit === ':'}>
  <!-- Static card: always shows currentDigit -->
  <span class="card" aria-hidden="true">
    <span class="card-top">{currentDigit}</span>
    <span class="card-bottom">{currentDigit}</span>
  </span>

  <!-- Animated overlays (only rendered while flipping) -->
  {#if flipping}
    <!-- Top overlay: shows prevDigit top half, folds down to -90deg -->
    <span
      class="overlay overlay-top"
      class:fold={flipStage === 'top-fold' || flipStage === 'bottom-reveal'}
      aria-hidden="true"
    >{prevDigit}</span>

    <!-- Bottom overlay: shows currentDigit bottom half, unfolds from 90deg to 0 -->
    <span
      class="overlay overlay-bottom"
      class:unfold={flipStage === 'bottom-reveal'}
      aria-hidden="true"
    >{currentDigit}</span>
  {/if}
</span>

<style>
  /* ── Container ── */
  .flip-digit {
    --digit-h: 1em;
    --digit-w: 0.72em;
    --bg: #0d1220;
    --text: #e8f0fe;
    --crease: #000;
    --shadow: rgba(0, 200, 255, 0.08);

    position: relative;
    display: inline-flex;
    flex-direction: column;
    width: var(--digit-w);
    height: var(--digit-h);
    perspective: 400px;
    perspective-origin: center center;
    /* Slight gap between digits */
    margin: 0 1px;
  }

  .flip-digit.colon {
    --digit-w: 0.3em;
  }

  /* ── Static card ── */
  .card {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-radius: 3px;
    box-shadow: 0 2px 8px var(--shadow);
    background: var(--bg);
  }

  .card-top,
  .card-bottom {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    color: var(--text);
    /* Monospace via parent, but enforce here too */
    font-family: inherit;
    line-height: 1;
    width: 100%;
  }

  .card-top {
    /* Top half: clip to upper 50% of the digit */
    align-items: flex-end;
    padding-bottom: 0;
    border-bottom: 1px solid var(--crease);
    background: #111827;
  }

  .card-bottom {
    /* Bottom half: clip to lower 50% */
    align-items: flex-start;
    background: #0d1220;
  }

  /* Trick: make each half show only its portion of the character
     by sizing them at 200% height and positioning accordingly */
  .card-top {
    height: 50%;
    min-height: 50%;
  }
  .card-bottom {
    height: 50%;
    min-height: 50%;
  }

  /* ── Flip overlays ── */
  .overlay {
    position: absolute;
    left: 0;
    right: 0;
    height: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border-radius: 3px 3px 0 0;
    transform-origin: bottom center;
    backface-visibility: hidden;
    color: var(--text);
    font-family: inherit;
    line-height: 1;
    background: #111827;
    /* Hardware-accelerated */
    will-change: transform;
    z-index: 10;
  }

  /* Top overlay: top half of prevDigit, folds DOWN */
  .overlay-top {
    top: 0;
    align-items: flex-end;
    border-radius: 3px 3px 0 0;
    transform-origin: bottom center;
    transform: rotateX(0deg);
    transition: transform 180ms cubic-bezier(0.4, 0, 1, 1);
    box-shadow: 0 4px 12px rgba(0,0,0,0.6);
    background: #111827;
    border-bottom: 1px solid var(--crease);
  }
  .overlay-top.fold {
    transform: rotateX(-90deg);
  }

  /* Bottom overlay: bottom half of currentDigit, unfolds from 90deg → 0 */
  .overlay-bottom {
    top: 50%;
    align-items: flex-start;
    border-radius: 0 0 3px 3px;
    transform-origin: top center;
    transform: rotateX(90deg);
    transition: none;
    background: #0d1220;
  }
  .overlay-bottom.unfold {
    transform: rotateX(0deg);
    transition: transform 180ms cubic-bezier(0, 0, 0.6, 1);
    box-shadow: 0 -2px 8px rgba(0,0,0,0.4);
  }
</style>
