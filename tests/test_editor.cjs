const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname,
  "../custom_components/grok_connector/frontend/actions-editor.js"), "utf8");
const api = { customElements:{whenDefined:() => new Promise(() => {})},
  console:{warn:() => {}} };
vm.runInNewContext(source, api);

function fixture() {
  const state = {ours:true, options:true, finished:new WeakSet(),
    dialog:{removeAttribute:() => {}}};
  const host = {flowConfig:{flowType:"options_flow"}, step:{type:"create_entry"},
    isConnected:true, finish:async () => {}};
  return {state,host};
}

test("auto finish accepts only confirmed Grok options success", () => {
  const {state,host} = fixture();
  assert.equal(api.canFinishOptions(host,state), true);
  for (const type of ["form","abort","progress"]) {
    assert.equal(api.canFinishOptions({...host,step:{type}},state), false);
  }
  assert.equal(api.canFinishOptions(host,{...state,ours:false}), false);
  assert.equal(api.canFinishOptions(host,{...state,options:false}), false);
  assert.equal(api.canFinishOptions({...host,flowConfig:{flowType:"config_flow"}},state), false);
  assert.equal(api.canFinishOptions({...host,step:{type:"create_entry",next_flow:["options_flow","id"]}},state), false);
});

test("native finish runs once, and an error form remains open", async () => {
  const {state,host} = fixture();
  let finishes = 0;
  host.finish = async () => {finishes++;};
  await api.finishOptions({...host,step:{type:"form",errors:{base:"invalid_action"}}},state);
  assert.equal(finishes,0);
  await api.finishOptions(host,state);
  await api.finishOptions(host,state);
  assert.equal(finishes,1);
});

test("a changed native finish API leaves the native finish screen available", async () => {
  const {state,host} = fixture();
  let shown = 0;
  state.dialog.removeAttribute = key => {assert.equal(key,"data-grok-options");shown++;};
  host.finish = async () => {throw new Error("example");};
  await api.finishOptions(host,state);
  assert.equal(shown,1);
});

test("foreign object selectors are not decorated", () => {
  const native = {selector:{object:{translation_key:"another_integration"}},
    get shadowRoot() {throw new Error("Foreign DOM was inspected");}};
  api.decorateActions(native,{ours:true,stepId:"actions"});
  api.decorateActions({selector:{object:{translation_key:"grok_actions"}},
    get shadowRoot() {throw new Error("Foreign flow DOM was inspected");}},
    {ours:false,stepId:"actions"});
});

test("an icon-only native edit refreshes presentation after rendering", async () => {
  let frame;
  let renders = 0;
  const native = {isConnected:true, updateComplete:Promise.resolve()};
  const state = {dialog:{isConnected:true}};
  const original = api.decorateActions;
  api.requestAnimationFrame = (callback) => {frame = callback;};
  api.decorateActions = (host, supplied) => {
    assert.equal(host,native);
    assert.equal(supplied,state);
    renders++;
  };
  try {
    const pending = api.refreshActionAfterEdit(native,state,{target:native});
    assert.equal(renders,0);
    frame();
    await pending;
    assert.equal(renders,1);
    frame = undefined;
    await api.refreshActionAfterEdit(native,state,{target:{}});
    assert.equal(frame,undefined);
    const detached = api.refreshActionAfterEdit(native,state,{target:native});
    native.isConnected = false;
    frame();
    await detached;
    assert.equal(renders,1);
  } finally {
    api.decorateActions = original;
  }
});
