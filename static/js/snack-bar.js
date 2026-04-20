const CONTAINER_ID = 'snack-bar-container';
const AUTO_DISMISS_MS = 4000;
const ANIMATION_MS = 380;

const VARIANTS = {
  info: {
    label: 'Information',
    autoDismiss: true,
    colors: {
      bg:     'rgba(15, 23, 42, 0.8)',
      border: 'rgba(96, 165, 250, 0.25)',
      shadow: 'rgba(14, 30, 62, 0.55)',
      accent: '#60a5fa',
      icon:   'rgba(96, 165, 250, 0.12)',
    },
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
  },
  success: {
    label: 'Success',
    autoDismiss: true,
    colors: {
      bg:     'rgba(5, 25, 15, 0.8)',
      border: 'rgba(52, 211, 153, 0.25)',
      shadow: 'rgba(2, 25, 15, 0.55)',
      accent: '#34d399',
      icon:   'rgba(52, 211, 153, 0.12)',
    },
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
  },
  warning: {
    label: 'Warning',
    autoDismiss: false,
    colors: {
      bg:     'rgba(28, 20, 5, 0.8)',
      border: 'rgba(251, 191, 36, 0.28)',
      shadow: 'rgba(40, 28, 5, 0.55)',
      accent: '#fbbf24',
      icon:   'rgba(251, 191, 36, 0.12)',
    },
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
  },
  error: {
    label: 'Error',
    autoDismiss: false,
    colors: {
      bg:     'rgba(28, 8, 8, 0.8)',
      border: 'rgba(248, 113, 113, 0.28)',
      shadow: 'rgba(50, 8, 8, 0.55)',
      accent: '#f87171',
      icon:   'rgba(248, 113, 113, 0.12)',
    },
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>'
  },
};

function getOrCreateContainer() {
  let container = document.getElementById(CONTAINER_ID);

  if (!container) {
    container = document.createElement('div');
    container.id = CONTAINER_ID;

    Object.assign(container.style, {
      position: 'fixed',
      top: '2rem',
      right: '2rem',
      zIndex: '2147483647',
      display: 'flex',
      flexDirection: 'column',
      gap: '1.2rem',
      width: '36rem',
      maxWidth: 'calc(100vw - 4rem)',
      pointerEvents: 'none',
    });

    container.setAttribute('aria-label', 'Notifications');

    document.body.appendChild(container);
  }

  return container;
}



class SnackBarNotification extends HTMLElement {
  constructor() {
    super();
    this._shadow = this.attachShadow({ mode: 'open' });

    // Timer & animation state
    this._autoDismissTimer = null;  // setInterval ID for countdown
    this._progressRaf = null;       // requestAnimationFrame ID for progress bar
    this._startTime = null;         // Epoch ms when the current countdown began
    this._elapsed = 0;              // Accumulated elapsed ms (accounts for pause)
    this._paused = false;           // Whether the hover-pause is active
    this._dismissed = false;        // Guard against double-dismiss

    // Bound listeners (stored for clean removeEventListener)
    this._onMouseEnter = this._onMouseEnter.bind(this);
    this._onMouseLeave = this._onMouseLeave.bind(this);
    this._onDismiss = this._onDismiss.bind(this);
  }

  connectedCallback() {
    this._durationMs = this._resolveDuration();

    const type = this._resolveType();
    const variant = VARIANTS[type];

    // 1. Move this custom element into the snackbar container.
    // (If the user placed <snack-bar> in their HTML, we relocate it.)
    const container = getOrCreateContainer();
    if (this.parentElement !== container) {
      container.appendChild(this);
      // connectedCallback fires again after the re-append — bail on first call.
      return;
    }

    // 2. Render shadow DOM content.
    this._render(variant);

    // 3. Cache references to key shadow elements.
    this._snackEl = this._shadow.querySelector('.snackbar');
    this._progressEl = this._shadow.querySelector('.progress-fill');
    this._dismissBtn = this._shadow.querySelector('.dismiss');

    // 4. Wire up event listeners.
    this._wireEvents(variant);

    // 5. Trigger slide-in animation on the next frame (allows CSS transition to run).
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        this._snackEl.classList.add('visible');
      });
    });

    // 6. Start auto-dismiss countdown for info/success variants.
    if (variant.autoDismiss) {
      this._startCountdown();
    }
  }

  disconnectedCallback() {
    // Clean up all timers and listeners when element is removed.
    this._clearCountdown();
    this._snackEl?.removeEventListener('mouseenter', this._onMouseEnter);
    this._snackEl?.removeEventListener('mouseleave', this._onMouseLeave);
    this._dismissBtn?.removeEventListener('click', this._onDismiss);
  }

  // ───── Rendering ─────

  // Returns the validated `type` attribute, falling back to 'info'.
  _resolveType() {
    const attr = (this.getAttribute('type') || 'info').toLowerCase();
    return VARIANTS[attr] ? attr : 'info';
  }

  // Returns a duration in milliseconds from the optional `duration` attribute.
  _resolveDuration() {
    const raw = this.getAttribute('duration');
    if (!raw) return AUTO_DISMISS_MS;

    const parsed = this._parseDuration(raw);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      return AUTO_DISMISS_MS;
    }

    return parsed;
  }

  _parseDuration(raw) {
    const value = String(raw).trim();

    if (/^\d+(?:\.\d+)?ms$/i.test(value)) {
      return Number(value.slice(0, -2));
    }

    if (/^\d+(?:\.\d+)?s$/i.test(value)) {
      return Number(value.slice(0, -1)) * 1000;
    }

    return Number(value);
  }

  /**
   * Builds the complete shadow DOM HTML + CSS for this snackbar instance.
   */
  _render(variant) {
    this._shadow.innerHTML = `
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }

        :host {
          display: block;
          pointer-events: auto;
          font-family: 'DM Sans', 'Segoe UI', system-ui, sans-serif;
        }

        .snackbar {
          --snackbar-bg:       ${variant.colors.bg};
          --snackbar-border:   ${variant.colors.border};
          --snackbar-shadow:   ${variant.colors.shadow};
          --snackbar-accent:   ${variant.colors.accent};
          --snackbar-icon-col: ${variant.colors.icon};
          --snackbar-text:     #e8eaf0;
          --snackbar-subtext:  #aaaaaa;

          position: relative;
          display: grid;
          grid-template-columns: 3rem 1fr auto;
          grid-template-rows: auto auto;
          column-gap: 1.2rem;
          align-items: start;

          padding: 1.6rem 1.4rem 1.4rem;
          border-radius: 1rem;
          overflow: hidden;
          cursor: default;

          background: var(--snackbar-bg);
          backdrop-filter: blur(18px) saturate(160%);
          --webkit-backdrop-filter: blur(18px) saturate(160%);
          border: 1px solid var(--snackbar-border);
          box-shadow:
            0 4px 20px var(--snackbar-shadow),
            0 1px 0 rgba(255,255,255,0.08) inset;

          transform: translateX(calc(100% + 2.4rem));
          opacity: 0;
          transition:
            transform ${ANIMATION_MS}ms cubic-bezier(0.34, 1, 0.64, 1),
            opacity   ${ANIMATION_MS}ms ease;
        }

        .snackbar.visible {
          transform: translateX(0);
          opacity: 1;
        }

        .snackbar.leaving {
          transform: translateX(calc(100% + 2.4rem));
          opacity: 0;
          transition:
            transform ${ANIMATION_MS}ms cubic-bezier(0.4, 0, 0.8, 0.5),
            opacity   ${ANIMATION_MS}ms ease;
        }

        .icon-wrap {
          grid-column: 1;
          grid-row: 1;
          width: 3rem;
          height: 3rem;
          border-radius: 1rem;
          background: var(--snackbar-icon-col);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .icon-wrap svg {
          width: 1.8rem;
          height: 1.8rem;
          color: var(--snackbar-accent);
          stroke: var(--snackbar-accent);
        }

        .body {
          grid-column: 2;
          grid-row: 1;
          padding-top: 0.2rem;
          min-width: 0;
        }

        .label {
          font-size: 1.1rem;
          font-weight: 700;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--snackbar-accent);
          margin-bottom: 0.32rem;
        }

        .content {
          font-size: 1.4rem;
          line-height: 1.5;
          color: var(--snackbar-text);
          word-break: break-word;
        }

        .content ::slotted(p) {
          margin: 0;
          font-size: 1.4rem;
          line-height: 1.5;
          color: var(--snackbar-text);
        }

        .content ::slotted(strong), .content ::slotted(b) {
          color: #fff;
        }

        .dismiss {
          grid-column: 3;
          grid-row: 1;
          width: 2.6rem;
          height: 2.6rem;
          border-radius: 0.8rem;
          background: rgba(255,255,255,0.06);
          border: 1px solid rgba(255,255,255,0.1);
          color: var(--snackbar-subtext);
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
          flex-shrink: 0;
          margin-top: -0.2rem;
        }

        .dismiss:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #fff;
          transform: scale(1.1);
        }

        .dismiss:focus-visible {
          outline: 2px solid var(--snackbar-accent);
          outline-offset: 2px;
        }

        .dismiss svg {
          width: 1.3rem;
          height: 1.3rem;
          stroke: currentColor;
        }

        .progress-track {
          grid-column: 1 / -1;
          grid-row: 2;
          height: 0.3rem;
          border-radius: 99px;
          background: rgba(255, 255, 255, 0.1);
          margin-top: 1.2rem;
          overflow: hidden;
          display: ${variant.autoDismiss ? 'block' : 'none'};
        }

        .progress-fill {
          height: 100%;
          width: 0%;
          border-radius: 99px;
          background: var(--snackbar-accent);
          opacity: 0.85;
        }
      </style>

      <div
        class="snackbar"
        role="${variant.autoDismiss ? 'status' : 'alert'}"
        aria-live="${variant.autoDismiss ? 'polite' : 'assertive'}"
        aria-atomic="true"
        aria-label="${variant.label} notification"
      >
        <div class="icon-wrap" aria-hidden="true">
          ${variant.icon}
        </div>

        <div class="body">
          <div class="label">${variant.label}</div>
          <div class="content"><slot></slot></div>
        </div>

        <button
          class="dismiss"
          aria-label="Dismiss ${variant.label.toLowerCase()} notification"
          title="Dismiss"
        >
          <svg viewBox="0 0 7 7" aria-hidden="true" focusable="false">
            <path d="m1 1 5 5m0-5L1 6" fill="none" stroke-linecap="round"/>
          </svg>
        </button>

        ${variant.autoDismiss ? `
          <div class="progress-track" aria-hidden="true">
            <div class="progress-fill"></div>
          </div>
        ` : ''}
      </div>
    `;
  }

  // ───── Event Wiring ─────

  _wireEvents(variant) {
    this._dismissBtn.addEventListener('click', this._onDismiss);

    // Pause-on-hover only applies to auto-dismissing variants.
    if (variant.autoDismiss) {
      this._snackEl.addEventListener('mouseenter', this._onMouseEnter);
      this._snackEl.addEventListener('mouseleave', this._onMouseLeave);
    }
  }

  _onMouseEnter() {
    if (!this._paused) {
      // Record how much time had elapsed when the user hovered.
      this._elapsed += performance.now() - this._startTime;
      this._paused = true;
      this._clearCountdown();
    }
  }

  _onMouseLeave() {
    if (this._paused) {
      this._paused = false;
      // Resume countdown with remaining time.
      const remaining = this._durationMs - this._elapsed;
      if (remaining > 0) {
        this._startTime = performance.now();
        this._scheduleAutoDismiss(remaining);
        this._tickProgress();
      } else {
        this._dismiss();
      }
    }
  }

  _onDismiss() {
    this._dismiss();
  }

  // ───── Countdown & Progress ─────

  _startCountdown() {
    this._elapsed = 0;
    this._paused = false;
    this._startTime = performance.now();

    this._scheduleAutoDismiss(this._durationMs);
    this._tickProgress();
  }

  // Set a timeout that will trigger dismiss after `ms` milliseconds.
  _scheduleAutoDismiss(ms) {
    this._autoDismissTimer = setTimeout(() => {
      if (!this._paused) this._dismiss();
    }, ms);
  }

  /**
   * Drives the progress bar width using requestAnimationFrame.
   * Width goes from 0 → 100% over this._durationMs.
   */
  _tickProgress() {
    if (!this._progressEl) return;

    const tick = () => {
      if (this._paused || this._dismissed) return;

      const currentElapsed = this._elapsed + (performance.now() - this._startTime);
      const pct = Math.min((currentElapsed / this._durationMs) * 100, 100);
      this._progressEl.style.width = `${pct}%`;

      if (pct < 100) {
        this._progressRaf = requestAnimationFrame(tick);
      }
    };

    this._progressRaf = requestAnimationFrame(tick);
  }

  // Cancel all active timers.
  _clearCountdown() {
    if (this._autoDismissTimer) {
      clearTimeout(this._autoDismissTimer);
      this._autoDismissTimer = null;
    }
    if (this._progressRaf) {
      cancelAnimationFrame(this._progressRaf);
      this._progressRaf = null;
    }
  }

  // ───── Dismissal ─────

  // Triggers the slide-out animation and removes the element from the DOM.
  _dismiss() {
    if (this._dismissed) return;
    this._dismissed = true;

    this._clearCountdown();

    // Trigger slide-out CSS transition.
    this._snackEl.classList.remove('visible');
    this._snackEl.classList.add('leaving');

    // Wait for the transition to finish, then remove from DOM.
    setTimeout(() => {
      this.remove();
    }, ANIMATION_MS + 50); // small buffer past transition end
  }
}

if (!customElements.get('snack-bar')) customElements.define('snack-bar', SnackBarNotification);