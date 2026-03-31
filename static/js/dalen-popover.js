import { computePosition, autoUpdate, flip, offset, size } from '../vendor/floating-ui/floating-ui.bundle.js';

class DlPopover extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: contents;
        }
        .popover-container {
          position: absolute;
          top: 0;
          left: 0;
          z-index: 9999;
          box-sizing: border-box;
          padding: 1rem;
          background: #ffffff;
          box-shadow: 0 0 8px rgba(0, 0, 0, 0.05);
          border: 1px solid #eeeeee;
          border-radius: 8px;
          overflow: auto; 
          overscroll-behavior: none;
          opacity: 0;
          transform: scale(0.95);
          visibility: hidden;
          pointer-events: none;
          transition: opacity 0.2s, transform 0.2s, visibility 0.2s;
        }
        .popover-container.open {
          opacity: 1;
          transform: scale(1);
          visibility: visible;
          pointer-events: auto;
        }
      </style>
      <div class="popover-container" part="container" tabindex="-1">
        <slot></slot>
      </div>
    `;

    this._isOpen = false;
    this._anchor = null;
    this._popover = this.shadowRoot.querySelector('.popover-container');
    this._cleanupAutoUpdate = null;

    this._isInitialUpdate = true;
    this._lockedPlacement = null;

    this.toggle = this.toggle.bind(this);
    this.close = this.close.bind(this);
    this.updatePosition = this.updatePosition.bind(this);
    this._handleOutsideClick = this._handleOutsideClick.bind(this);
    this._handleKeyDown = this._handleKeyDown.bind(this);
  }

  connectedCallback() {
    const anchorId = this.getAttribute('anchor-id');
    if (!anchorId) return;

    requestAnimationFrame(() => {
      this._anchor = document.getElementById(anchorId);
      if (this._anchor) {
        this._anchor.addEventListener('click', this.toggle);

        this._anchor.setAttribute('aria-haspopup', 'menu');
        this._anchor.setAttribute('aria-expanded', 'false');

        if (!this.id) {
          this.id = `dl-popover-${Math.random().toString(36).substring(2, 9)}`;
        }
        this._anchor.setAttribute('aria-controls', this.id);

        const label = this.getAttribute('aria-label') || 'Popover content';
        this.setAttribute('aria-label', label);

        this.setAttribute('role', 'menu');
      } else {
        console.warn(`Anchor with id "${anchorId}" not found.`);
      }
    });
  }

  disconnectedCallback() {
    if (this._anchor) {
      this._anchor.removeEventListener('click', this.toggle);
    }
    if (this._isOpen) {
      this.close();
    }
  }

  toggle(event) {
    if (event) event.preventDefault();
    this._isOpen ? this.close() : this.open();
  }

  open() {
    if (this._isOpen || !this._anchor) return;
    this._isOpen = true;

    // Reset the initial update flag so we do a full calculation (flip/size) once on open
    this._isInitialUpdate = true;

    this._popover.classList.add('open');
    this._anchor.setAttribute('aria-expanded', 'true');

    // Start autoUpdate. This immediately calls updatePosition once, then listens to scroll/resize.
    this._cleanupAutoUpdate = autoUpdate(
      this._anchor,
      this._popover,
      this.updatePosition
    );

    document.addEventListener('mousedown', this._handleOutsideClick);
    document.addEventListener('keydown', this._handleKeyDown);

    setTimeout(() => { this._popover.focus(); }, 50);
  }

  close() {
    if (!this._isOpen || !this._anchor) return;
    this._isOpen = false;

    this._popover.classList.remove('open');
    this._anchor.setAttribute('aria-expanded', 'false');

    if (this._cleanupAutoUpdate) {
      this._cleanupAutoUpdate();
      this._cleanupAutoUpdate = null;
    }

    document.removeEventListener('mousedown', this._handleOutsideClick);
    document.removeEventListener('keydown', this._handleKeyDown);
  }

  async updatePosition() {
    if (!this._anchor || !this._popover) return;

    // Determine target placement: fallback to attribute, or use the locked one if scrolling
    const currentPlacement = this._isInitialUpdate
      ? (this.getAttribute('placement') || 'top')
      : this._lockedPlacement;

    // Base middleware
    const middleware = [offset(10)];

    // Only run flip() on the very first render.
    if (this._isInitialUpdate) middleware.push(flip());

    middleware.push(
      size({
        padding: 10,
        apply({ availableWidth, availableHeight, elements }) {
          Object.assign(elements.floating.style, {
            maxWidth: `${Math.max(0, availableWidth)}px`,
            maxHeight: `${Math.max(0, availableHeight)}px`,
          });
        }
      })
    );

    // Compute the position
    const { x, y, placement } = await computePosition(this._anchor, this._popover, {
      placement: currentPlacement,
      middleware: middleware,
      strategy: 'absolute'
    });

    // Lock the resulting placement
    if (this._isInitialUpdate) {
      this._lockedPlacement = placement;
      this._isInitialUpdate = false;
    }

    Object.assign(this._popover.style, { left: `${x}px`, top: `${y}px` });
  }

  _handleOutsideClick(event) {
    const composedPath = event.composedPath();
    if (!composedPath.includes(this) && !composedPath.includes(this._anchor)) {
      this.close();
    }
  }

  _handleKeyDown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      this.close();

      if (this._anchor) this._anchor.focus();
    }
  }
}

customElements.define('dl-popover', DlPopover);