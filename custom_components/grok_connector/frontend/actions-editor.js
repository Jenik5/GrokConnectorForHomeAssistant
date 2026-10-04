// A scoped presentation of HA's object selector. HA owns the list operations,
// dialogs and action editor; this adapter only changes this integration's view.
const PROPERTIES = ["hass", "value", "selector", "label", "helper", "placeholder",
  "disabled", "required", "localizeValue", "narrow", "context"];
const PLAY = "M8,5.14V19.14L19,12.14L8,5.14Z";
const PLUS = "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z";

class GrokActionList extends HTMLElement {
  constructor() {
    super();
    this._properties = {};
    this.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = ":host {display:block} ha-selector {display:block}";
    this.shadowRoot.append(style);
    this._list = document.createElement("ha-selector");
    this.shadowRoot.append(this._list);
    this._observer = new MutationObserver(() => this._decorate());
    this._list.addEventListener("value-changed", (event) => {
      this._properties.value = event.detail.value;
    });
  }

  connectedCallback() {
    // A custom element may receive properties before its extra module loads.
    for (const key of PROPERTIES) {
      if (Object.prototype.hasOwnProperty.call(this, key)) {
        const value = this[key];
        delete this[key];
        this[key] = value;
      }
    }
    this._connect();
  }

  disconnectedCallback() { this._observer.disconnect(); }

  async _connect() {
    await customElements.whenDefined("ha-selector");
    this._sync();
    await customElements.whenDefined("ha-selector-object");
    await this._list.updateComplete;
    const native = this._list.shadowRoot.querySelector("ha-selector-object");
    if (!native) return;
    await native.updateComplete;
    if (!this.isConnected) return;
    this._native = native;
    this._observer.observe(native.shadowRoot, { childList: true, subtree: true, characterData: true });
    this._decorate();
  }

  _sync() {
    for (const key of PROPERTIES) {
      if (key === "selector") continue;
      this._list[key] = this._properties[key];
    }
    const config = this._properties.selector?.grok_connector_actions;
    if (config) this._list.selector = { object: config };
    this._decorate();
  }

  _decorate() {
    const root = this._native?.shadowRoot;
    if (!root) return;
    // Deliberately confined to our own nested selector. No global HA component,
    // prototype, theme or another integration's form is changed.
    if (!root.querySelector("style[data-grok-actions]")) {
      const style = document.createElement("style");
      style.dataset.grokActions = "";
      style.textContent = `
        .items-container {display:flex;flex-direction:column;align-items:flex-start;gap:8px}
        ha-sortable {width:100%}
        ha-md-list-item {background:var(--secondary-background-color);border:0;
          border-radius:4px;min-height:56px;--md-list-item-two-line-container-height:56px}
        .label {font-weight:700}
        .description {color:var(--secondary-text-color);font-weight:400}
        .handle {color:var(--secondary-text-color)}
        ha-icon-button {color:var(--secondary-text-color)}
        ha-button {--ha-button-height:32px}
      `;
      root.append(style);
    }
    for (const icon of root.querySelectorAll(".handle")) icon.path = PLAY;
    for (const button of root.querySelectorAll("ha-icon-button")) button.disabled = !!this.disabled;
    for (const row of root.querySelectorAll("ha-md-list-item")) {
      const buttons = [...row.querySelectorAll("ha-icon-button")];
      const edit = buttons.find((button) => button.item !== undefined);
      const remove = buttons.find((button) => button !== edit);
      if (edit && remove && (edit.compareDocumentPosition(remove) & Node.DOCUMENT_POSITION_FOLLOWING)) {
        // Keep both native event handlers and DOM nodes, in the requested order.
        row.insertBefore(remove, edit);
      }
    }
    const button = root.querySelector(".items-container > ha-button");
    if (!button) return;
    button.disabled = !!this.disabled;
    button.appearance = "accent";
    button.size = "small";
    const label = this.localizeValue?.("grok_actions.options.add") || "Add action";
    // Preserve Lit's text node and markers so native rerenders remain valid.
    for (const node of button.childNodes) {
      if (node.nodeType === Node.TEXT_NODE && node.textContent.trim() && node.textContent.trim() !== label) {
        node.textContent = label;
      }
    }
    if (!button.querySelector("ha-svg-icon")) {
      const icon = document.createElement("ha-svg-icon");
      icon.path = PLUS;
      icon.slot = "start";
      button.prepend(icon);
    }
  }

  reportValidity() { return this._list.reportValidity?.() ?? true; }
  focus() { this._list.focus(); }
}

for (const key of PROPERTIES) {
  Object.defineProperty(GrokActionList.prototype, key, {
    get() { return this._properties[key]; },
    set(value) { this._properties[key] = value; this._sync(); },
  });
}
if (!customElements.get("ha-selector-grok_connector_actions")) {
  customElements.define("ha-selector-grok_connector_actions", GrokActionList);
}
