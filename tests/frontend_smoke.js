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

function createElementState(initial = {}) {
  return {
    value: "",
    placeholder: "",
    innerHTML: "",
    textContent: "",
    style: {},
    disabled: false,
    appended: [],
    appendChild(item) { this.appended.push(item); },
    insertAdjacentHTML(_position, html) { this.innerHTML += html; },
    ...initial,
  };
}

function createHarness({ confirmResult = true, search = "", routes = {} } = {}) {
  const elements = new Map();
  const calls = { confirm: [], fetch: [], open: [], clipboard: [], toast: [] };
  elements.set("string_session", createElementState());
  elements.set("downloadTaskList", createElementState());
  elements.set("downloadFileList", createElementState());
  elements.set("downloadFileStatus", createElementState());
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
      getElementById(id) { return elements.get(id) || null; },
      createElement() { return { className: "", textContent: "", remove() {} }; },
      querySelectorAll() { return []; },
    },
    io() { return { on() {} }; },
    fetch: async (path, options = {}) => {
      calls.fetch.push({ path, options });
      for (const [prefix, value] of Object.entries(routes)) {
        if (String(path).startsWith(prefix)) {
          if (value instanceof Error) {
            return response({ success: false, error: value.message }, 500);
          }
          return response({ success: true, data: typeof value === "function" ? value(path, options) : value });
        }
      }
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
  const html = harness.elements.get("downloadTaskList").innerHTML;
  assert(html.includes("download_media · running"));
  assert(html.includes("taskPause('run-1')"));
  assert(html.includes("取消"));
  assert(html.includes("prepare_media · done"));
  assert(html.includes("移除记录"));

  const failing = createHarness({ routes: { "/api/tasks": new Error("任务接口失败") } });
  await failing.context.loadDownloadTasks();
  assert(failing.elements.get("downloadTaskList").innerHTML.includes("任务接口失败"));
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
  assert(harness.elements.get("downloadFileList").innerHTML.includes("photo.jpg"));
  assert(harness.elements.get("downloadFileList").innerHTML.includes("clip.mp4"));
  assert.strictEqual(harness.elements.get("downloadFileStatus").textContent, "已显示 2 / 3");
  assert.strictEqual(harness.elements.get("downloadFileMore").style.display, "inline-flex");

  await harness.context.loadDownloadFiles(false);
  assert.strictEqual(harness.calls.fetch[1].path, "/api/download-files?limit=30&offset=2");
  assert(harness.elements.get("downloadFileList").innerHTML.includes("doc.txt"));
  assert.strictEqual(harness.elements.get("downloadFileStatus").textContent, "已显示 3 / 3");
  assert.strictEqual(harness.elements.get("downloadFileMore").style.display, "none");
}

async function testDownloadFilesErrorShowsToastAfterExistingPage() {
  const harness = createHarness({
    routes: {
      "/api/download-files": (path) => {
        if (path.includes("offset=0")) {
          return { items: [{ name: "first.bin", kind: "download", url: "/download-file/first.bin", size: 1 }], total: 2, has_more: true };
        }
        throw new Error("下一页失败");
      },
    },
  });
  harness.context.fetch = async (path, options = {}) => {
    harness.calls.fetch.push({ path, options });
    if (String(path).startsWith("/api/download-files") && String(path).includes("offset=0")) {
      return response({ success: true, data: { items: [{ name: "first.bin", kind: "download", url: "/download-file/first.bin", size: 1 }], total: 2, has_more: true } });
    }
    if (String(path).startsWith("/api/download-files")) {
      return response({ success: false, error: "下一页失败" }, 500);
    }
    return response({ success: true, data: [] });
  };

  await harness.context.loadDownloadFiles(true);
  await harness.context.loadDownloadFiles(false);
  assert(harness.calls.toast.includes("下一页失败"));
  assert(harness.elements.get("downloadFileList").innerHTML.includes("first.bin"));
}

async function main() {
  await testCancelingStringExportDoesNotRequestToken();
  await testStringExportRequestsOneTimeToken();
  await testFileExportOpensTokenizedDownloadUrl();
  await testTaskDeleteConfirmationControlsRequest();
  await testDownloadTasksRenderControlsAndErrors();
  await testDownloadFilesPaginationAndRendering();
  await testDownloadFilesErrorShowsToastAfterExistingPage();
  console.log("frontend smoke passed");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
