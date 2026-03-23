class HexColorPicker extends HTMLElement {
  static get formAssociated() {
    return true;
  }

  static get observedAttributes() {
    return ['value'];
  }

  constructor() {
    super();
    this._internals = this.attachInternals();
    this.attachShadow({ mode: 'open' });
    this._isRendered = false;

    this.baseColorPalette = [
      ["#FF7100", "#FF4B14", "#FF1B1B", "#FF144B", "#FF0071"],
      ["#FFB420", "#FF9440", "#FF6D52", "#FF526D", "#FF4094", "#FF20B4"],
      ["#FFF231", "#FFD75E", "#FFB880", "#FF8D8D", "#FF80B8", "#FF5ED7", "#FF31F2"],
      ["#CEFF2F", "#EAFF65", "#FFF998", "#FFDBBF", "#FFBFDB", "#FF98F9", "#EA65FF", "#CE2FFF"],
      ["#8DFF1B", "#A9FF54", "#C6FF8D", "#E2FFC6", "#FFFFFF", "#E2C6FF", "#C68DFF", "#A954FF", "#8D1BFF"],
      ["#60FF2F", "#7AFF65", "#98FF9F", "#BFFFE3", "#BFE3FF", "#989FFF", "#7A65FF", "#602FFF"],
      ["#31FF3E", "#5EFF86", "#80FFC7", "#8DFFFF", "#80C7FF", "#5E86FF", "#313EFF"],
      ["#20FF6B", "#40FFAA", "#52FFE4", "#52E4FF", "#40AAFF", "#206BFF"],
      ["#00FF8E", "#14FFC8", "#1BFFFF", "#14C8FF", "#008EFF"]
    ];

    this._value = '';
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'value' && oldValue !== newValue) {
      if (this._isRendered) {
        const colorToApply = newValue || this.baseColorPalette[0][0];

        if (colorToApply.toUpperCase() !== this._value.toUpperCase()) {
          this.selectColor(colorToApply);
        }
      }
    }
  }

  connectedCallback() {
    if (!this._isRendered) {
      this.render();
      this.cacheDOM();
      this.bindEvents();
      this._isRendered = true;
    }

    const initialValue = this.getAttribute('value') || this.baseColorPalette[0][0];
    this.selectColor(initialValue);
  }

  formResetCallback() {
    const resetValue = this.getAttribute('value') || this.baseColorPalette[0][0];
    this.selectColor(resetValue);
  }

  get value() { return this._value; }
  set value(v) { this.selectColor(v); }
  get form() { return this._internals.form; }
  get name() { return this.getAttribute('name'); }
  get type() { return this.localName; }

  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; overflow-x: auto; overflow-y: hidden; }
        .visually-hidden {
          position: absolute !important; width: 1px !important; height: 1px !important;
          padding: 0 !important; margin: -1px !important; overflow: hidden !important;
          clip: rect(0, 0, 0, 0) !important; white-space: nowrap !important; border: 0 !important;
        }
        #color-display {
          width: min-content; min-width: 9rem;
          padding: 0.2rem 0.6rem; margin-bottom: 1rem;
          box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
          border-radius: 0.4rem;
          font-weight: 500; font-size: 1.4rem; text-align: center;
          transition: background-color 0.3s, color 0.3s;
        }
        .color-picker-container { display: flex; gap: 3rem; padding: 0.4rem; }
        fieldset { border: none; padding: 0; margin: 0; }
        #shade-palette { margin-top: 0.2rem; }
        .palette-row { display: flex; justify-content: center; margin-bottom: -0.65rem; }
        .base-swatch, .shade-swatch { display: block; position: relative; cursor: pointer; transition: transform 0.2s ease; }
        .base-swatch { width: 2.2rem; height: 2.6rem; clip-path: polygon(50% 0, 100% 25%, 100% 75%, 50% 100%, 0 75%, 0 25%); scale: 1.05; }
        .shade-swatch { width: 2rem; height: 2rem; }
        .base-swatch:hover, .shade-swatch:hover { transform: scale(1.15); }
        .base-swatch:has(input:focus-visible)::after, .shade-swatch:has(input:focus-visible)::after {
          content: "";
          position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
          width: 0.6rem; height: 0.6rem;
          background-color: #000; border-radius: 50%;
        }
        .shade-swatch:nth-of-type(n+5):nth-of-type(-n+9):has(input:focus-visible)::after { background-color: #fff; }
      </style>

      <div id="color-display" aria-live="polite" aria-atomic="true"></div>
      <div class="color-picker-container">
        <fieldset id="base-palette">
          <legend class="visually-hidden">Base Color</legend>
          ${this.generateBasePaletteHTML()}
        </fieldset>
        <fieldset id="shade-palette">
          <legend class="visually-hidden">Shades</legend>
        </fieldset>
      </div>
    `;
  }

  cacheDOM() {
    this.colorDisplayEl = this.shadowRoot.querySelector('#color-display');
    this.basePaletteEl = this.shadowRoot.querySelector('#base-palette');
    this.shadePaletteEl = this.shadowRoot.querySelector('#shade-palette');
  }

  bindEvents() {
    this.basePaletteEl.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT' && e.target.name === 'base') {
        this.generateAndRenderShades(e.target.value);
      }
    });

    this.shadePaletteEl.addEventListener('change', (e) => {
      if (e.target.name === 'shade') this.updateDisplay(e.target.value);
    });
  }

  generateBasePaletteHTML() {
    return this.baseColorPalette.map(row =>
      `<div class="palette-row">
         ${row.map(hexCode =>
          `<label class="base-swatch" style="background:${hexCode}" title="Base color ${hexCode}">
            <input type="radio" name="base" value="${hexCode}" class="visually-hidden" aria-label="Base color ${hexCode}">
          </label>`
        ).join('')}
      </div>`
    ).join('');
  }

  selectColor(targetHex) {
    targetHex = targetHex.toUpperCase();
    let matchedBase = this.baseColorPalette[0][0];
    let matchedShade = null;

    outerLoop: for (let r = 0; r < this.baseColorPalette.length; r++) {
      for (let c = 0; c < this.baseColorPalette[r].length; c++) {
        const testBase = this.baseColorPalette[r][c];
        const red = parseInt(testBase.slice(1, 3), 16);
        const green = parseInt(testBase.slice(3, 5), 16);
        const blue = parseInt(testBase.slice(5, 7), 16);

        for (let i = 0; i < 9; i++) {
          const factor = (8 - i) / 8;
          const sR = Math.round(red * factor).toString(16).padStart(2, '0');
          const sG = Math.round(green * factor).toString(16).padStart(2, '0');
          const sB = Math.round(blue * factor).toString(16).padStart(2, '0');
          const testShade = `#${sR}${sG}${sB}`.toUpperCase();

          if (testShade === targetHex) {
            matchedBase = testBase;
            matchedShade = targetHex;
            break outerLoop;
          }
        }
      }
    }

    const baseRadio = this.shadowRoot.querySelector(`input[name="base"][value="${matchedBase}"]`);
    if (baseRadio) baseRadio.checked = true;

    this.generateAndRenderShades(matchedBase, matchedShade || targetHex);
  }

  generateAndRenderShades(hex, forceSelectedShade = null) {
    const red = parseInt(hex.slice(1, 3), 16);
    const green = parseInt(hex.slice(3, 5), 16);
    const blue = parseInt(hex.slice(5, 7), 16);

    let defaultShadeToSelect = null;

    const shadeElements = Array.from({ length: 9 }, (_, index) => {
      const brightnessFactor = (8 - index) / 8;
      const calcHexChannel = (colorValue) => Math.round(colorValue * brightnessFactor).toString(16).padStart(2, '0');
      const shadeHexCode = `#${calcHexChannel(red)}${calcHexChannel(green)}${calcHexChannel(blue)}`.toUpperCase();

      if (index === 0) defaultShadeToSelect = shadeHexCode;
      const isChecked = forceSelectedShade ? (shadeHexCode === forceSelectedShade) : (index === 0);

      return `<label class="shade-swatch" style="background:${shadeHexCode}" title="Shade ${shadeHexCode}">
                <input type="radio" name="shade" value="${shadeHexCode}" class="visually-hidden" aria-label="Shade ${shadeHexCode}" ${isChecked ? 'checked' : ''}>
              </label>`;
    }).join('');

    this.shadePaletteEl.innerHTML = `<legend class="visually-hidden">Shades</legend>` + shadeElements;

    this.updateDisplay(forceSelectedShade || defaultShadeToSelect);
  }

  updateDisplay(hexCode) {
    const red = parseInt(hexCode.slice(1, 3), 16);
    const green = parseInt(hexCode.slice(3, 5), 16);
    const blue = parseInt(hexCode.slice(5, 7), 16);
    const yiq = ((red * 299) + (green * 587) + (blue * 114)) / 1000;

    this.colorDisplayEl.innerText = hexCode;
    this.colorDisplayEl.style.backgroundColor = hexCode;
    this.colorDisplayEl.style.color = (yiq >= 128) ? '#000000' : '#FFFFFF';

    this._value = hexCode;
    this._internals.setFormValue(hexCode);

    this.dispatchEvent(new CustomEvent('color-changed', {
      detail: { hex: hexCode },
      bubbles: true,
      composed: true
    }));
  }
}

customElements.define('hex-color-picker', HexColorPicker);