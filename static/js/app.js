let DIALOGS = [];
let CURRENT_PEER = "";
let OLDEST_MSG_ID = 0;
let downloadsTimer = null;

let GALLERY_ITEMS = [];
let GALLERY_INDEX = 0;
const SHOW_META = false;

const THUMB_CACHE = new Map(); // key: `${peer}:${msgId}` -> url|null
const socket = io();
socket.on("new_message", msg => { if (msg && CURRENT_PEER) appendLiveMessage(msg); });

function $(id){ return document.getElementById(id); }
function escapeHtml(s){ return String(s || "").replace(/[&<>"']/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;" }[c])); }

function toast(text){
  const box = $("toast"); if (!box) return alert(text);
  const item = document.createElement("div");
  item.className = "toast-item"; item.textContent = text;
  box.appendChild(item); setTimeout(() => item.remove(), 2400);
}

async function api(path, options = {}){
  const isForm = options.body instanceof FormData;
  const res = await fetch(path, {
    ...options,
    headers: isForm ? (options.headers || {}) : { "Content-Type":"application/json", ...(options.headers || {}) }
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.success === false) throw new Error(data.error || data.message || "请求失败");
  return data.data;
}

function formatSize(n){
  n = Number(n || 0);
  const u = ["B","KB","MB","GB","TB"];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return i === 0 ? `${Math.round(n)} ${u[i]}` : `${n.toFixed(2)} ${u[i]}`;
}

function toggleFold(id){ $(id)?.classList.toggle("show"); }
function toggleComposer(id){
  document.querySelectorAll(".composer-panel").forEach(el => {
    if (el.id === id) el.classList.toggle("show");
    else el.classList.remove("show");
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
  try{
    const d = await api("/api/status");
    const top = $("topStatus"); if (!top) return;
    if (d.authorized) {
      const me = d.me || {};
      top.textContent = "已登录：" + (me.username || me.first_name || me.phone || me.id);
    } else if (d.connected) top.textContent = "已连接，未授权";
    else top.textContent = "未连接";
  } catch { $("topStatus") && ($("topStatus").textContent = "状态异常"); }
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
    $("download_threads").value = cfg.download_threads || 16;
    $("cache_limit_mb").value = cfg.cache_limit_mb || 1024;
  } catch(e){ toast(e.message); }
}
async function startLogin(){
  try{
    const d = await api("/api/login/start", {
      method:"POST",
      body: JSON.stringify({
        api_id: Number($("api_id").value || 0),
        api_hash: $("api_hash").value.trim(),
        phone: $("phone").value.trim(),
        proxy: $("proxy").value.trim(),
        download_threads: Number($("download_threads").value || 16),
        cache_limit_mb: Number($("cache_limit_mb").value || 1024),
      })
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
  if (!confirm("确认退出登录？")) return;
  try{ await api("/api/logout", { method:"POST", body:"{}" }); toast("已退出登录"); refreshStatus(); }
  catch(e){ toast(e.message); }
}

/* 会话 */
async function initDialogListPage(){ refreshStatus(); await loadDialogs(); }
async function loadDialogs(){
  const box = $("dialogList"); if (!box) return;
  box.innerHTML = `<div class="empty">加载中...</div>`;
  try{
    DIALOGS = await api("/api/dialogs?limit=120");
    renderDialogs(DIALOGS);
  } catch(e){ box.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`; }
}
function renderDialogs(list){
  const box = $("dialogList"); if (!box) return;
  box.innerHTML = "";
  if (!list.length) return box.innerHTML = `<div class="empty">暂无会话</div>`;
  list.forEach(d => {
    const first = String(d.name || "?").trim().slice(0, 1).toUpperCase();
    const a = document.createElement("a");
    a.className = "dialog-item";
    a.href = "/chat/" + encodeURIComponent(d.peer);
    a.innerHTML = `<div class="avatar">${escapeHtml(first)}</div><div style="min-width:0"><div class="dialog-name">${escapeHtml(d.name || d.peer)}</div><div class="dialog-meta">${d.username ? "@"+escapeHtml(d.username)+" · " : ""}${d.is_channel ? "频道" : d.is_group ? "群组" : "私聊"}</div></div>${d.unread_count ? `<div class="unread-badge">${d.unread_count}</div>` : ""}`;
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
async function loadMessages(){
  if (!CURRENT_PEER) return;
  const box = $("messageList");
  box.innerHTML = `<div class="empty">加载消息中...</div>`;
  try{
    const msgs = await api("/api/messages?peer=" + encodeURIComponent(CURRENT_PEER) + "&limit=80");
    box.innerHTML = "";
    if (!msgs.length) return box.innerHTML = `<div class="empty">暂无消息</div>`;
    OLDEST_MSG_ID = msgs[0]?.id || 0;
    const blocks = buildRenderBlocks(msgs);
    for (const b of blocks) {
      if (b.type === "single") appendSingleMessageBlock(b.msg, false);
      else appendMediaGroupBlock(b.items, false);
    }
    box.scrollTop = box.scrollHeight;
  } catch(e){ box.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`; }
}
async function loadOlderMessages(){
  if (!CURRENT_PEER || !OLDEST_MSG_ID) return;
  try{
    const msgs = await api(`/api/messages?peer=${encodeURIComponent(CURRENT_PEER)}&limit=40&offset_id=${encodeURIComponent(OLDEST_MSG_ID)}`);
    if (!msgs.length) return toast("没有更早消息");
    OLDEST_MSG_ID = msgs[0]?.id || OLDEST_MSG_ID;
    const box = $("messageList"); const oldHeight = box.scrollHeight;
    const blocks = buildRenderBlocks(msgs);
    for (let i = blocks.length - 1; i >= 0; i--) {
      const b = blocks[i];
      if (b.type === "single") prependSingleMessageBlock(b.msg);
      else prependMediaGroupBlock(b.items);
    }
    box.scrollTop = box.scrollHeight - oldHeight;
  } catch(e){ toast(e.message); }
}
function appendSingleMessageBlock(m, scroll = true){
  const box = $("messageList"); if (!box) return;
  if (box.querySelector(`[data-msg-id="${m.id}"]`)) return;

  const div = document.createElement("div");
  div.className = "message " + (m.out ? "out " : "") + (m.has_media ? "has-media" : "");
  div.dataset.msgId = m.id;
  div.innerHTML = `
    ${messageBaseHtml(m)}
    ${m.has_media ? `
      <div class="media-cluster" id="cluster-${m.id}">
        <div class="media-cell loading" data-msg-id="${m.id}">
          <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${m.id})">⬇</button>
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
  div.dataset.msgId = m.id;
  div.innerHTML = `
    ${messageBaseHtml(m)}
    ${m.has_media ? `
      <div class="media-cluster" id="cluster-${m.id}">
        <div class="media-cell loading" data-msg-id="${m.id}">
          <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${m.id})">⬇</button>
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
  div.dataset.msgId = "group-" + mainId;
  div.innerHTML = `
    ${SHOW_META ? `<div class="msg-meta">${escapeHtml(first.date || "")} · 媒体集(${items.length})</div>` : ""}
    ${textMerged ? `<div class="msg-text">${renderMarkdownSafe(textMerged)}</div>` : ""}
    <div class="media-cluster media-grid" id="cluster-group-${mainId}">
      ${items.map((x) => `
        <div class="media-cell loading" data-msg-id="${x.id}">
          <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${x.id})">⬇</button>
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
  div.dataset.msgId = "group-" + mainId;
  div.innerHTML = `
    ${SHOW_META ? `<div class="msg-meta">${escapeHtml(first.date || "")} · 媒体集(${items.length})</div>` : ""}
    ${textMerged ? `<div class="msg-text">${renderMarkdownSafe(textMerged)}</div>` : ""}
    <div class="media-cluster media-grid" id="cluster-group-${mainId}">
      ${items.map((x) => `
        <div class="media-cell loading" data-msg-id="${x.id}">
          <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${x.id})">⬇</button>
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
        <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${msg.id})">⬇</button>
        <img src="${escapeHtml(cachedUrl)}" class="media-thumb" loading="lazy">
      `;
    } else {
      cell.innerHTML = `
        <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${msg.id})">⬇</button>
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
        <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${msg.id})">⬇</button>
        <img src="${escapeHtml(d.url)}" class="media-thumb" loading="lazy">
      `;
    } else {
      THUMB_CACHE.set(k, null);
      cell.innerHTML = `
        <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${msg.id})">⬇</button>
        <div class="media-file-thumb">📄 无预览</div>
      `;
    }
  } catch {
    THUMB_CACHE.set(k, null);
    cell.classList.remove("loading");
    cell.innerHTML = `
      <button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${msg.id})">⬇</button>
      <div class="media-file-thumb">📄 无预览</div>
    `;
  }
}
function mediaCellHtml(item, order = 0, total = 0){
  return `<div class="media-cell ready" data-msg-id="${item.msgId}"><button class="media-download-btn" onclick="event.stopPropagation(); downloadMedia(${item.msgId})">⬇</button>${renderMediaPreviewNode(item.url, item.mime)}${total > 1 ? `<div class="media-index">${order}/${total}</div>` : ""}</div>`;
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
    toast("媒体正在准备");
    return;
  }
  openGallery([{ msgId, url: d.url, mime: d.mime || "", label: `media ${msgId}` }], 0);
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
  $("viewerClose")?.addEventListener("click", closeGallery);
  $("viewerPrev")?.addEventListener("click", () => moveGallery(-1));
  $("viewerNext")?.addEventListener("click", () => moveGallery(1));
  $("viewerDownload")?.addEventListener("click", () => { const cur = GALLERY_ITEMS[GALLERY_INDEX]; if (cur) downloadMedia(cur.msgId); });
}
function openGallery(items, startIndex = 0){
  if (!items?.length) return;
  GALLERY_ITEMS = items; GALLERY_INDEX = Math.max(0, Math.min(startIndex, items.length - 1));
  $("mediaViewer")?.classList.add("show");
  renderGalleryCurrent();
}
function closeGallery(){ $("mediaViewer")?.classList.remove("show"); }
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
  try{
    const msg = await api("/api/send", { method:"POST", body: JSON.stringify({ peer: CURRENT_PEER, text }) });
    $("messageInput").value = "";
    appendSingleMessageBlock(msg, true);
    $("textComposer").classList.remove("show");
  } catch(e){ toast(e.message); }
}
async function sendFile(){
  if (!CURRENT_PEER) return;
  const file = $("sendFileInput")?.files?.[0];
  if (!file) return toast("请选择文件");
  const fd = new FormData();
  fd.append("peer", CURRENT_PEER);
  fd.append("caption", $("captionInput").value || "");
  fd.append("file", file);
  try{
    const msg = await api("/api/send-file", { method:"POST", body: fd });
    $("sendFileInput").value = ""; $("captionInput").value = ""; $("fileComposer").classList.remove("show");
    appendSingleMessageBlock(msg, true);
  } catch(e){ toast(e.message); }
}

/* 下载 */
async function downloadMedia(msgId){
  if (!CURRENT_PEER) return;
  try{
    await api("/api/download-media", { method:"POST", body: JSON.stringify({ peer: CURRENT_PEER, msg_id: msgId }) });
    toast("下载任务已创建");
  } catch(e){ toast(e.message); }
}
async function taskPause(id){ try{ await api(`/api/task/${id}/pause`, { method:"POST", body:"{}" }); } catch(e){ toast(e.message); } }
async function taskResume(id){ try{ await api(`/api/task/${id}/resume`, { method:"POST", body:"{}" }); } catch(e){ toast(e.message); } }
async function taskDelete(id){ try{ await api(`/api/task/${id}`, { method:"DELETE" }); } catch(e){ toast(e.message); } }

async function initDownloadsPage(){
  await loadDownloadsPage();
  if (downloadsTimer) clearInterval(downloadsTimer);
  downloadsTimer = setInterval(loadDownloadsPage, 1200);
}
async function loadDownloadsPage(){ await Promise.allSettled([loadDownloadTasks(), loadDownloadFiles()]); }
async function loadDownloadTasks(){
  const box = $("downloadTaskList"); if (!box) return;
  try{
    const list = await api("/api/tasks");
    if (!list.length) return box.innerHTML = `<div class="empty">暂无任务</div>`;
    box.innerHTML = list.map(t => {
      const controls = t.status === "running" ? `<button class="small-btn gray" onclick="taskPause('${t.id}')">暂停</button>` : t.status === "paused" ? `<button class="small-btn" onclick="taskResume('${t.id}')">恢复</button>` : "";
      return `<div class="task-card"><div class="task-head"><div><div class="task-title">${escapeHtml(t.kind)} · ${escapeHtml(t.status)}</div><div class="task-meta">${escapeHtml(t.downloaded_text || "0 B")}${t.total_text ? " / " + escapeHtml(t.total_text) : ""}${t.speed_text ? " · " + escapeHtml(t.speed_text) : ""}</div></div><b>${t.progress || 0}%</b></div><div class="progress-line"><div style="width:${t.progress || 0}%"></div></div><div class="actions" style="margin-top:8px">${controls}<button class="small-btn danger" onclick="taskDelete('${t.id}')">删除</button></div></div>`;
    }).join("");
  } catch(e){ box.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`; }
}
async function loadDownloadFiles(){
  const box = $("downloadFileList"); if (!box) return;
  try{
    const list = await api("/api/download-files");
    if (!list.length) return box.innerHTML = `<div class="empty">暂无文件</div>`;
    box.innerHTML = list.map(f => {
      const preview = f.is_image ? `<img src="${escapeHtml(f.url)}" class="download-thumb" loading="lazy">` : f.is_video ? `<video src="${escapeHtml(f.url)}" class="download-thumb" muted preload="metadata"></video>` : f.is_audio ? `<div class="audio-thumb">🎵</div>` : `<div class="file-thumb">📄</div>`;
      return `<div class="download-card">${preview}<div class="download-info"><b>${escapeHtml(f.name)}</b><span>${escapeHtml(f.kind)} · ${escapeHtml(f.size_text || formatSize(f.size || 0))}</span></div><a href="${escapeHtml(f.url)}" target="_blank" class="small-btn">打开</a></div>`;
    }).join("");
  } catch(e){ box.innerHTML = `<div class="empty">${escapeHtml(e.message)}</div>`; }
}

refreshStatus();
