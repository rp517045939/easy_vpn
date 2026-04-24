"""
Client 本地 Web 管理界面，默认监听 http://localhost:7070
"""
import asyncio
import json
import logging
from pathlib import Path
import secrets

import yaml
from aiohttp import web

from state import client_state

logger = logging.getLogger(__name__)

SESSION_COOKIE = "easy_vpn_ui_session"


@web.middleware
async def password_auth_middleware(request, handler):
    if request.path in ("/login", "/api/login"):
        return await handler(request)

    if request.cookies.get(SESSION_COOKIE) != getattr(client_state, "ui_session_token", ""):
        raise web.HTTPFound("/login")

    return await handler(request)

# ------------------------------------------------------------------ HTML

_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>easy_vpn · 客户端管理</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f1f5f9; color: #0f172a; min-height: 100vh; }
  header { background: #fff; border-bottom: 1px solid #e2e8f0; padding: 0 24px;
           min-height: 60px; display: flex; align-items: center; gap: 12px;
           position: sticky; top: 0; z-index: 10; }
  .brand { display:flex; align-items:center; gap:10px; }
  .brand-mark { width:38px; height:38px; flex-shrink:0; }
  .brand-copy { display:flex; flex-direction:column; line-height:1.05; }
  .logo { font-size: 16px; font-weight: 800; color: #0f172a; letter-spacing: 0; }
  .logo-sub { margin-top:3px; font-size:10px; font-weight:700; color:#64748b; letter-spacing:.12em; text-transform:uppercase; }
  .dot { width: 8px; height: 8px; border-radius: 50%; margin-left: auto; flex-shrink: 0; }
  .dot.connected    { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,.6); }
  .dot.connecting   { background: #f59e0b; animation: pulse 1s infinite; }
  .dot.disconnected { background: #cbd5e1; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.4} }
  .status-text { font-size: 13px; font-weight: 500; }
  .status-text.connected    { color: #059669; }
  .status-text.connecting   { color: #d97706; }
  .status-text.disconnected { color: #94a3b8; }

  main { max-width: 960px; margin: 0 auto; padding: 24px 16px; display: grid;
         gap: 16px; grid-template-columns: 1fr 1fr; }
  @media(max-width:640px){ main{ grid-template-columns:1fr; } }

  .card { background:#fff; border-radius:12px; border:1px solid #e2e8f0;
          overflow:hidden; }
  .card-header { padding:16px 20px; border-bottom:1px solid #f1f5f9;
                 font-size:13px; font-weight:700; color:#64748b;
                 text-transform:uppercase; letter-spacing:.05em; }
  .card-body { padding:20px; }
  .span2 { grid-column: span 2; }
  @media(max-width:640px){ .span2{ grid-column:span 1; } }

  .info-row { display:flex; justify-content:space-between; align-items:center;
              padding:8px 0; border-bottom:1px solid #f8fafc; gap:12px; }
  .info-row:last-child { border:none; }
  .info-label { font-size:13px; color:#64748b; white-space:nowrap; }
  .info-value { font-size:13px; font-weight:500; text-align:right;
                word-break:break-all; font-family:ui-monospace,monospace; }
  .badge { display:inline-flex; align-items:center; padding:2px 8px;
           border-radius:6px; font-size:11px; font-weight:700; }
  .badge-http { background:#ede9fe; color:#6d28d9; }
  .badge-tcp  { background:#d1fae5; color:#065f46; }

  table { width:100%; border-collapse:collapse; font-size:13px; }
  th { text-align:left; padding:10px 12px; font-size:11px; font-weight:700;
       color:#94a3b8; text-transform:uppercase; letter-spacing:.05em;
       border-bottom:1px solid #f1f5f9; }
  td { padding:10px 12px; border-bottom:1px solid #f8fafc; vertical-align:middle; }
  tr:last-child td { border:none; }
  .mono { font-family:ui-monospace,monospace; font-size:12px; }
  .empty { text-align:center; padding:32px 0; color:#94a3b8; font-size:13px; }

  /* 日志区 */
  .log-wrap { background:#0f172a; border-radius:8px; height:340px;
              overflow-y:auto; padding:12px 14px; scroll-behavior:smooth; }
  .log-line { font-family:ui-monospace,monospace; font-size:12px;
              line-height:1.7; white-space:pre-wrap; word-break:break-all; }
  .log-line.INFO    { color:#94a3b8; }
  .log-line.WARNING { color:#fbbf24; }
  .log-line.ERROR   { color:#f87171; }
  .log-line.DEBUG   { color:#475569; }
  .log-controls { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
  .log-controls label { font-size:12px; color:#64748b; display:flex;
                        align-items:center; gap:4px; cursor:pointer; }
  .btn-clear { margin-left:auto; font-size:12px; padding:4px 10px;
               border:1px solid #e2e8f0; border-radius:6px; background:#fff;
               cursor:pointer; color:#64748b; }
  .btn-clear:hover { background:#f8fafc; }

  /* 配置编辑 */
  .field { margin-bottom:14px; }
  .field label { display:block; font-size:12px; font-weight:600;
                 color:#64748b; margin-bottom:4px; }
  .field input { width:100%; padding:8px 10px; border:1px solid #e2e8f0;
                 border-radius:8px; font-size:13px; font-family:ui-monospace,monospace;
                 outline:none; transition:border .15s; }
  .field input:focus { border-color:#6366f1; box-shadow:0 0 0 3px rgba(99,102,241,.1); }
  .field .hint { font-size:11px; color:#94a3b8; margin-top:3px; }
  .btn-save { width:100%; padding:9px; border:none; border-radius:8px;
              background:#4f46e5; color:#fff; font-size:13px; font-weight:600;
              cursor:pointer; transition:background .15s; }
  .btn-save:hover { background:#4338ca; }
  .btn-save:disabled { background:#a5b4fc; cursor:not-allowed; }
  .save-msg { text-align:center; font-size:12px; margin-top:8px; min-height:18px; }
  .save-msg.ok  { color:#059669; }
  .save-msg.err { color:#dc2626; }
</style>
</head>
<body>
<header>
  <div class="brand" aria-label="easy_vpn client">
    <svg class="brand-mark" viewBox="0 0 40 40" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
      <defs><linearGradient id="clientMark" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse"><stop stop-color="#4F46E5"/><stop offset="1" stop-color="#7C3AED"/></linearGradient></defs>
      <rect x="1" y="1" width="38" height="38" rx="10" fill="white" stroke="#E2E8F0" stroke-width="2"/>
      <path d="M20 6.5L31 11V19.2C31 26.2 26.5 31.7 20 34C13.5 31.7 9 26.2 9 19.2V11L20 6.5Z" fill="url(#clientMark)"/>
      <path d="M14 20H18.2L16.8 27L26 16.5H21.8L23.2 10L14 20Z" fill="white"/>
      <path d="M7.5 14.5H3.5M36.5 14.5H32.5M7.5 25.5H3.5M36.5 25.5H32.5" stroke="#818CF8" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <span class="brand-copy">
      <span class="logo">easy_vpn</span>
      <span class="logo-sub">client console</span>
    </span>
  </div>
  <span class="dot disconnected" id="hDot"></span>
  <span class="status-text disconnected" id="hStatus">加载中…</span>
</header>

<main>
  <!-- 连接信息 -->
  <div class="card">
    <div class="card-header">连接状态</div>
    <div class="card-body">
      <div class="info-row">
        <span class="info-label">服务器</span>
        <span class="info-value" id="iServer">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">设备 ID</span>
        <span class="info-value" id="iClientId">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">在线时长</span>
        <span class="info-value" id="iUptime">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">↑ 上行（本次）</span>
        <span class="info-value" id="iBytesSent">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">↓ 下行（本次）</span>
        <span class="info-value" id="iBytesRecv">-</span>
      </div>
      <div class="info-row">
        <span class="info-label">HTTP 请求 / TCP 连接</span>
        <span class="info-value" id="iReqCount">-</span>
      </div>
    </div>
  </div>

  <!-- 配置编辑 -->
  <div class="card">
    <div class="card-header">配置</div>
    <div class="card-body">
      <div class="field">
        <label>服务器地址</label>
        <input id="cfgUrl" type="text" placeholder="wss://vpn.example.com/tunnel/ws">
      </div>
      <div class="field">
        <label>设备 ID</label>
        <input id="cfgId" type="text" placeholder="macM1">
      </div>
      <div class="field">
        <label>Token</label>
        <input id="cfgToken" type="password" placeholder="••••••••">
        <div class="hint">留空则不修改</div>
      </div>
      <button class="btn-save" id="btnSave" onclick="saveConfig()">保存并重启连接</button>
      <div class="save-msg" id="saveMsg"></div>
    </div>
  </div>

  <!-- 规则列表 -->
  <div class="card span2">
    <div class="card-header">穿透规则 <span id="ruleCount" style="font-weight:400;color:#94a3b8"></span></div>
    <div class="card-body" style="padding:0">
      <div id="rulesWrap">
        <div class="empty">暂无规则（等待服务器推送）</div>
      </div>
    </div>
  </div>

  <!-- 日志 -->
  <div class="card span2">
    <div class="card-header">实时日志</div>
    <div class="card-body">
      <div class="log-controls">
        <label><input type="checkbox" id="chkAutoScroll" checked> 自动滚动</label>
        <button class="btn-clear" onclick="clearLogs()">清空</button>
      </div>
      <div class="log-wrap" id="logWrap"></div>
    </div>
  </div>
</main>

<script>
let uptimeBase = 0, uptimeTimer = null

function fmtBytes(n) {
  if (n === 0) return '0 B'
  const u = ['B','KB','MB','GB','TB']
  const i = Math.floor(Math.log(n) / Math.log(1024))
  return (n / Math.pow(1024, i)).toFixed(i ? 1 : 0) + ' ' + u[i]
}

// ── 状态轮询 ──────────────────────────────
async function fetchStatus() {
  try {
    const d = await fetch('/api/status').then(r => r.json())
    const s = d.status

    const dot = document.getElementById('hDot')
    const txt = document.getElementById('hStatus')
    dot.className = 'dot ' + s
    txt.className = 'status-text ' + s
    txt.textContent = s === 'connected' ? '已连接' : s === 'connecting' ? '连接中…' : '未连接'

    document.getElementById('iServer').textContent = d.server_url || '-'
    document.getElementById('iClientId').textContent = d.client_id || '-'

    // 配置回填（仅首次）
    if (!document.getElementById('cfgUrl').dataset.filled) {
      document.getElementById('cfgUrl').value = d.server_url || ''
      document.getElementById('cfgId').value = d.client_id || ''
      document.getElementById('cfgUrl').dataset.filled = '1'
    }

    // 在线时长
    if (s === 'connected' && d.uptime_seconds > 0) {
      uptimeBase = Date.now() / 1000 - d.uptime_seconds
      if (!uptimeTimer) uptimeTimer = setInterval(tickUptime, 1000)
    } else {
      clearInterval(uptimeTimer); uptimeTimer = null
      document.getElementById('iUptime').textContent = '-'
    }

    // 流量
    const t = d.traffic || {}
    document.getElementById('iBytesSent').textContent =
      d.status === 'connected' ? fmtBytes(t.bytes_sent || 0) : '-'
    document.getElementById('iBytesRecv').textContent =
      d.status === 'connected' ? fmtBytes(t.bytes_recv || 0) : '-'
    document.getElementById('iReqCount').textContent =
      d.status === 'connected'
        ? `${(t.http_requests || 0).toLocaleString()} / ${(t.tcp_connections || 0).toLocaleString()}`
        : '-'

    // 规则
    renderRules(d.rules || [])
  } catch(e) { /* 忽略 */ }
}

function tickUptime() {
  const s = Math.round(Date.now()/1000 - uptimeBase)
  const h = Math.floor(s/3600), m = Math.floor((s%3600)/60), ss = s%60
  document.getElementById('iUptime').textContent =
    (h ? h+'h ' : '') + (m ? m+'m ' : '') + ss + 's'
}

function renderRules(rules) {
  const wrap = document.getElementById('rulesWrap')
  document.getElementById('ruleCount').textContent = rules.length ? `(${rules.length})` : ''
  if (!rules.length) {
    wrap.innerHTML = '<div class="empty">暂无规则（等待服务器推送）</div>'
    return
  }
  wrap.innerHTML = `<table>
    <thead><tr>
      <th>类型</th><th>外部地址</th><th>本地地址</th><th>备注</th>
    </tr></thead>
    <tbody>${rules.map(r => `<tr>
      <td><span class="badge badge-${r.type}">${r.type.toUpperCase()}</span></td>
      <td class="mono">${r.type==='http' ? r.subdomain : ':'+r.server_port}</td>
      <td class="mono">${r.local_host}:${r.local_port}</td>
      <td>${r.label || '-'}</td>
    </tr>`).join('')}</tbody>
  </table>`
}

// ── 日志轮询 ─────────────────────────────
const logWrap = document.getElementById('logWrap')
let lastLogsSignature = ''

function appendLog(line) {
  const lvl = /\] (\w+)/.exec(line)?.[1] || 'INFO'
  const el = document.createElement('div')
  el.className = 'log-line ' + lvl
  el.textContent = line
  logWrap.appendChild(el)
  // 保留最近 2000 行
  while (logWrap.children.length > 2000) logWrap.removeChild(logWrap.firstChild)
  if (document.getElementById('chkAutoScroll').checked)
    logWrap.scrollTop = logWrap.scrollHeight
}

function clearLogs() { logWrap.innerHTML = '' }

function renderLogs(lines) {
  const signature = JSON.stringify(lines)
  if (signature === lastLogsSignature) return
  lastLogsSignature = signature
  logWrap.innerHTML = ''
  lines.forEach(appendLog)
}

async function fetchLogs() {
  try {
    const lines = await fetch('/api/logs').then(r => r.json())
    renderLogs(lines)
  } catch(e) { /* 忽略 */ }
}

// ── 配置保存 ─────────────────────────────
async function saveConfig() {
  const btn = document.getElementById('btnSave')
  const msg = document.getElementById('saveMsg')
  btn.disabled = true; msg.textContent = '保存中…'; msg.className = 'save-msg'
  try {
    const body = { url: document.getElementById('cfgUrl').value.trim(),
                   client_id: document.getElementById('cfgId').value.trim() }
    const token = document.getElementById('cfgToken').value
    if (token) body.token = token
    const r = await fetch('/api/config', { method:'PUT',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) })
    if (r.ok) { msg.textContent = '已保存，正在重新连接…'; msg.className = 'save-msg ok' }
    else       { msg.textContent = '保存失败: ' + (await r.text()); msg.className = 'save-msg err' }
  } catch(e) { msg.textContent = '网络错误'; msg.className = 'save-msg err' }
  finally { btn.disabled = false }
}

// ── 启动 ──────────────────────────────────
fetchStatus()
setInterval(fetchStatus, 3000)
fetchLogs()
setInterval(fetchLogs, 3000)
</script>
</body>
</html>"""


_LOGIN_HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>easy_vpn · 登录</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    min-height: 100vh;
    display: grid;
    place-items: center;
    background: linear-gradient(160deg, #eef2ff 0%, #f8fafc 45%, #e2e8f0 100%);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    color: #0f172a;
    padding: 24px;
  }
  .card {
    width: 100%;
    max-width: 360px;
    background: rgba(255,255,255,.9);
    backdrop-filter: blur(10px);
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    box-shadow: 0 20px 50px rgba(15, 23, 42, .08);
    padding: 28px;
  }
  .brand { display:flex; align-items:center; gap:12px; margin-bottom:20px; }
  .brand-mark { width:48px; height:48px; flex-shrink:0; }
  .brand-copy { display:flex; flex-direction:column; line-height:1.05; }
  .title { font-size: 23px; font-weight: 800; color:#0f172a; letter-spacing:0; }
  .kicker { margin-top:4px; font-size:10px; font-weight:800; color:#64748b; letter-spacing:.14em; text-transform:uppercase; }
  .sub { color: #64748b; font-size: 14px; margin-bottom: 20px; }
  label { display:block; font-size:12px; font-weight:700; color:#475569; margin-bottom:8px; text-transform:uppercase; letter-spacing:.04em; }
  input {
    width: 100%; padding: 12px 14px; border: 1px solid #cbd5e1; border-radius: 12px;
    font-size: 14px; outline: none; transition: .15s border, .15s box-shadow;
  }
  input:focus { border-color: #6366f1; box-shadow: 0 0 0 3px rgba(99,102,241,.12); }
  button {
    width: 100%; margin-top: 16px; border: none; border-radius: 12px; padding: 12px 14px;
    background: linear-gradient(135deg, #4f46e5, #6366f1); color: white; font-weight: 700;
    cursor: pointer;
  }
  button:hover { filter: brightness(1.03); }
  .error { color: #dc2626; font-size: 13px; min-height: 18px; margin-top: 10px; }
</style>
</head>
<body>
  <div class="card">
    <div class="brand" aria-label="easy_vpn client">
      <svg class="brand-mark" viewBox="0 0 40 40" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
        <defs><linearGradient id="loginMark" x1="4" y1="4" x2="36" y2="36" gradientUnits="userSpaceOnUse"><stop stop-color="#4F46E5"/><stop offset="1" stop-color="#7C3AED"/></linearGradient></defs>
        <rect x="1" y="1" width="38" height="38" rx="10" fill="white" stroke="#E2E8F0" stroke-width="2"/>
        <path d="M20 6.5L31 11V19.2C31 26.2 26.5 31.7 20 34C13.5 31.7 9 26.2 9 19.2V11L20 6.5Z" fill="url(#loginMark)"/>
        <path d="M14 20H18.2L16.8 27L26 16.5H21.8L23.2 10L14 20Z" fill="white"/>
        <path d="M7.5 14.5H3.5M36.5 14.5H32.5M7.5 25.5H3.5M36.5 25.5H32.5" stroke="#818CF8" stroke-width="2" stroke-linecap="round"/>
      </svg>
      <div class="brand-copy">
        <div class="title">easy_vpn</div>
        <div class="kicker">client console</div>
      </div>
    </div>
    <div class="sub">请输入本次启动生成的访问密码</div>
    <label for="password">访问密码</label>
    <input id="password" type="password" placeholder="请输入密码" autofocus />
    <button onclick="login()">进入管理页面</button>
    <div class="error" id="error"></div>
  </div>
<script>
async function login() {
  const password = document.getElementById('password').value
  const error = document.getElementById('error')
  error.textContent = ''
  try {
    const res = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    })
    if (res.ok) {
      window.location.href = '/'
      return
    }
    error.textContent = '密码错误'
  } catch {
    error.textContent = '网络错误'
  }
}
document.getElementById('password').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') login()
})
</script>
</body>
</html>"""


# ------------------------------------------------------------------ API

async def handle_index(request):
    return web.Response(text=_HTML, content_type="text/html")


async def handle_login_page(request):
    return web.Response(text=_LOGIN_HTML, content_type="text/html")


async def handle_login(request):
    try:
        body = await request.json()
    except Exception:
        return web.Response(text="invalid request", status=400)

    if body.get("password") != client_state.ui_password:
        return web.Response(text="invalid password", status=401)

    response = web.json_response({"ok": True})
    response.set_cookie(
        SESSION_COOKIE,
        client_state.ui_session_token,
        httponly=True,
        samesite="Lax",
    )
    return response


async def handle_status(request):
    return web.json_response(client_state.snapshot())


async def handle_logs_stream(request):
    """SSE 端点，先推送历史日志，再实时推送新日志。"""
    response = web.StreamResponse()
    response.headers["Content-Type"] = "text/event-stream"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    await response.prepare(request)

    # 推送历史缓冲
    history = client_state.get_log_buffer()
    data = json.dumps(history, ensure_ascii=False)
    await response.write(f"event: history\ndata: {data}\n\n".encode())

    # 实时订阅
    q = client_state.subscribe_logs()
    try:
        while True:
            try:
                line = await asyncio.wait_for(q.get(), timeout=25)
                await response.write(f"event: log\ndata: {line}\n\n".encode())
            except asyncio.TimeoutError:
                # 心跳，防止连接被代理断掉
                await response.write(b": ping\n\n")
    except (ConnectionResetError, Exception):
        pass
    finally:
        client_state.unsubscribe_logs(q)

    return response


async def handle_logs(request):
    """返回当前日志缓冲，供代理场景下轮询读取。"""
    return web.json_response(client_state.get_log_buffer())


async def handle_get_config(request):
    try:
        with open(client_state.config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        return web.json_response({
            "url": cfg.get("server", {}).get("url", ""),
            "client_id": cfg.get("client", {}).get("id", ""),
            "token": "••••••••",  # 不返回真实 token
        })
    except Exception as e:
        return web.Response(text=str(e), status=500)


async def handle_put_config(request):
    try:
        body = await request.json()
        with open(client_state.config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}

        cfg.setdefault("server", {})["url"] = body.get("url", cfg["server"].get("url", ""))
        cfg.setdefault("client", {})["id"]  = body.get("client_id", cfg.get("client", {}).get("id", ""))
        if body.get("token"):
            cfg["server"]["token"] = body["token"]

        with open(client_state.config_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

        # 通知主循环重新连接
        if client_state.reload_event:
            client_state.reload_event.set()

        return web.json_response({"ok": True})
    except Exception as e:
        return web.Response(text=str(e), status=500)


# ------------------------------------------------------------------ 启动

def create_app() -> web.Application:
    app = web.Application(middlewares=[password_auth_middleware])
    app.router.add_get("/",                  handle_index)
    app.router.add_get("/login",             handle_login_page)
    app.router.add_post("/api/login",        handle_login)
    app.router.add_get("/api/status",        handle_status)
    app.router.add_get("/api/logs",          handle_logs)
    app.router.add_get("/api/logs/stream",   handle_logs_stream)
    app.router.add_get("/api/config",        handle_get_config)
    app.router.add_put("/api/config",        handle_put_config)
    return app


async def start_web_ui(host: str = "127.0.0.1", port: int = 7070):
    client_state.ui_session_token = secrets.token_urlsafe(24)
    app = create_app()
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Web UI running at http://%s:%s", host, port)
    logger.info(
        "Local admin UI credentials: url=http://%s:%s password=%s",
        host,
        port,
        client_state.ui_password,
    )
