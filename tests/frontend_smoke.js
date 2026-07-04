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

function apiSuccess(data, status = 200) {
  return { status, body: { success: true, data } };
}

function apiFailure(error, status = 500, extra = {}) {
  return { status, body: { success: false, error, ...extra } };
}

const LOGIN_ELEMENT_IDS = [
  "api_id",
  "api_hash",
  "phone",
  "proxy",
  "session_type",
  "session_file",
  "string_session",
  "download_threads",
  "cache_limit_mb",
  "web_token",
];

const DOWNLOAD_ELEMENT_IDS = [
  "downloadTaskList",
  "downloadFileList",
  "downloadFileStatus",
];

const CONFIRM_ELEMENT_IDS = [
  "confirmMessage",
  "confirmOk",
  "confirmCancel",
];

const GALLERY_ELEMENT_IDS = [
  "mediaViewer",
  "viewerTitle",
  "viewerIndex",
  "viewerBody",
  "viewerClose",
  "viewerPrev",
  "viewerNext",
  "viewerDownload",
  "galleryTrigger",
];

const DEFAULT_ELEMENT_IDS = [
  ...LOGIN_ELEMENT_IDS,
  ...DOWNLOAD_ELEMENT_IDS,
  ...CONFIRM_ELEMENT_IDS,
  ...GALLERY_ELEMENT_IDS,
];

function createClassList() {
  const values = new Set();
  return {
    add(...names) { names.forEach((name) => values.add(name)); },
    remove(...names) { names.forEach((name) => values.delete(name)); },
    contains(name) { return values.has(name); },
    toggle(name) {
      if (values.has(name)) {
        values.delete(name);
        return false;
      }
      values.add(name);
      return true;
    },
    toString() { return Array.from(values).join(" "); },
  };
}

function createElementState(initial = {}) {
  const listeners = new Map();
  return {
    value: "",
    placeholder: "",
    innerHTML: "",
    textContent: "",
    style: {},
    hidden: false,
    disabled: false,
    appended: [],
    classList: createClassList(),
    appendChild(item) { this.appended.push(item); },
    insertAdjacentHTML(_position, html) { this.innerHTML += html; },
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    removeEventListener(type, handler) {
      const items = listeners.get(type) || [];
      listeners.set(type, items.filter((item) => item !== handler));
    },
    dispatchEvent(event) {
      const normalized = { target: this, preventDefault() {}, ...event };
      (listeners.get(normalized.type) || []).forEach((handler) => handler(normalized));
    },
    focus() { this.focused = true; },
    ...initial,
  };
}

function routeResponse(value, path, options) {
  try {
    const resolved = typeof value === "function" ? value(path, options) : value;
    if (resolved instanceof Error) return response(apiFailure(resolved.message).body, 500);
    if (resolved && Object.prototype.hasOwnProperty.call(resolved, "status") && Object.prototype.hasOwnProperty.call(resolved, "body")) {
      return response(resolved.body, resolved.status);
    }
    return response(apiSuccess(resolved).body);
  } catch (err) {
    return response(apiFailure(err.message || String(err)).body, 500);
  }
}

function registerElements(elements, ids) {
  ids.forEach((id) => {
    if (!elements.has(id)) elements.set(id, createElementState());
  });
}

function textOf(harness, id) {
  return harness.elements.get(id).textContent;
}

function htmlOf(harness, id) {
  return harness.elements.get(id).innerHTML;
}

function expectHtmlIncludes(harness, id, fragments) {
  const html = htmlOf(harness, id);
  fragments.forEach((fragment) => assert(html.includes(fragment), `expected ${id} to include ${fragment}`));
}

function setFocused(harness, id) {
  harness.context.document.activeElement = harness.elements.get(id);
}

function setOutsideFocus(harness) {
  harness.context.document.activeElement = createElementState({ id: "outside" });
}

function expectFocused(harness, id) {
  assert.strictEqual(harness.context.document.activeElement, harness.elements.get(id), `expected ${id} to be focused`);
}

function expectPreventedKeys(harness, keys) {
  assert.deepStrictEqual(harness.calls.preventDefault, keys);
}

function clickElement(harness, id) {
  harness.elements.get(id).dispatchEvent({ type: "click" });
}

function pressDocumentKey(harness, key, options = {}) {
  harness.context.document.dispatchEvent({
    type: "keydown",
    key,
    shiftKey: Boolean(options.shiftKey),
    preventDefault() { harness.calls.preventDefault.push(options.shiftKey ? `Shift+${key}` : key); },
  });
}

function createHarness({ confirmResult = true, search = "", routes = {} } = {}) {
  const elements = new Map();
  const documentListeners = new Map();
  const calls = { confirm: [], fetch: [], open: [], clipboard: [], toast: [], preventDefault: [], focus: [] };
  registerElements(elements, DEFAULT_ELEMENT_IDS);
  elements.set("confirmOverlay", createElementState({ hidden: true }));
  elements.set("downloadFileMore", createElementState({ style: { display: "none" } }));
  elements.set("toast", createElementState({ appendChild(item) { calls.toast.push(item.textContent); } }));

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
      activeElement: createElementState({ id: "initialActive" }),
      getElementById(id) { return elements.get(id) || null; },
      createElement() { return createElementState({ remove() {} }); },
      querySelectorAll() { return []; },
      addEventListener(type, handler) {
        if (!documentListeners.has(type)) documentListeners.set(type, []);
        documentListeners.get(type).push(handler);
      },
      removeEventListener(type, handler) {
        const items = documentListeners.get(type) || [];
        documentListeners.set(type, items.filter((item) => item !== handler));
      },
      dispatchEvent(event) {
        (documentListeners.get(event.type) || []).forEach((handler) => handler(event));
      },
    },
    io() { return { on() {} }; },
    fetch: async (path, options = {}) => {
      calls.fetch.push({ path, options });
      for (const [prefix, value] of Object.entries(routes)) {
        if (String(path).startsWith(prefix)) {
          return routeResponse(value, path, options);
        }
      }
      if (path === "/api/session/export-token") {
        const body = JSON.parse(options.body || "{}");
        return response(apiSuccess({ export_token: `${body.kind}-token` }).body);
      }
      if (String(path).startsWith("/api/session/string")) {
        return response(apiSuccess({ string_session: "exported-string-session" }).body);
      }
      if (String(path).startsWith("/api/task/")) {
        return response(apiSuccess({ task_id: "task-1" }).body);
      }
      return response(apiSuccess([]).body);
    },
  };
  elements.forEach((element, id) => {
    element.id = id;
    element.focus = function focus() {
      this.focused = true;
      context.document.activeElement = this;
      calls.focus.push(id);
    };
  });
  context.globalThis = context;

  vm.createContext(context);
  vm.runInContext(fs.readFileSync("static/js/app.js", "utf8"), context, { filename: "static/js/app.js" });
  calls.fetch.length = 0;
  calls.toast.length = 0;
  return { context, elements, calls };
}

async function testSensitiveConfirmCancelButtonResolvesFalse() {
  const harness = createHarness();
  const result = harness.context.confirmSensitive("确认取消测试");
  assert.strictEqual(harness.elements.get("confirmOverlay").hidden, false);
  assert(harness.elements.get("confirmOverlay").classList.contains("show"));
  assert.strictEqual(textOf(harness, "confirmMessage"), "确认取消测试");
  expectFocused(harness, "confirmCancel");
  clickElement(harness, "confirmCancel");
  assert.strictEqual(await result, false);
  assert.strictEqual(harness.elements.get("confirmOverlay").hidden, true);
  assert(!harness.elements.get("confirmOverlay").classList.contains("show"));
  assert.deepStrictEqual(harness.calls.confirm, []);
}

async function testSensitiveConfirmOkButtonResolvesTrue() {
  const harness = createHarness();
  const result = harness.context.confirmSensitive("确认继续测试");
  clickElement(harness, "confirmOk");
  assert.strictEqual(await result, true);
  assert.strictEqual(harness.elements.get("confirmOverlay").hidden, true);
  assert.deepStrictEqual(harness.calls.confirm, []);
}

async function testSensitiveConfirmFocusTrapCyclesWithinDialog() {
  const harness = createHarness();
  const result = harness.context.confirmSensitive("焦点循环测试");

  setFocused(harness, "confirmOk");
  pressDocumentKey(harness, "Tab");
  expectFocused(harness, "confirmCancel");

  pressDocumentKey(harness, "Tab", { shiftKey: true });
  expectFocused(harness, "confirmOk");

  setOutsideFocus(harness);
  pressDocumentKey(harness, "Tab");
  expectFocused(harness, "confirmCancel");

  expectPreventedKeys(harness, ["Tab", "Shift+Tab", "Tab"]);
  clickElement(harness, "confirmCancel");
  assert.strictEqual(await result, false);
}

async function testSensitiveConfirmEscapeCancels() {
  const harness = createHarness();
  const result = harness.context.confirmSensitive("按 Esc 取消");
  pressDocumentKey(harness, "Escape");
  assert.strictEqual(await result, false);
  assert.strictEqual(harness.elements.get("confirmOverlay").hidden, true);
  expectPreventedKeys(harness, ["Escape"]);
}

async function testSensitiveConfirmReentrantCancelsPrevious() {
  const harness = createHarness();
  const first = harness.context.confirmSensitive("第一个确认");
  const second = harness.context.confirmSensitive("第二个确认");
  assert.strictEqual(await first, false);
  assert.strictEqual(textOf(harness, "confirmMessage"), "第二个确认");
  clickElement(harness, "confirmOk");
  assert.strictEqual(await second, true);
}

async function testGalleryKeyboardNavigationAndFocusRestore() {
  const harness = createHarness();
  setFocused(harness, "galleryTrigger");

  harness.context.openGallery([
    { msgId: 1, url: "/media/one.jpg", mime: "image/jpeg", label: "第一张" },
    { msgId: 2, url: "/media/two.mp4", mime: "video/mp4", label: "第二段" },
  ], 0);

  assert(harness.elements.get("mediaViewer").classList.contains("show"));
  expectFocused(harness, "viewerClose");
  assert.strictEqual(textOf(harness, "viewerTitle"), "第一张");
  assert.strictEqual(textOf(harness, "viewerIndex"), "1 / 2");
  expectHtmlIncludes(harness, "viewerBody", ["/media/one.jpg"]);

  pressDocumentKey(harness, "ArrowRight");
  assert.strictEqual(textOf(harness, "viewerTitle"), "第二段");
  assert.strictEqual(textOf(harness, "viewerIndex"), "2 / 2");
  expectHtmlIncludes(harness, "viewerBody", ["/media/two.mp4"]);

  pressDocumentKey(harness, "ArrowLeft");
  assert.strictEqual(textOf(harness, "viewerTitle"), "第一张");
  assert.strictEqual(textOf(harness, "viewerIndex"), "1 / 2");

  pressDocumentKey(harness, "Escape");
  assert(!harness.elements.get("mediaViewer").classList.contains("show"));
  expectFocused(harness, "galleryTrigger");
  expectPreventedKeys(harness, ["ArrowRight", "ArrowLeft", "Escape"]);
}

async function testGalleryFocusTrapCyclesWithinViewerControls() {
  const harness = createHarness();

  harness.context.bindGalleryEvents();
  harness.context.openGallery([
    { msgId: 1, url: "/media/one.jpg", mime: "image/jpeg", label: "第一张" },
  ], 0);

  setFocused(harness, "viewerNext");
  pressDocumentKey(harness, "Tab");
  expectFocused(harness, "viewerClose");

  pressDocumentKey(harness, "Tab", { shiftKey: true });
  expectFocused(harness, "viewerNext");

  setOutsideFocus(harness);
  pressDocumentKey(harness, "Tab");
  expectFocused(harness, "viewerClose");

  expectPreventedKeys(harness, ["Tab", "Shift+Tab", "Tab"]);
  clickElement(harness, "viewerClose");
  assert(!harness.elements.get("mediaViewer").classList.contains("show"));
}

async function testGalleryKeyboardIgnoresKeysWhileConfirmIsOpen() {
  const harness = createHarness();
  harness.context.openGallery([
    { msgId: 1, url: "/media/one.jpg", mime: "image/jpeg", label: "第一张" },
    { msgId: 2, url: "/media/two.jpg", mime: "image/jpeg", label: "第二张" },
  ], 0);
  const confirmResult = harness.context.confirmSensitive("确认覆盖查看器");

  pressDocumentKey(harness, "ArrowRight");
  assert.strictEqual(textOf(harness, "viewerTitle"), "第一张");
  pressDocumentKey(harness, "Escape");
  assert(harness.elements.get("mediaViewer").classList.contains("show"));
  assert.strictEqual(await confirmResult, false);

  pressDocumentKey(harness, "Escape");
  assert(!harness.elements.get("mediaViewer").classList.contains("show"));
}

async function testApiCopiesErrorIdAndKeepsMessageActionable() {
  const harness = createHarness({
    routes: {
      "/api/broken": apiFailure("内部错误", 500, { error_id: "err-phase10" }),
    },
  });

  await assert.rejects(
    () => harness.context.api("/api/broken"),
    (err) => {
      assert.strictEqual(err.message, "内部错误（错误 ID: err-phase10）");
      assert.strictEqual(err.errorId, "err-phase10");
      return true;
    },
  );
  assert.deepStrictEqual(harness.calls.clipboard, ["err-phase10"]);
}

async function testApiRedirectsUnauthorizedToAuthPage() {
  const harness = createHarness({
    search: "?token=web-token",
    routes: {
      "/api/protected": apiFailure("未授权", 401),
    },
  });

  await assert.rejects(
    () => harness.context.api("/api/protected"),
    /需要 Web Token/,
  );
  assert.strictEqual(harness.context.location.href, "/auth?next=%2Flogin%3Ftoken%3Dweb-token");
}

async function testLoadLoginPageUsesRedactedConfigPlaceholders() {
  const harness = createHarness({
    routes: {
      "/api/config": {
        api_id: 12345,
        api_hash_saved: true,
        phone: "+8613800000000",
        proxy: "",
        proxy_redacted: true,
        session_type: "string",
        session_file_saved: true,
        string_session_saved: true,
        download_threads: 8,
        cache_limit_mb: 2048,
        web_token_saved: true,
      },
    },
  });

  await harness.context.loadLoginPage();

  assert.strictEqual(harness.elements.get("api_id").value, 12345);
  assert.strictEqual(harness.elements.get("phone").value, "+8613800000000");
  assert.strictEqual(harness.elements.get("session_type").value, "string");
  assert.strictEqual(harness.elements.get("download_threads").value, 8);
  assert.strictEqual(harness.elements.get("cache_limit_mb").value, 2048);
  assert.strictEqual(harness.elements.get("api_hash").value, "");
  assert.strictEqual(harness.elements.get("api_hash").placeholder, "已保存，留空沿用当前 api_hash");
  assert.strictEqual(harness.elements.get("proxy").placeholder, "已保存含凭据代理，留空沿用");
  assert.strictEqual(harness.elements.get("session_file").value, "");
  assert.strictEqual(harness.elements.get("session_file").placeholder, "已保存，留空沿用当前 .session");
  assert.strictEqual(harness.elements.get("string_session").value, "");
  assert.strictEqual(harness.elements.get("string_session").placeholder, "已保存，留空沿用当前 StringSession");
  assert.strictEqual(harness.elements.get("web_token").value, "");
  assert.strictEqual(harness.elements.get("web_token").placeholder, "已保存，留空不修改 Web Token");
}

async function testCancelingStringExportDoesNotRequestToken() {
  const { context, calls, elements } = createHarness();
  const action = context.exportStringSession();
  assert.strictEqual(elements.get("confirmMessage").textContent, "确认导出 StringSession？导出的文本可直接登录此 Telegram 账号。");
  clickElement({ elements }, "confirmCancel");
  await action;
  assert.strictEqual(calls.confirm.length, 0);
  assert.deepStrictEqual(calls.fetch, []);
}

async function testStringExportRequestsOneTimeToken() {
  const { context, elements, calls } = createHarness();
  const action = context.exportStringSession();
  clickElement({ elements }, "confirmOk");
  await action;
  assert.strictEqual(calls.confirm.length, 0);
  assert.strictEqual(calls.fetch[0].path, "/api/session/export-token");
  assert.deepStrictEqual(JSON.parse(calls.fetch[0].options.body), { kind: "string" });
  assert.strictEqual(calls.fetch[1].path, "/api/session/string?export_token=string-token");
  assert.strictEqual(elements.get("string_session").value, "exported-string-session");
  assert.deepStrictEqual(calls.clipboard, ["exported-string-session"]);
}

async function testFileExportOpensTokenizedDownloadUrl() {
  const { context, elements, calls } = createHarness({ search: "?token=web-token" });
  const action = context.exportSessionFile();
  clickElement({ elements }, "confirmOk");
  await action;
  assert.strictEqual(calls.fetch[0].path, "/api/session/export-token");
  assert.deepStrictEqual(JSON.parse(calls.fetch[0].options.body), { kind: "file" });
  assert.strictEqual(calls.open.length, 1);
  assert.strictEqual(calls.open[0].url, "/api/session/file?export_token=file-token&token=web-token");
}

async function testTaskDeleteConfirmationControlsRequest() {
  let harness = createHarness();
  let action = harness.context.taskDelete("task-1", "running");
  assert.strictEqual(textOf(harness, "confirmMessage"), "确认取消这个下载/预览任务？");
  clickElement(harness, "confirmCancel");
  await action;
  assert.strictEqual(harness.calls.confirm.length, 0);
  assert.deepStrictEqual(harness.calls.fetch, []);

  harness = createHarness();
  harness.context.loadDownloadTasks = async () => {};
  harness.context.loadDownloadFiles = async () => {};
  action = harness.context.taskDelete("task-1", "done");
  assert.strictEqual(textOf(harness, "confirmMessage"), "确认移除这条任务记录？");
  clickElement(harness, "confirmOk");
  await action;
  assert.strictEqual(harness.calls.fetch[0].path, "/api/task/task-1");
  assert.strictEqual(harness.calls.fetch[0].options.method, "DELETE");
}

async function testDownloadTasksRenderControlsAndErrors() {
  const harness = createHarness({
    routes: {
      "/api/tasks": [
        { id: "run-1", kind: "download_media", status: "running", progress: 25, downloaded_text: "1 MB", total_text: "4 MB", speed_text: "2 KB/s" },
        { id: "done-1", kind: "prepare_media", status: "done", progress: 100, downloaded_text: "2 MB", total_text: "2 MB", speed_text: "0 B/s" },
      ],
    },
  });
  await harness.context.loadDownloadTasks();
  expectHtmlIncludes(harness, "downloadTaskList", [
    "download_media · running",
    "taskPause('run-1')",
    "取消",
    "prepare_media · done",
    "移除记录",
  ]);

  const failing = createHarness({ routes: { "/api/tasks": new Error("任务接口失败") } });
  await failing.context.loadDownloadTasks();
  expectHtmlIncludes(failing, "downloadTaskList", ["任务接口失败"]);
}

async function testDownloadFilesPaginationAndRendering() {
  const harness = createHarness({
    routes: {
      "/api/download-files": (path) => {
        assert(path.includes("limit=30"));
        if (path.includes("offset=0")) {
          return {
            items: [
              { name: "photo.jpg", kind: "picture", url: "/pictures/photo.jpg", size_text: "10 KB", is_image: true },
              { name: "clip.mp4", kind: "download", url: "/download-file/clip.mp4", size: 2048, is_video: true },
            ],
            total: 3,
            has_more: true,
          };
        }
        return {
          items: [{ name: "doc.txt", kind: "download", url: "/download-file/doc.txt", size: 12 }],
          total: 3,
          has_more: false,
        };
      },
    },
  });

  await harness.context.loadDownloadFiles(true);
  assert.strictEqual(harness.calls.fetch[0].path, "/api/download-files?limit=30&offset=0");
  expectHtmlIncludes(harness, "downloadFileList", ["photo.jpg", "clip.mp4"]);
  assert.strictEqual(textOf(harness, "downloadFileStatus"), "已显示 2 / 3");
  assert.strictEqual(harness.elements.get("downloadFileMore").style.display, "inline-flex");

  await harness.context.loadDownloadFiles(false);
  assert.strictEqual(harness.calls.fetch[1].path, "/api/download-files?limit=30&offset=2");
  expectHtmlIncludes(harness, "downloadFileList", ["doc.txt"]);
  assert.strictEqual(textOf(harness, "downloadFileStatus"), "已显示 3 / 3");
  assert.strictEqual(harness.elements.get("downloadFileMore").style.display, "none");
}

async function testDownloadFilesErrorShowsToastAfterExistingPage() {
  const harness = createHarness({
    routes: {
      "/api/download-files": (path) => {
        if (path.includes("offset=0")) {
          return { items: [{ name: "first.bin", kind: "download", url: "/download-file/first.bin", size: 1 }], total: 2, has_more: true };
        }
        return apiFailure("下一页失败", 500);
      },
    },
  });

  await harness.context.loadDownloadFiles(true);
  await harness.context.loadDownloadFiles(false);
  assert(harness.calls.toast.includes("下一页失败"));
  expectHtmlIncludes(harness, "downloadFileList", ["first.bin"]);
}

const TEST_GROUPS = [
  {
    name: "confirm dialog",
    tests: [
      testSensitiveConfirmCancelButtonResolvesFalse,
      testSensitiveConfirmOkButtonResolvesTrue,
      testSensitiveConfirmFocusTrapCyclesWithinDialog,
      testSensitiveConfirmEscapeCancels,
      testSensitiveConfirmReentrantCancelsPrevious,
    ],
  },
  {
    name: "gallery viewer",
    tests: [
      testGalleryKeyboardNavigationAndFocusRestore,
      testGalleryFocusTrapCyclesWithinViewerControls,
      testGalleryKeyboardIgnoresKeysWhileConfirmIsOpen,
    ],
  },
  {
    name: "api and login",
    tests: [
      testApiCopiesErrorIdAndKeepsMessageActionable,
      testApiRedirectsUnauthorizedToAuthPage,
      testLoadLoginPageUsesRedactedConfigPlaceholders,
    ],
  },
  {
    name: "session and task confirmations",
    tests: [
      testCancelingStringExportDoesNotRequestToken,
      testStringExportRequestsOneTimeToken,
      testFileExportOpensTokenizedDownloadUrl,
      testTaskDeleteConfirmationControlsRequest,
    ],
  },
  {
    name: "downloads",
    tests: [
      testDownloadTasksRenderControlsAndErrors,
      testDownloadFilesPaginationAndRendering,
      testDownloadFilesErrorShowsToastAfterExistingPage,
    ],
  },
];

async function runTestGroups(groups) {
  for (const group of groups) {
    for (const test of group.tests) {
      try {
        await test();
      } catch (err) {
        if (err && typeof err === "object") {
          err.message = `${group.name} / ${test.name}: ${err.message}`;
        }
        throw err;
      }
    }
  }
}

async function main() {
  await runTestGroups(TEST_GROUPS);
  console.log("frontend smoke passed");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
