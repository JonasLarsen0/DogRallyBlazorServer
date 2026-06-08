<script lang="ts">
  /** Single split-flap tile. Accepts `char` (primary) or legacy `digit` prop. */
  export let char: string = '0';
  export let digit: string | undefined = undefined;

  // Normalise: `digit` is the legacy prop used by FlipClock
  $: _char = digit !== undefined ? digit : char;

  let prevChar    = _char;
  let currentChar = _char;
  let flipping    = false;
  let flipStage: 'top-fold' | 'bottom-reveal' | 'idle' = 'idle';
  let pendingChar: string | null = null;

  function triggerFlip(next: string) {
    if (flipping) {
      pendingChar = next;
      return;
    }
    if (next === currentChar) return;

    prevChar  = currentChar;
    flipping  = true;
    flipStage = 'top-fold';

    setTimeout(() => {
      currentChar = next;
      flipStage   = 'bottom-reveal';

      setTimeout(() => {
        flipping  = false;
        flipStage = 'idle';

        if (pendingChar !== null && pendingChar !== currentChar) {
          const p   = pendingChar;
          pendingChar = null;
          triggerFlip(p);
        }
      }, 180);
    }, 180);
  }

  $: if (_char !== currentChar) triggerFlip(_char);
</script>

<!--
  Physical split-flap tile layout:
  ┌─────────────┐  top half  – shows upper portion of character
  ══════════════   metallic crease / fold line
  └─────────────┘  bottom half – shows lower portion of character

  Two animated overlay panels fly during the flip transition.
-->
<span
  class="flip-digit"
  class:is-colon={_char === ':'}
  class:is-space={_char === ' ' || _char === '-'}
  aria-hidden="true"
>
  <!-- Static card: always shows currentChar -->
  <span class="card">
    <span class="card-top">{currentChar}</span>
    <span class="card-crease" aria-hidden="true"></span>
    <span class="card-bottom">{currentChar}</span>
  </span>

  <!-- Animated overlays (only while flipping) -->
  {#if flipping}
    <!-- Top overlay: prevChar top half folds downward 0 → -90° -->
    <span
      class="overlay overlay-top"
      class:fold={flipStage === 'top-fold' || flipStage === 'bottom-reveal'}
    >{prevChar}</span>

    <!-- Bottom overlay: currentChar bottom half unfolds 90° → 0 -->
    <span
      class="overlay overlay-bottom"
      class:unfold={flipStage === 'bottom-reveal'}
    >{currentChar}</span>
  {/if}
</span>

<style>
  /* ── Tile container ── */
  .flip-digit {
    --tile-h: 1em;
    --tile-w: 0.75em;
    --tile-bg-top:    #161b2e;
    --tile-bg-bottom: #111625;
    --tile-text:      #e8f4ff;
    --tile-crease:    #000000;
    --tile-shadow:    rgba(0, 212, 255, 0.07);
    --tile-radius:    3px;

    position: relative;
    display: inline-flex;
    flex-direction: column;
    width:  var(--tile-w);
    height: var(--tile-h);
    perspective: 500px;
    perspective-origin: center 50%;
    margin: 0 1.5px;
    flex-shrink: 0;
  }

  /* Narrower slot for colon and space characters */
  .flip-digit.is-colon { --tile-w: 0.32em; }
  .flip-digit.is-space  { --tile-w: 0.3em;  }

  /* ── Static card ── */
  .card {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    border-radius: var(--tile-radius);
    overflow: hidden;
    box-shadow:
      0 2px 10px rgba(0, 0, 0, 0.7),
      0 0 0 1px rgba(255, 255, 255, 0.04),
      inset 0 1px 0 rgba(255, 255, 255, 0.06);
  }

  .card-top {
    flex: 1;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 1px;
    background: var(--tile-bg-top);
    color: var(--tile-text);
    font-family: inherit;
    font-weight: inherit;
    font-size: inherit;
    line-height: 1;
    overflow: hidden;
    /* Subtle metallic highlight at the top edge */
    background-image: linear-gradient(
      to bottom,
      rgba(255, 255, 255, 0.07) 0%,
      transparent 40%
    );
  }

  /* 1 px physical crease line — looks like the split point of a real tile */
  .card-crease {
    display: block;
    height: 1px;
    background: var(--tile-crease);
    flex-shrink: 0;
    /* Metallic sheen at the fold */
    box-shadow: 0 0.5px 0 rgba(255, 255, 255, 0.12);
  }

  .card-bottom {
    flex: 1;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding-top: 1px;
    background: var(--tile-bg-bottom);
    color: var(--tile-text);
    font-family: inherit;
    font-weight: inherit;
    font-size: inherit;
    line-height: 1;
    overflow: hidden;
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
    color: var(--tile-text);
    font-family: inherit;
    font-weight: inherit;
    font-size: inherit;
    line-height: 1;
    will-change: transform;
    backface-visibility: hidden;
    z-index: 10;
  }

  /* Top overlay: upper half of prevChar, folds DOWN */
  .overlay-top {
    top: 0;
    align-items: flex-end;
    padding-bottom: 1px;
    background: var(--tile-bg-top);
    background-image: linear-gradient(
      to bottom,
      rgba(255, 255, 255, 0.07) 0%,
      transparent 40%
    );
    border-radius: var(--tile-radius) var(--tile-radius) 0 0;
    transform-origin: bottom center;
    transform: rotateX(0deg);
    transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1);
    box-shadow:
      0 4px 16px rgba(0, 0, 0, 0.8),
      0 0 0 1px rgba(255, 255, 255, 0.04);
    border-bottom: 1px solid var(--tile-crease);
  }
  .overlay-top.fold {
    transform: rotateX(-90deg);
  }

  /* Bottom overlay: lower half of currentChar, unfolds UP (90° → 0) */
  .overlay-bottom {
    top: 50%;
    align-items: flex-start;
    padding-top: 1px;
    background: var(--tile-bg-bottom);
    border-radius: 0 0 var(--tile-radius) var(--tile-radius);
    transform-origin: top center;
    transform: rotateX(90deg);
    transition: none;
  }
  .overlay-bottom.unfold {
    transform: rotateX(0deg);
    transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1);
    box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.5);
  }
</style>
