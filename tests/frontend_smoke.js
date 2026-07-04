const assert = require("assert");
const fs = require("fs");
const vm = require("vm");

function response(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
  };
}

function createHarness({ confirmResult = true, search = "" } = {}) {
  const elements = new Map();
  const calls = { confirm: [], fetch: [], open: [], clipboard: [], toast: [] };
  elements.set("string_session", { value: "", placeholder: "" });
  elements.set("toast", {
    appendChild(item) { calls.toast.push(item.textContent); },
  });

  const context = {
    console,
    URL,
    URLSearchParams,
    FormData: class FormData {},
    setTimeout(fn) { return fn(); },
    alert(text) { calls.toast.push(text); },
    confirm(message) { calls.confirm.push(message); return confirmResult; },
    location: { origin: "http://127.0.0.1:5000", pathname: "/login", search, href: "" },
    navigator: {
      clipboard: {
        writeText: async (text) => { calls.clipboard.push(text); },
      },
    },
    window: {
      open(url, target, features) { calls.open.push({ url, target, features }); },
    },
    document: {
      getElementById(id) { return elements.get(id) || null; },
      createElement() { return { className: "", textContent: "", remove() {} }; },
      querySelectorAll() { return []; },
    },
    io() { return { on() {} }; },
    fetch: async (path, options = {}) => {
      calls.fetch.push({ path, options });
      if (path === "/api/session/export-token") {
        const body = JSON.parse(options.body || "{}");
        return response({ success: true, data: { export_token: `${body.kind}-token` } });
      }
      if (String(path).startsWith("/api/session/string")) {
        return response({ success: true, data: { string_session: "exported-string-session" } });
      }
      if (String(path).startsWith("/api/task/")) {
        return response({ success: true, data: { task_id: "task-1" } });
      }
      return response({ success: true, data: [] });
    },
  };
  context.globalThis = context;

  vm.createContext(context);
  vm.runInContext(fs.readFileSync("static/js/app.js", "utf8"), context, { filename: "static/js/app.js" });
  calls.fetch.length = 0;
  calls.toast.length = 0;
  return { context, elements, calls };
}

async function testCancelingStringExportDoesNotRequestToken() {
  const { context, calls } = createHarness({ confirmResult: false });
  await context.exportStringSession();
  assert.strictEqual(calls.confirm.length, 1);
  assert.deepStrictEqual(calls.fetch, []);
}

async function testStringExportRequestsOneTimeToken() {
  const { context, elements, calls } = createHarness({ confirmResult: true });
  await context.exportStringSession();
  assert.strictEqual(calls.confirm.length, 1);
  assert.strictEqual(calls.fetch[0].path, "/api/session/export-token");
  assert.deepStrictEqual(JSON.parse(calls.fetch[0].options.body), { kind: "string" });
  assert.strictEqual(calls.fetch[1].path, "/api/session/string?export_token=string-token");
  assert.strictEqual(elements.get("string_session").value, "exported-string-session");
  assert.deepStrictEqual(calls.clipboard, ["exported-string-session"]);
}

async function testFileExportOpensTokenizedDownloadUrl() {
  const { context, calls } = createHarness({ confirmResult: true, search: "?token=web-token" });
  await context.exportSessionFile();
  assert.strictEqual(calls.fetch[0].path, "/api/session/export-token");
  assert.deepStrictEqual(JSON.parse(calls.fetch[0].options.body), { kind: "file" });
  assert.strictEqual(calls.open.length, 1);
  assert.strictEqual(calls.open[0].url, "/api/session/file?export_token=file-token&token=web-token");
}

async function testTaskDeleteConfirmationControlsRequest() {
  let harness = createHarness({ confirmResult: false });
  await harness.context.taskDelete("task-1", "running");
  assert.strictEqual(harness.calls.confirm.length, 1);
  assert.deepStrictEqual(harness.calls.fetch, []);

  harness = createHarness({ confirmResult: true });
  harness.context.loadDownloadTasks = async () => {};
  harness.context.loadDownloadFiles = async () => {};
  await harness.context.taskDelete("task-1", "done");
  assert.strictEqual(harness.calls.fetch[0].path, "/api/task/task-1");
  assert.strictEqual(harness.calls.fetch[0].options.method, "DELETE");
}

async function main() {
  await testCancelingStringExportDoesNotRequestToken();
  await testStringExportRequestsOneTimeToken();
  await testFileExportOpensTokenizedDownloadUrl();
  await testTaskDeleteConfirmationControlsRequest();
  console.log("frontend smoke passed");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
