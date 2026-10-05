// Native selectors own values, validation and editing. This module only presents
// Grok configuration dialogs; missing assets leave the native forms usable.
const DOMAIN = "grok_connector";
const PLUS = "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z";
const CLOSE = "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z";

function style(root, key, css) {
  if (root.querySelector(`style[data-grok-${key}]`)) return;
  const node = document.createElement("style");
  node.setAttribute(`data-grok-${key}`, "");
  node.textContent = css;
  root.append(node);
}

function setText(element, text) {
  // Keep native Lit markers and event handlers intact.
  for (const node of element.childNodes) {
    if (node.nodeType === Node.TEXT_NODE && node.textContent.trim()
        && node.textContent.trim() !== text) node.textContent = text;
  }
}

function setHeading(state, text) {
  if (!text) return;
  const heading = state.dialog.shadowRoot?.querySelector(".dialog-title");
  if (!heading) return;
  setText(heading, text);
  if (heading.title !== text) heading.title = text;
}

function addButton(button, label) {
  if (!button) return;
  if (button.appearance !== "filled") button.appearance = "filled";
  if (button.size !== "s") button.size = "s";
  if (label) setText(button, label);
  let icon = button.querySelector("ha-svg-icon");
  if (!icon) {
    icon = document.createElement("ha-svg-icon");
    icon.slot = "start";
    button.prepend(icon);
  }
  if (icon.path !== PLUS) icon.path = PLUS;
}

const LIST_SCROLL = `max-height:min(400px,45vh);overflow-y:auto;
  scrollbar-gutter:stable;overscroll-behavior:contain`;

async function refreshActionAfterEdit(native, state, event) {
  if (event.target !== native) return;
  // Property-only Lit updates (such as an icon change) need not mutate the
  // observed DOM. Wait for the native value propagation and render before the
  // next paint, then update presentation without touching the list value.
  await new Promise((resolve) => requestAnimationFrame(resolve));
  await native.updateComplete;
  if (native.isConnected && state.dialog.isConnected) decorateActions(native, state);
}

function decorateActions(native, state) {
  const config = native.selector?.object;
  if (!state.ours || state.stepId !== "actions"
      || config?.translation_key !== "grok_actions") return;
  const root = native.shadowRoot;
  if (!root) return;
  if (!state.actionListeners.has(native)) {
    const changed = (event) => refreshActionAfterEdit(native, state, event);
    native.addEventListener("value-changed", changed);
    state.actionListeners.add(native);
    state.cleanup.push(() => native.removeEventListener("value-changed", changed));
  }
  setHeading(state, native.label);
  style(root, "actions", `
    label {display:none!important}
    .items-container {display:flex;flex-direction:column;align-items:flex-start;gap:8px}
    ha-sortable {display:block;width:100%;${LIST_SCROLL}}
    ha-md-list-item.item {position:relative;background:var(--ha-color-form-background)!important;
      border:0!important;border-radius:var(--ha-border-radius-sm) var(--ha-border-radius-sm) 0 0!important;
      min-height:56px;--md-list-item-one-line-container-height:56px;
      --md-list-item-two-line-container-height:56px;--md-list-item-top-space:0px;
      --md-list-item-bottom-space:0px;--md-list-item-leading-space:var(--ha-space-4);
      --md-list-item-trailing-space:var(--ha-space-2);--ha-md-list-item-gap:var(--ha-space-2)}
    ha-md-list-item.item:after {content:"";position:absolute;bottom:0;left:0;right:0;
      height:1px;pointer-events:none;background:var(--ha-color-border-neutral-loud)}
    .label {font-weight:700}
    .description {color:var(--secondary-text-color);font-weight:400}
    .handle {display:none!important}
    .grok-action-icon {display:inline-flex;align-items:center;justify-content:center;
      width:40px;height:40px;color:var(--secondary-text-color);--mdc-icon-size:24px}
    ha-icon-button {color:var(--secondary-text-color);--ha-icon-button-size:32px;
      --ha-icon-button-padding-inline:var(--ha-space-1)}
    ha-button {--ha-button-height:32px}
  `);
  const sortable = root.querySelector("ha-sortable");
  if (sortable && !sortable.disabled) sortable.disabled = true;
  for (const row of root.querySelectorAll("ha-md-list-item")) {
    const buttons = [...row.querySelectorAll("ha-icon-button")];
    const edit = buttons.find((button) => button.item !== undefined);
    const remove = buttons.find((button) => button !== edit);
    let icon = row.querySelector("ha-icon.grok-action-icon");
    if (!icon) {
      icon = document.createElement("ha-icon");
      icon.className = "grok-action-icon";
      icon.slot = "start";
      row.prepend(icon);
    }
    const chosen = edit?.item?.icon || "mdi:play";
    if (icon.icon !== chosen) icon.icon = chosen;
    if (remove && remove.path !== CLOSE) remove.path = CLOSE;
    for (const button of buttons) {
      if (button.disabled !== !!native.disabled) button.disabled = !!native.disabled;
    }
    if (edit && remove && (edit.compareDocumentPosition(remove) & Node.DOCUMENT_POSITION_FOLLOWING)) {
      row.insertBefore(remove, edit);
    }
  }
  const button = root.querySelector(".items-container > ha-button");
  if (button && button.disabled !== !!native.disabled) button.disabled = !!native.disabled;
  addButton(button, native.localizeValue?.("grok_actions.options.add"));
}

function decorateEntities(host, state) {
  if (!state.ours || state.stepId !== "entities" || !host.shadowRoot) return;
  const root = host.shadowRoot;
  if (host.localName === "ha-selector-entity") {
    setHeading(state, host.label);
  } else if (host.localName === "ha-entities-picker") {
    style(root, "entities", `label {display:none!important}
      .list {margin-top:0!important;${LIST_SCROLL}}.entity:first-child {margin-top:0!important}`);
  } else if (host.localName === "ha-picker-field") {
    style(root, "entity-field", `[slot="headline"] {font-weight:700}
      [slot="supporting-text"] {font-weight:400}`);
    const clear = root.querySelector("ha-icon-button.clear");
    const label = state.hass?.localize("ui.common.delete");
    if (clear && label && clear.label !== label) clear.label = label;
  } else if (host.localName === "ha-generic-picker") {
    addButton(root.querySelector("#picker > slot > ha-button"));
  }
}

function canFinishOptions(host, state) {
  return state.ours && state.options && !state.finished.has(host)
    && host.flowConfig?.flowType === "options_flow"
    && host.step?.type === "create_entry" && !host.step.next_flow
    && typeof host.finish === "function";
}

async function finishOptions(host, state) {
  if (!canFinishOptions(host, state)) return;
  state.finished.add(host);
  try {
    await host.updateComplete;
    if (host.isConnected) await host.finish();
  } catch (_error) {
    // Preserve HA's native finish screen if the frontend contract changes.
    state.dialog.removeAttribute("data-grok-options");
    console.warn("Grok Connector: close the saved settings using HA's finish button.");
  }
}

const FORM_HOSTS = "step-flow-form,step-flow-create-entry,ha-form,ha-selector,ha-selector-object,"
  + "ha-selector-entity,ha-entities-picker,ha-entity-picker,ha-generic-picker,ha-picker-field";
const dialogs = new Map();

function watchDialog(dialog) {
  const state = { dialog, ours:false, options:false, stepId:undefined, hass:undefined,
    roots:new WeakSet(), pending:new WeakSet(), finished:new WeakSet(),
    actionListeners:new WeakSet(), cleanup:[], observers:[] };
  dialogs.set(dialog, state);

  function decorate(host) {
    if (host.localName === "step-flow-form") {
      state.ours = host.domain === DOMAIN;
      state.options = state.ours && host.flowConfig?.flowType === "options_flow";
      state.stepId = host.step?.step_id;
      state.hass = host.hass;
      dialog.toggleAttribute("data-grok-options", state.options);
      if (state.ours && ["entities", "actions"].includes(state.stepId)) {
        style(host.shadowRoot, "form", ".content > ha-markdown {display:none!important}");
      }
      if (state.options) {
        // Installed before completion: only a confirmed Grok options success is
        // skipped, while abort/error screens and other integrations stay visible.
        style(dialog.shadowRoot, "success", `:host([data-grok-options])
          ha-dialog:has(step-flow-create-entry) {visibility:hidden}`);
      }
    }
    if (!state.ours) return;
    if (host.localName === "step-flow-create-entry") finishOptions(host, state);
    else if (host.localName === "ha-selector-object") decorateActions(host, state);
    else decorateEntities(host, state);
  }

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
      decorate(host);
      for (const child of root.querySelectorAll(FORM_HOSTS)) visit(child);
    }
    if (state.roots.has(root)) {
      decorate(host);
      return;
    }
    state.roots.add(root);
    const observer = new MutationObserver(scan);
    observer.observe(root, { childList:true, subtree:true, characterData:true });
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
        for (const cleanup of state.cleanup) cleanup();
        dialogs.delete(dialog);
      }
    }
    for (const dialog of app.shadowRoot.querySelectorAll("dialog-data-entry-flow")) {
      if (!dialogs.has(dialog)) watchDialog(dialog);
    }
  };
  const observer = new MutationObserver(scan);
  observer.observe(app.shadowRoot, { childList:true, subtree:true });
  scan();
}
start().catch(() => {
  console.warn("Grok Connector: configuration forms are using HA's default appearance.");
});
