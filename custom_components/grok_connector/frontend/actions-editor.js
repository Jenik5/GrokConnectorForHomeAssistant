// Progressive presentation of a native HA object selector. The backend always
// returns `object`, so missing/cached JavaScript cannot hide the action editor.
const PLAY = "M8,5.14V19.14L19,12.14L8,5.14Z";
const PLUS = "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z";

function decorate(native) {
  const config = native.selector?.object;
  if (config?.translation_key !== "grok_actions" || config.label_field !== "name"
      || config.description_field !== "description") return;
  const root = native.shadowRoot;
  if (!root) return;
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
  for (const button of root.querySelectorAll("ha-icon-button")) button.disabled = !!native.disabled;
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
  button.disabled = !!native.disabled;
  button.appearance = "accent";
  button.size = "small";
  const label = native.localizeValue?.("grok_actions.options.add") || "Add action";
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

// Observe only HA's config-flow dialogs and their form/selector roots. We never
// replace a native component, prototype, value or event handler. Other object
// selectors retain their native appearance and behavior.
const FORM_HOSTS = "step-flow-form,ha-form,ha-selector,ha-selector-object";
const dialogs = new Map();

function watchDialog(dialog) {
  const state = { roots: new WeakSet(), pending: new WeakSet(), observers: [] };
  dialogs.set(dialog, state);

  function visit(host) {
    if (!host.isConnected) return;
    if (!host.shadowRoot) {
      if (state.pending.has(host)) return;
      state.pending.add(host);
      customElements.whenDefined(host.localName).then(async () => {
        await host.updateComplete;
        state.pending.delete(host);
        if (host.isConnected && dialogs.get(dialog) === state) visit(host);
      });
      return;
    }
    const root = host.shadowRoot;
    function scan() {
      if (!dialog.isConnected) return;
      if (host.localName === "ha-selector-object") decorate(host);
      for (const child of root.querySelectorAll(FORM_HOSTS)) visit(child);
    }
    if (state.roots.has(root)) {
      if (host.localName === "ha-selector-object") decorate(host);
      return;
    }
    state.roots.add(root);
    const observer = new MutationObserver(scan);
    observer.observe(root, { childList: true, subtree: true, characterData: true });
    state.observers.push(observer);
    scan();
  }
  visit(dialog);
}

async function start() {
  await customElements.whenDefined("home-assistant");
  const app = document.querySelector("home-assistant");
  if (!app) return;
  await app.updateComplete;
  if (!app.shadowRoot) return;
  const scan = () => {
    for (const [dialog, state] of dialogs) {
      if (!dialog.isConnected) {
        for (const observer of state.observers) observer.disconnect();
        dialogs.delete(dialog);
      }
    }
    for (const dialog of app.shadowRoot.querySelectorAll("dialog-data-entry-flow")) {
      if (!dialogs.has(dialog)) watchDialog(dialog);
    }
  };
  const observer = new MutationObserver(scan);
  observer.observe(app.shadowRoot, { childList: true, subtree: true });
  scan();
}
start().catch(() => {
  // A frontend structure change affects presentation only; native editing works.
  console.warn("Grok Connector: native action editor is using its default appearance.");
});
