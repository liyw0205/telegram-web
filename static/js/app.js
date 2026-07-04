let DIALOGS = [];
let CURRENT_PEER = "";
let OLDEST_MSG_ID = 0;
let downloadsTimer = null;
let downloadFilesOffset = 0;
let downloadFilesHasMore = false;
let downloadFilesLoading = false;
const DOWNLOAD_FILE_LIMIT = 30;

let GALLERY_ITEMS = [];
let GALLERY_INDEX = 0;
let galleryLastFocus = null;
let galleryKeydownBound = false;
let galleryEventsBound = false;
const SHOW_META = false;
let pendingConfirm = null;
let confirmDialogBound = false;
let confirmLastFocus = null;

const THUMB_CACHE = new Map(); // key: `${peer}:${msgId}` -> url|null
const URL_TOKEN = new URLSearchParams(location.search).get("token") || "";
const socket = io({ auth: URL_TOKEN ? { token: URL_TOKEN } : {} });
socket.on("new_message", msg => { if (msg && CURRENT_PEER) appendLiveMessage(msg); });

function $(id){ return document.getElementById(id); }
function escapeHtml(s){ return String(s || "").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }

function toast(text){
  const box = $("toast"); if (!box) return alert(text);
  const item = document.createElement("div");
  item.className = "toast-item"; item.textContent = text;
  if (typeof item.setAttribute === "function") item.setAttribute("role", "status");
  box.appendChild(item); setTimeout(() => item.remove(), 2400);
}

function bindConfirmDialog(){
  if (confirmDialogBound) return;
  const overlay = $("confirmOverlay"), ok = $("confirmOk"), cancel = $("confirmCancel");
  if (!overlay || !ok || !cancel) return;
  confirmDialogBound = true;
  ok.addEventListener("click", () => closeSensitiveConfirm(true));
  cancel.addEventListener("click", () => closeSensitiveConfirm(false));
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeSensitiveConfirm(false);
  });
}

function getConfirmFocusables(){
  return [$("confirmCancel"), $("confirmOk")].filter(el => el && !el.disabled && typeof el.focus === "function");
}

function handleConfirmKeydown(event){
  if (!pendingConfirm) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeSensitiveConfirm(false);
    return;
  }
  if (event.key !== "Tab") return;
  const focusables = getConfirmFocusables();
  if (!focusables.length) {
    event.preventDefault();
    return;
  }
  const first = focusables[0], last = focusables[focusables.length - 1];
  const current = document.activeElement;
  if (event.shiftKey && (current === first || !focusables.includes(current))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (current === last || !focusables.includes(current))) {
    event.preventDefault();
    first.focus();
  }
}

function closeSensitiveConfirm(result){
  if (!pendingConfirm) return;
  const current = pendingConfirm;
  pendingConfirm = null;
  const overlay = $("confirmOverlay");
  if (overlay) {
    overlay.classList.remove("show");
    overlay.hidden = true;
  }
  document.removeEventListener("keydown", handleConfirmKeydown);
  current.resolve(result);
  if (confirmLastFocus && typeof confirmLastFocus.focus === "function") confirmLastFocus.focus();
  confirmLastFocus = null;
}

function confirmSensitive(message){
  const overlay = $("confirmOverlay"), text = $("confirmMessage"), ok = $("confirmOk"), cancel = $("confirmCancel");
  if (!overlay || !text || !ok || !cancel) return Promise.resolve(confirm(message));
  bindConfirmDialog();
  if (pendingConfirm) closeSensitiveConfirm(false);
  text.textContent = message;
  overlay.hidden = false;
  overlay.classList.add("show");
  confirmLastFocus = document.activeElement || null;
  document.addEventListener("keydown", handleConfirmKeydown);
  setTimeout(() => cancel.focus(), 0);
  return new Promise((resolve) => { pendingConfirm = { resolve }; });
}

function withQuery(path, params){
  const url = new URL(path, location.origin);
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, value);
  });
  return url.pathname + url.search;
}

async function createSessionExportToken(kind){
  return await api("/api/session/export-token", { method:"POST", body: JSON.stringify({ kind }) });
}

async function api(path, options = {}){
  const isForm = options.body instanceof FormData;
  const res = await fetch(path, {
    ...options,
    headers: isForm ? (options.headers || {}) : { "Content-Type":"application/json", ...(options.headers || {}) }
  });
  const data = await res.json().catch(() => ({}));
  if (res.status === 401) {
    location.href = "/auth?next=" + encodeURIComponent(location.pathname + location.search);
    throw new Error("需要 Web Token");
  }
  if (!res.ok || data.success === false) {
    const message = data.error || data.message || "请求失败";
    if (data.error_id) {
      if (navigator.clipboard) navigator.clipboard.writeText(data.error_id).catch(() => {});
      const err = new Error(`${message}（错误 ID: ${data.error_id}）`);
      err.errorId = data.error_id;
      throw err;
    }
    throw new Error(message);
  }
  return data.data;
}

function formatSize(n){
  n = Number(n || 0);
  const u = ["B","KB","MB","GB","TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return i === 0 ? `${Math.round(n)} ${u[i]}` : `${n.toFixed(2)} ${u[i]}`;
}

function boolText(value){ return value ? "是" : "否"; }
function authSourceText(value){ return value === "environment" ? "环境变量" : value === "config" ? "配置文件" : "未启用"; }
function runtimeScopeText(runtime){ return runtime && runtime.loopback ? "本机监听" : "对外监听"; }
function runtimePortText(runtime){ return runtime && runtime.port_valid ? String(runtime.port) : "无效"; }
function diagnosticsValueText(value){ return typeof value === "boolean" ? boolText(value) : String(value ?? "-"); }
function setAriaBusy(target, busy){
  const el = typeof target === "string" ? $(target) : target;
  if (el && typeof el.setAttribute === "function") el.setAttribute("aria-busy", busy ? "true" : "false");
}
function setDiagnosticsState(state){
  const summary = $("diagnosticsSummary");
  if (summary) {
    summary.classList.remove("ok", "warn");
    if (state === "ok") summary.classList.add("ok");
    if (state === "error") summary.classList.add("warn");
  }
  const busy = state === "loading";
  ["diagnosticsSummary", "diagnosticsConfig", "diagnosticsAuth", "diagnosticsRuntime", "diagnosticsPaths"].forEach(id => setAriaBusy(id, busy));
}
function renderDiagnosticsValue(value, isOk = null){
  const text = diagnosticsValueText(value);
  const cls = isOk === null ? "" : (isOk ? " ok" : " warn");
  return `<span class="diagnostics-value${cls}">${escapeHtml(text)}</span>`;
}
function renderDiagnosticsRows(id, rows){
  const box = $(id); if (!box) return;
  box.innerHTML = rows.map(row => {
    const label = String(row[0] ?? "");
    const value = diagnosticsValueText(row[1]);
    return `<div class="diagnostics-row" role="listitem" aria-label="${escapeHtml(label)}：${escapeHtml(value)}"><span class="diagnostics-label">${escapeHtml(label)}</span>${renderDiagnosticsValue(row[1], row[2])}</div>`;
  }).join("");
}
async function loadDiagnosticsPage(){
  const summary = $("diagnosticsSummary");
  setDiagnosticsState("loading");
  if (summary) summary.textContent = "加载中...";
  try{
    const d = await api("/api/diagnostics");
    const cfg = d.config || {}, auth = d.web_auth || {}, runtime = d.runtime || {}, paths = d.paths || {};
    if (summary) summary.textContent = `${auth.enabled ? "Web Token 已启用" : "Web Token 未启用"} · ${authSourceText(auth.source)} · ${runtimeScopeText(runtime)} · ${runtimePortText(runtime)}`;
    renderDiagnosticsRows("diagnosticsConfig", [
      ["配置文件", cfg.exists, cfg.exists],
      ["api_id", cfg.api_id_configured, cfg.api_id_configured],
      ["api_hash", cfg.api_hash_saved, cfg.api_hash_saved],
      ["手机号", cfg.phone_configured, cfg.phone_configured],
      ["代理", cfg.proxy_saved ? (cfg.proxy_redacted ? "已保存，含凭据" : "已保存") : "未保存", null],
      ["Session 类型", cfg.session_type || "file", null],
      [".session 已保存", cfg.session_file_saved, cfg.session_file_saved],
      [".session 文件存在", cfg.session_file_exists, cfg.session_file_exists],
      ["StringSession", cfg.string_session_saved, cfg.string_session_saved],
      ["下载线程", cfg.download_threads ?? "-", null],
      ["缓存上限(MB)", cfg.cache_limit_mb ?? "-", null],
    ]);
    renderDiagnosticsRows("diagnosticsAuth", [
      ["Web Token", auth.enabled, auth.enabled],
      ["Token 来源", authSourceText(auth.source), null],
      ["环境变量 Token", auth.env_token_set, auth.env_token_set],
      ["配置文件 Token", auth.config_token_saved, auth.config_token_saved],
    ]);
    renderDiagnosticsRows("diagnosticsRuntime", [
      ["监听范围", runtime.loopback ? "本机" : "对外", runtime.loopback || auth.enabled],
      ["Port", runtimePortText(runtime), runtime.port_valid],
      ["对外监听需 Token", runtime.external_bind_requires_token, !runtime.external_bind_requires_token || auth.enabled],
    ]);
    renderDiagnosticsRows("diagnosticsPaths", [
      ["data", paths.data_dir_exists, paths.data_dir_exists],
      ["Download", paths.download_dir_exists, paths.download_dir_exists],
      ["Pictures", paths.pictures_dir_exists, paths.pictures_dir_exists],
      ["media-cache", paths.cache_dir_exists, paths.cache_dir_exists],
      ["uploads", paths.upload_dir_exists, paths.upload_dir_exists],
      ["task-history", paths.task_history_exists, null],
    ]);
    setDiagnosticsState("ok");
  } catch(e){
    if (summary) summary.textContent = e.message;
    ["diagnosticsConfig", "diagnosticsAuth", "diagnosticsRuntime", "diagnosticsPaths"].forEach(id => {
      const box = $(id); if (box) box.innerHTML = "";
    });
    setDiagnosticsState("error");
    toast(e.message);
  }
}

function toggleFold(id){ $(id)?.classList.toggle("show"); }
function toggleComposer(id){
  document.querySelectorAll(".composer-panel").forEach(el => {
    const show = el.id === id ? el.classList.toggle("show") : false;
    if (el.id !== id) el.classList.remove("show");
    if (typeof el.setAttribute === "function") el.setAttribute("aria-hidden", show ? "false" : "true");
  });
  document.querySelectorAll("[data-composer-target]").forEach(button => {
    const expanded = button.getAttribute("data-composer-target") === id && $(id)?.classList.contains("show");
    if (typeof button.setAttribute === "function") button.setAttribute("aria-expanded", expanded ? "true" : "false");
  });
}

/* 安全 Markdown */
function renderMarkdownSafe(raw){
  let s = escapeHtml(raw || "");
  s = s.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
  s = s.replace(/\*(.+?)\*/g, "<i>$1</i>");
  s = s.replace(/`([^`]+?)`/g, "<code>$1</code>");
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/\n/g, "<br>");
  return s;
}

async function refreshStatus(){
  const top = $("topStatus");
  setAriaBusy(top, true);
  try{
    const d = await api("/api/status");
    if (!top) return;
    if (d.authorized) {
      const me = d.me || {};
      top.textContent = "已登录：" + (me.username || me.first_name || me.phone || me.id);
    } else if (d.connected) top.textContent = "已连接，未授权";
    else top.textContent = "未连接";
  } catch {
    if (top) top.textContent = "状态异常";
  } finally {
    setAriaBusy(top, false);
  }
}

/* 登录 */
async function loadLoginPage(){
  try{
    const cfg = await api("/api/config");
    $("api_id").value = cfg.api_id || "";
    $("api_hash").value = "";
    $("api_hash").placeholder = cfg.api_hash_saved ? "已保存，留空沿用当前 api_hash" : "api_hash";
    $("phone").value = cfg.phone || "";
    $("proxy").value = cfg.proxy || "";
    $("proxy").placeholder = cfg.proxy_redacted ? "已保存含凭据代理，留空沿用" : "socks5://127.0.0.1:7890";
    $("session_type").value = cfg.session_type || "file";
    $("session_file").value = "";
    $("session_file").placeholder = cfg.session_file_saved ? "已保存，留空沿用当前 .session 文件" : "telegram.session";
    $("string_session").value = "";
    $("string_session").placeholder = cfg.string_session_saved ? "已保存，留空沿用当前 StringSession" : "导入或登录后自动保存";
    $("download_threads").value = cfg.download_threads || 16;
    $("cache_limit_mb").value = cfg.cache_limit_mb || 1024;
    $("web_token").value = "";
    $("web_token").placeholder = cfg.web_token_saved ? "已保存，留空不修改 Web Token" : "可选，8-256 字符，不能含空白";
  } catch(e){ toast(e.message); }
}
function loginConfigPayload(includeWebToken = false){
  const payload = {};
  const apiId = $("api_id").value.trim();
  const apiHash = $("api_hash").value.trim();
  const phone = $("phone").value.trim();
  const proxy = $("proxy").value.trim();
  const sessionType = $("session_type")?.value || "file";
  const sessionFile = $("session_file")?.value.trim();
  const stringSession = $("string_session")?.value.trim();
  const threads = $("download_threads").value.trim();
  const cacheLimit = $("cache_limit_mb").value.trim();
  if (apiId) payload.api_id = Number(apiId);
  if (apiHash) payload.api_hash = apiHash;
  if (phone) payload.phone = phone;
  if (proxy) payload.proxy = proxy;
  if (sessionType) payload.session_type = sessionType;
  if (sessionFile) payload.session_file = sessionFile;
  if (stringSession) payload.string_session = stringSession;
  if (threads) payload.download_threads = Number(threads);
  if (cacheLimit) payload.cache_limit_mb = Number(cacheLimit);
  if (includeWebToken && $("web_token").value.trim()) payload.web_token = $("web_token").value.trim();
  return payload;
}
async function saveLoginConfig(){
  try{
    await api("/api/config", { method:"POST", body: JSON.stringify(loginConfigPayload(true)) });
    toast("配置已保存");
    loadLoginPage();
  } catch(e){ toast(e.message); }
}
async function startLogin(){
  try{
    const d = await api("/api/login/start", {
      method:"POST",
      body: JSON.stringify(loginConfigPayload(false))
    });
    toast(d.message || "已处理"); refreshStatus();
  } catch(e){ toast(e.message); }
}
async function submitCode(){
  const code = prompt("请输入验证码"); if (!code) return;
  try{
    const d = await api("/api/login/code", { method:"POST", body: JSON.stringify({ code }) });
    toast(d.need_password ? "需要两步验证密码" : "登录成功");
    refreshStatus();
  } catch(e){ toast(e.message); }
}
async function submitPassword(){
  const password = prompt("请输入两步验证密码"); if (!password) return;
  try{ await api("/api/login/password", { method:"POST", body: JSON.stringify({ password }) }); toast("登录成功"); refreshStatus(); }
  catch(e){ toast(e.message); }
}
async function logoutTelegram(){
  if (!(await confirmSensitive("确认退出 Telegram 登录？这会断开当前账号会话。"))) return;
  try{ await api("/api/logout", { method:"POST", body:"{}" }); toast("已退出登录"); refreshStatus(); }
  catch(e){ toast(e.message); }
}
async function importStringSession(){
  const value = $("string_session")?.value.trim();
  if (!value) return toast("请先粘贴 StringSession");
  if (!(await confirmSensitive("确认导入 StringSession？当前客户端会重置并切换到导入的会话。"))) return;
  try{
    await api("/api/session/string", { method:"POST", body: JSON.stringify({ string_session: value }) });
    $("string_session").value = "";
    toast("StringSession 已导入");
    loadLoginPage(); refreshStatus();
  } catch(e){ toast(e.message); }
}
async function exportStringSession(){
  if (!(await confirmSensitive("确认导出 StringSession？导出的文本可直接登录此 Telegram 账号。"))) return;
  try{
    const token = await createSessionExportToken("string");
    const data = await api(withQuery("/api/session/string", { export_token: token.export_token }));
    const value = data.string_session || "";
    if (!value) return toast("当前没有 StringSession");
    $("string_session").value = value;
    if (navigator.clipboard) await navigator.clipboard.writeText(value).catch(() => {});
    toast("StringSession 已填入文本框");
  } catch(e){ toast(e.message); }
}
async function importSessionFile(){
  const file = $("sessionFileInput")?.files?.[0];
  if (!file) return toast("请选择 .session 文件");
  if (!(await confirmSensitive("确认导入 .session 文件？当前客户端会重置并切换到导入的会话。"))) return;
  const fd = new FormData();
  fd.append("file", file);
  try{
    await api("/api/session/file", { method:"POST", body: fd });
    $("sessionFileInput").value = "";
    toast(".session 文件已导入");
    loadLoginPage(); refreshStatus();
  } catch(e){ toast(e.message); }
}
async function exportSessionFile(){
  if (!(await confirmSensitive("确认导出 .session 文件？该文件可直接登录此 Telegram 账号。"))) return;
  try{
    const token = await createSessionExportToken("file");
    window.open(withQuery("/api/session/file", { export_token: token.export_token, token: URL_TOKEN }), "_blank", "noopener");
  } catch(e){ toast(e.message); }
}

/* 会话 */
async function initDialogListPage(){ refreshStatus(); await loadDialogs(); }
async function loadDialogs(){
  const box = $("dialogList"); if (!box) return;
  setAriaBusy(box, true);
  box.innerHTML = `<div class="empty" role="listitem">加载中...</div>`;
  try{
    DIALOGS = await api("/api/dialogs?limit=120");
    renderDialogs(DIALOGS);
  } catch(e){
    box.innerHTML = `<div class="empty" role="listitem">${escapeHtml(e.message)}</div>`;
  } finally {
    setAriaBusy(box, false);
  }
}
function dialogTypeText(d){
  return d.is_channel ? "频道" : d.is_group ? "群组" : "私聊";
}
function dialogAriaLabel(d){
  const name = d.name || d.peer || "未命名会话";
  const username = d.username ? `，用户名 @${d.username}` : "";
  const unread = d.unread_count ? `，${d.unread_count} 条未读` : "";
  return `${name}，${dialogTypeText(d)}${username}${unread}`;
}
function renderDialogs(list){
  const box = $("dialogList"); if (!box) return;
  box.innerHTML = "";
  if (!list.length) return box.innerHTML = `<div class="empty" role="listitem">暂无会话</div>`;
  list.forEach(d => {
    const first = String(d.name || "?").trim().slice(0, 1).toUpperCase();
    const a = document.createElement("a");
    a.className = "dialog-item";
    a.href = "/chat/" + encodeURIComponent(d.peer);
    a.setAttribute("role", "listitem");
    a.setAttribute("aria-label", dialogAriaLabel(d));
    a.innerHTML = `<div class="avatar">${escapeHtml(first)}</div><div style="min-width:0"><div class="dialog-name">${escapeHtml(d.name || d.peer)}</div><div class="dialog-meta">${d.username ? "@"+escapeHtml(d.username)+" · " : ""}${dialogTypeText(d)}</div></div>${d.unread_count ? `<div class="unread-badge" aria-label="未读 ${escapeHtml(d.unread_count)} 条">${d.unread_count}</div>` : ""}`;
    box.appendChild(a);
  });
}
function filterDialogs(){
  const q = $("dialogSearch").value.trim().toLowerCase();
  if (!q) return renderDialogs(DIALOGS);
  renderDialogs(DIALOGS.filter(d => String(d.name||"").toLowerCase().includes(q) || String(d.username||"").toLowerCase().includes(q) || String(d.peer||"").toLowerCase().includes(q) || String(d.id||"").includes(q)));
}

/* 聊天 */
async function initSingleChatPage(peer){
  CURRENT_PEER = peer; OLDEST_MSG_ID = 0;
  refreshStatus(); bindGalleryEvents(); await loadMessages();
}
function buildRenderBlocks(msgs){
  const blocks = []; let i = 0;
  while (i < msgs.length){
    const cur = msgs[i];
    if (!cur.grouped_id || cur.has_media !== true) { blocks.push({ type:"single", msg:cur }); i++; continue; }
    const group = [cur]; let j = i + 1;
    while (j < msgs.length && msgs[j].grouped_id === cur.grouped_id && msgs[j].has_media === true) { group.push(msgs[j]); j++; }
    if (group.length <= 1) { blocks.push({ type:"single", msg:cur }); i++; } else { blocks.push({ type:"media_group", items:group }); i = j; }
  }
  return blocks;
}
function messageBaseHtml(m){
  const meta = SHOW_META ? `<div class="msg-meta">#${m.id} · ${escapeHtml(m.date || "")}</div>` : "";
  const text = m.text ? `<div class="msg-text">${renderMarkdownSafe(m.text)}</div>` : "";
  return meta + text;
}
function messageAriaLabel(m, mediaCount = 0){
  const direction = m.out ? "已发送消息" : "收到消息";
  const media = mediaCount > 1 ? `，包含 ${mediaCount} 个媒体` : (m.has_media ? "，包含媒体" : "");
  return direction + media;
}
function decorateMessageElement(el, m, mediaCount = 0){
  if (!el || typeof el.setAttribute !== "function") return;
  el.setAttribute("role", "article");
  el.setAttribute("aria-label", messageAriaLabel(m, mediaCount));
}
function mediaDownloadButtonHtml(msgId){
  return `<button class="media-download-btn" type="button" aria-label="创建媒体 ${msgId} 下载任务" title="创建下载任务" onclick="event.stopPropagation(); downloadMedia(${msgId})">⬇</button>`;
}
async function loadMessages(){
  if (!CURRENT_PEER) return;
  const box = $("messageList");
  if (!box) return;
  setAriaBusy(box, true);
  box.innerHTML = `<div class="empty" role="status">加载消息中...</div>`;
  try{
    const msgs = await api("/api/messages?peer=" + encodeURIComponent(CURRENT_PEER) + "&limit=80");
    box.innerHTML = "";
    if (!msgs.length) {
      box.innerHTML = `<div class="empty" role="status">暂无消息</div>`;
      return;
    }
    OLDEST_MSG_ID = msgs[0]?.id || 0;
    const blocks = buildRenderBlocks(msgs);
    for (const b of blocks) {
      if (b.type === "single") appendSingleMessageBlock(b.msg, false);
      else appendMediaGroupBlock(b.items, false);
    }
    box.scrollTop = box.scrollHeight;
  } catch(e){
    box.innerHTML = `<div class="empty" role="status">${escapeHtml(e.message)}</div>`;
  } finally {
    setAriaBusy(box, false);
  }
}
async function loadOlderMessages(){
  if (!CURRENT_PEER || !OLDEST_MSG_ID) return;
  const box = $("messageList");
  setAriaBusy(box, true);
  try{
    const msgs = await api(`/api/messages?peer=${encodeURIComponent(CURRENT_PEER)}&limit=40&offset_id=${encodeURIComponent(OLDEST_MSG_ID)}`);
    if (!msgs.length) return toast("没有更早消息");
    OLDEST_MSG_ID = msgs[0]?.id || OLDEST_MSG_ID;
    const oldHeight = box.scrollHeight;
    const blocks = buildRenderBlocks(msgs);
    for (let i = blocks.length - 1; i >= 0; i--) {
      const b = blocks[i];
      if (b.type === "single") prependSingleMessageBlock(b.msg);
      else prependMediaGroupBlock(b.items);
    }
    box.scrollTop = box.scrollHeight - oldHeight;
  } catch(e){ toast(e.message); }
  finally { setAriaBusy(box, false); }
}
function appendSingleMessageBlock(m, scroll = true){
  const box = $("messageList"); if (!box) return;
  if (box.querySelector(`[data-msg-id="${m.id}"]`)) return;

  const div = document.createElement("div");
  div.className = "message " + (m.out ? "out " : "") + (m.has_media ? "has-media" : "");
  decorateMessageElement(div, m);
  div.dataset.msgId = m.id;
  div.innerHTML = `
    ${messageBaseHtml(m)}
    ${m.has_media ? `
      <div class="media-cluster" id="cluster-${m.id}">
        <div class="media-cell loading" data-msg-id="${m.id}">
          ${mediaDownloadButtonHtml(m.id)}
          <div class="media-placeholder">加载预览...</div>
        </div>
      </div>` : ""}
  `;
  box.appendChild(div);

  if (m.has_media) {
    const cell = div.querySelector(".media-cell");
    if (cell) {
      // 点击仅按需准备原文件
      cell.onclick = (e) => {
        if (e.target.closest(".media-download-btn")) return;
        openMediaViewerByMessage(m.id);
      };
      // 自动加载thumb（不下载原文件）
      loadThumbIntoCell(cell, m);
    }
  }

  if (scroll) box.scrollTop = box.scrollHeight;
}

function prependSingleMessageBlock(m){
  const box = $("messageList"); if (!box) return;
  if (box.querySelector(`[data-msg-id="${m.id}"]`)) return;

  const div = document.createElement("div");
  div.className = "message " + (m.out ? "out " : "") + (m.has_media ? "has-media" : "");
  decorateMessageElement(div, m);
  div.dataset.msgId = m.id;
  div.innerHTML = `
    ${messageBaseHtml(m)}
    ${m.has_media ? `
      <div class="media-cluster" id="cluster-${m.id}">
        <div class="media-cell loading" data-msg-id="${m.id}">
          ${mediaDownloadButtonHtml(m.id)}
          <div class="media-placeholder">加载预览...</div>
        </div>
      </div>` : ""}
  `;
  box.insertBefore(div, box.firstChild);

  if (m.has_media) {
    const cell = div.querySelector(".media-cell");
    if (cell) {
      cell.onclick = (e) => {
        if (e.target.closest(".media-download-btn")) return;
        openMediaViewerByMessage(m.id);
      };
      loadThumbIntoCell(cell, m);
    }
  }
}

function appendMediaGroupBlock(items, scroll = true){
  const box = $("messageList"); if (!box) return;
  const mainId = items[0].id;
  if (box.querySelector(`[data-msg-id="group-${mainId}"]`)) return;

  const first = items[0];
  const textMerged = items.map(x => x.text || "").filter(Boolean).join("\n").trim();

  const div = document.createElement("div");
  div.className = "message " + (first.out ? "out " : "") + "has-media";
  decorateMessageElement(div, first, items.length);
  div.dataset.msgId = "group-" + mainId;
  div.innerHTML = `
    ${SHOW_META ? `<div class="msg-meta">${escapeHtml(first.date || "")} · 媒体集(${items.length})</div>` : ""}
    ${textMerged ? `<div class="msg-text">${renderMarkdownSafe(textMerged)}</div>` : ""}
    <div class="media-cluster media-grid" id="cluster-group-${mainId}">
      ${items.map((x) => `
        <div class="media-cell loading" data-msg-id="${x.id}">
          ${mediaDownloadButtonHtml(x.id)}
          <div class="media-placeholder">加载预览...</div>
        </div>
      `).join("")}
    </div>
  `;
  box.appendChild(div);

  const cells = Array.from(div.querySelectorAll(".media-cell"));
  cells.forEach((cell, idx) => {
    const msg = items[idx];
    cell.onclick = (e) => {
      if (e.target.closest(".media-download-btn")) return;
      openMediaViewerByMessage(msg.id);
    };
    loadThumbIntoCell(cell, msg);
  });

  if (scroll) box.scrollTop = box.scrollHeight;
}

function prependMediaGroupBlock(items){
  const box = $("messageList"); if (!box) return;
  const mainId = items[0].id;
  if (box.querySelector(`[data-msg-id="group-${mainId}"]`)) return;

  const first = items[0];
  const textMerged = items.map(x => x.text || "").filter(Boolean).join("\n").trim();

  const div = document.createElement("div");
  div.className = "message " + (first.out ? "out " : "") + "has-media";
  decorateMessageElement(div, first, items.length);
  div.dataset.msgId = "group-" + mainId;
  div.innerHTML = `
    ${SHOW_META ? `<div class="msg-meta">${escapeHtml(first.date || "")} · 媒体集(${items.length})</div>` : ""}
    ${textMerged ? `<div class="msg-text">${renderMarkdownSafe(textMerged)}</div>` : ""}
    <div class="media-cluster media-grid" id="cluster-group-${mainId}">
      ${items.map((x) => `
        <div class="media-cell loading" data-msg-id="${x.id}">
          ${mediaDownloadButtonHtml(x.id)}
          <div class="media-placeholder">加载预览...</div>
        </div>
      `).join("")}
    </div>
  `;
  box.insertBefore(div, box.firstChild);

  const cells = Array.from(div.querySelectorAll(".media-cell"));
  cells.forEach((cell, idx) => {
    const msg = items[idx];
    cell.onclick = (e) => {
      if (e.target.closest(".media-download-btn")) return;
      openMediaViewerByMessage(msg.id);
    };
    loadThumbIntoCell(cell, msg);
  });
}

/* 预览：先 thumb，不自动下载原文件 */
async function loadThumbIntoCell(cell, msg) {
  const k = `${CURRENT_PEER}:${msg.id}`;

  // 1) 内存命中：本次页面生命周期内不重复请求
  if (THUMB_CACHE.has(k)) {
    const cachedUrl = THUMB_CACHE.get(k);
    cell.classList.remove("loading");
    if (cachedUrl) {
      cell.innerHTML = `
        ${mediaDownloadButtonHtml(msg.id)}
        <img src="${escapeHtml(cachedUrl)}" class="media-thumb" loading="lazy">
      `;
    } else {
      cell.innerHTML = `
        ${mediaDownloadButtonHtml(msg.id)}
        <div class="media-file-thumb">📄 无预览</div>
      `;
    }
    return;
  }

  try {
    const d = await api("/api/media/thumb", {
      method: "POST",
      body: JSON.stringify({ peer: CURRENT_PEER, msg_id: msg.id }),
    });

    cell.classList.remove("loading");

    if (d?.ready && d?.url) {
      THUMB_CACHE.set(k, d.url);
      cell.innerHTML = `
        ${mediaDownloadButtonHtml(msg.id)}
        <img src="${escapeHtml(d.url)}" class="media-thumb" loading="lazy">
      `;
    } else {
      THUMB_CACHE.set(k, null);
      cell.innerHTML = `
        ${mediaDownloadButtonHtml(msg.id)}
        <div class="media-file-thumb">📄 无预览</div>
      `;
    }
  } catch {
    THUMB_CACHE.set(k, null);
    cell.classList.remove("loading");
    cell.innerHTML = `
      ${mediaDownloadButtonHtml(msg.id)}
      <div class="media-file-thumb">📄 无预览</div>
    `;
  }
}
function mediaCellHtml(item, order = 0, total = 0){
  return `<div class="media-cell ready" data-msg-id="${item.msgId}">${mediaDownloadButtonHtml(item.msgId)}${renderMediaPreviewNode(item.url, item.mime)}${total > 1 ? `<div class="media-index">${order}/${total}</div>` : ""}</div>`;
}
function renderMediaPreviewNode(url, mime){
  if (mime.startsWith("image/")) return `<img src="${escapeHtml(url)}" class="media-thumb" loading="lazy">`;
  if (mime.startsWith("video/")) return `<video src="${escapeHtml(url)}" class="media-thumb" muted preload="metadata" playsinline></video>`;
  if (mime.startsWith("audio/")) return `<div class="media-audio-thumb">🎵 音频</div>`;
  return `<div class="media-file-thumb">📄 文件</div>`;
}
async function openMediaViewerByMessage(msgId){
  const d = await api("/api/media/prepare", { method:"POST", body: JSON.stringify({ peer: CURRENT_PEER, msg_id: msgId }) });
  if (!d.ready) {
    toast("媒体正在准备，稍后重试打开");
    return;
  }
  openGallery([{ msgId, url: d.url, mime: d.mime || "", label: `媒体 #${msgId}` }], 0);
}

function bindGroupCellClicks(clusterId, galleryItems){
  const cluster = $(clusterId); if (!cluster) return;
  const ready = Array.from(cluster.querySelectorAll(".media-cell.ready"));
  const normalized = galleryItems.filter(Boolean);
  if (!ready.length || !normalized.length) return;
  ready.forEach(cell => {
    const msgId = Number(cell.getAttribute("data-msg-id") || 0);
    const idx = normalized.findIndex(x => Number(x.msgId) === msgId);
    if (idx >= 0) cell.onclick = () => openGallery(normalized, idx);
  });
}
function appendLiveMessage(msg){
  const box = $("messageList"); if (!box) return;
  if (box.querySelector(`[data-msg-id="${msg.id}"]`) || box.querySelector(`[data-msg-id="group-${msg.id}"]`)) return;
  appendSingleMessageBlock(msg, true);
}

/* 查看器 */
function bindGalleryEvents(){
  const viewer = $("mediaViewer"); if (!viewer) return;
  if (galleryEventsBound) return;
  galleryEventsBound = true;
  $("viewerClose")?.addEventListener("click", closeGallery);
  $("viewerPrev")?.addEventListener("click", () => moveGallery(-1));
  $("viewerNext")?.addEventListener("click", () => moveGallery(1));
  $("viewerDownload")?.addEventListener("click", () => { const cur = GALLERY_ITEMS[GALLERY_INDEX]; if (cur) downloadMedia(cur.msgId); });
}
function getGalleryFocusables(){
  return [$("viewerClose"), $("viewerDownload"), $("viewerPrev"), $("viewerNext")]
    .filter(el => el && !el.disabled && typeof el.focus === "function");
}
function handleGalleryKeydown(event){
  const viewer = $("mediaViewer");
  if (!viewer?.classList.contains("show") || pendingConfirm) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeGallery();
  } else if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveGallery(-1);
  } else if (event.key === "ArrowRight") {
    event.preventDefault();
    moveGallery(1);
  } else if (event.key === "Tab") {
    const focusables = getGalleryFocusables();
    if (!focusables.length) {
      event.preventDefault();
      return;
    }
    const first = focusables[0], last = focusables[focusables.length - 1];
    const current = document.activeElement;
    if (event.shiftKey && (current === first || !focusables.includes(current))) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && (current === last || !focusables.includes(current))) {
      event.preventDefault();
      first.focus();
    }
  }
}
function openGallery(items, startIndex = 0){
  if (!items?.length) return;
  const viewer = $("mediaViewer"); if (!viewer) return;
  const wasOpen = viewer.classList.contains("show");
  GALLERY_ITEMS = items; GALLERY_INDEX = Math.max(0, Math.min(startIndex, items.length - 1));
  if (!wasOpen) galleryLastFocus = document.activeElement || null;
  viewer.classList.add("show");
  if (!galleryKeydownBound) {
    document.addEventListener("keydown", handleGalleryKeydown);
    galleryKeydownBound = true;
  }
  renderGalleryCurrent();
  setTimeout(() => $("viewerClose")?.focus(), 0);
}
function closeGallery(){
  const viewer = $("mediaViewer"); if (!viewer?.classList.contains("show")) return;
  viewer.classList.remove("show");
  if (galleryKeydownBound) {
    document.removeEventListener("keydown", handleGalleryKeydown);
    galleryKeydownBound = false;
  }
  if (galleryLastFocus && typeof galleryLastFocus.focus === "function") galleryLastFocus.focus();
  galleryLastFocus = null;
}
function moveGallery(step){
  if (!GALLERY_ITEMS.length) return;
  GALLERY_INDEX = (GALLERY_INDEX + step + GALLERY_ITEMS.length) % GALLERY_ITEMS.length;
  renderGalleryCurrent();
}
function renderGalleryCurrent(){
  const item = GALLERY_ITEMS[GALLERY_INDEX]; if (!item) return;
  $("viewerTitle").textContent = item.label || "媒体";
  $("viewerIndex").textContent = `${GALLERY_INDEX + 1} / ${GALLERY_ITEMS.length}`;
  const body = $("viewerBody"), mime = item.mime || "", url = item.url || "";
  if (mime.startsWith("image/")) body.innerHTML = `<img src="${escapeHtml(url)}" class="viewer-media">`;
  else if (mime.startsWith("video/")) body.innerHTML = `<video src="${escapeHtml(url)}" class="viewer-media" controls autoplay playsinline preload="metadata"></video>`;
  else if (mime.startsWith("audio/")) body.innerHTML = `<audio src="${escapeHtml(url)}" class="viewer-audio" controls autoplay preload="metadata"></audio>`;
  else body.innerHTML = `<a class="small-btn" href="${escapeHtml(url)}" target="_blank">打开文件</a>`;
}

/* 发送 */
async function sendText(){
  if (!CURRENT_PEER) return;
  const text = $("messageInput").value;
  if (!text.trim()) return;
  const panel = $("textComposer");
  setAriaBusy(panel, true);
  try{
    const msg = await api("/api/send", { method:"POST", body: JSON.stringify({ peer: CURRENT_PEER, text }) });
    $("messageInput").value = "";
    appendSingleMessageBlock(msg, true);
    $("textComposer").classList.remove("show");
    if (panel && typeof panel.setAttribute === "function") panel.setAttribute("aria-hidden", "true");
  } catch(e){ toast(e.message); }
  finally { setAriaBusy(panel, false); }
}
async function sendFile(){
  if (!CURRENT_PEER) return;
  const file = $("sendFileInput")?.files?.[0];
  if (!file) return toast("请选择文件");
  const panel = $("fileComposer");
  setAriaBusy(panel, true);
  const fd = new FormData();
  fd.append("peer", CURRENT_PEER);
  fd.append("caption", $("captionInput").value || "");
  fd.append("file", file);
  try{
    const msg = await api("/api/send-file", { method:"POST", body: fd });
    $("sendFileInput").value = ""; $("captionInput").value = ""; $("fileComposer").classList.remove("show");
    if (panel && typeof panel.setAttribute === "function") panel.setAttribute("aria-hidden", "true");
    appendSingleMessageBlock(msg, true);
  } catch(e){ toast(e.message); }
  finally { setAriaBusy(panel, false); }
}

/* 下载 */
async function downloadMedia(msgId){
  if (!CURRENT_PEER) return;
  try{
    await api("/api/download-media", { method:"POST", body: JSON.stringify({ peer: CURRENT_PEER, msg_id: msgId }) });
    toast("下载任务已创建，可在下载页查看进度");
  } catch(e){ toast(e.message); }
}
async function taskPause(id){ try{ await api(`/api/task/${id}/pause`, { method:"POST", body:"{}" }); await loadDownloadTasks(); } catch(e){ toast(e.message); } }
async function taskResume(id){ try{ await api(`/api/task/${id}/resume`, { method:"POST", body:"{}" }); await loadDownloadTasks(); } catch(e){ toast(e.message); } }
async function taskDelete(id, status = ""){
  const active = ["queued", "running", "paused"].includes(status);
  const text = active ? "确认取消这个下载/预览任务？任务记录会移除，并向后台任务发送取消信号。" : "确认移除这条终态任务记录？已下载文件不会删除。";
  if (!(await confirmSensitive(text))) return;
  try{
    await api(`/api/task/${id}`, { method:"DELETE" });
    await Promise.allSettled([loadDownloadTasks(), loadDownloadFiles(true)]);
  } catch(e){ toast(e.message); }
}

function taskKindText(kind){
  return {
    download_media: "下载原文件",
    prepare_media: "准备预览",
  }[kind] || kind || "任务";
}
function taskStatusText(status){
  return {
    queued: "排队中",
    running: "运行中",
    paused: "已暂停",
    done: "已完成",
    error: "失败",
    canceled: "已取消",
  }[status] || status || "未知";
}
async function initDownloadsPage(){
  await loadDownloadsPage();
  if (downloadsTimer) clearInterval(downloadsTimer);
  downloadsTimer = setInterval(loadDownloadTasks, 1200);
}
async function loadDownloadsPage(){ await Promise.allSettled([loadDownloadTasks(), loadDownloadFiles(true)]); }
async function loadDownloadTasks(){
  const box = $("downloadTaskList"); if (!box) return;
  setAriaBusy(box, true);
  try{
    const list = await api("/api/tasks");
    if (!list.length) {
      box.innerHTML = `<div class="empty" role="listitem">暂无任务</div>`;
      return;
    }
    box.innerHTML = list.map(t => {
      const controls = t.status === "running" ? `<button class="small-btn gray" type="button" onclick="taskPause('${t.id}')">暂停</button>` : t.status === "paused" ? `<button class="small-btn" type="button" onclick="taskResume('${t.id}')">恢复</button>` : "";
      const deleteText = ["queued", "running", "paused"].includes(t.status) ? "取消任务" : "移除记录";
      return `<div class="task-card" role="listitem"><div class="task-head"><div><div class="task-title">${escapeHtml(taskKindText(t.kind))} · ${escapeHtml(taskStatusText(t.status))}</div><div class="task-meta">${escapeHtml(t.downloaded_text || "0 B")}${t.total_text ? " / " + escapeHtml(t.total_text) : ""}${t.speed_text ? " · " + escapeHtml(t.speed_text) : ""}</div></div><b>${t.progress || 0}%</b></div><div class="progress-line"><div style="width:${t.progress || 0}%"></div></div><div class="actions" style="margin-top:8px">${controls}<button class="small-btn danger" type="button" onclick="taskDelete('${t.id}', '${escapeHtml(t.status)}')">${deleteText}</button></div></div>`;
    }).join("");
  } catch(e){
    box.innerHTML = `<div class="empty" role="listitem">${escapeHtml(e.message)}</div>`;
  } finally {
    setAriaBusy(box, false);
  }
}
function renderDownloadFile(f){
  const preview = f.is_image ? `<img src="${escapeHtml(f.url)}" class="download-thumb" loading="lazy">` : f.is_video ? `<video src="${escapeHtml(f.url)}" class="download-thumb" muted preload="metadata"></video>` : f.is_audio ? `<div class="audio-thumb">🎵</div>` : `<div class="file-thumb">📄</div>`;
  return `<div class="download-card" role="listitem">${preview}<div class="download-info"><b>${escapeHtml(f.name)}</b><span>${escapeHtml(f.kind)} · ${escapeHtml(f.size_text || formatSize(f.size || 0))}</span></div><a href="${escapeHtml(f.url)}" target="_blank" class="small-btn" aria-label="打开 ${escapeHtml(f.name)}">打开</a></div>`;
}
function updateDownloadFilePager(){
  const more = $("downloadFileMore");
  if (!more) return;
  more.style.display = downloadFilesHasMore ? "inline-flex" : "none";
  more.disabled = downloadFilesLoading;
  if (typeof more.setAttribute === "function") more.setAttribute("aria-disabled", downloadFilesLoading ? "true" : "false");
  more.textContent = downloadFilesLoading ? "加载中..." : "加载更多";
}
async function loadDownloadFiles(reset = false){
  const box = $("downloadFileList"); if (!box) return;
  const status = $("downloadFileStatus");
  if (downloadFilesLoading) return;
  if (reset) {
    downloadFilesOffset = 0;
    downloadFilesHasMore = false;
    updateDownloadFilePager();
  }
  downloadFilesLoading = true;
  setAriaBusy(box, true);
  setAriaBusy(status, true);
  updateDownloadFilePager();
  try{
    const offset = reset ? 0 : downloadFilesOffset;
    const data = await api(`/api/download-files?limit=${DOWNLOAD_FILE_LIMIT}&offset=${offset}`);
    const list = Array.isArray(data) ? data : (data.items || []);
    const total = Array.isArray(data) ? list.length : Number(data.total || 0);
    if (reset) box.innerHTML = "";
    if (!list.length && offset === 0) {
      box.innerHTML = `<div class="empty" role="listitem">暂无文件</div>`;
    } else if (list.length) {
      const html = list.map(renderDownloadFile).join("");
      if (reset) box.innerHTML = html;
      else box.insertAdjacentHTML("beforeend", html);
    }
    downloadFilesOffset = offset + list.length;
    downloadFilesHasMore = Array.isArray(data) ? false : Boolean(data.has_more);
    if (status) status.textContent = total ? `已显示 ${Math.min(downloadFilesOffset, total)} / ${total}` : "";
  } catch(e){
    if (reset || downloadFilesOffset === 0) box.innerHTML = `<div class="empty" role="listitem">${escapeHtml(e.message)}</div>`;
    else toast(e.message);
  } finally {
    downloadFilesLoading = false;
    setAriaBusy(box, false);
    setAriaBusy(status, false);
    updateDownloadFilePager();
  }
}

refreshStatus();
