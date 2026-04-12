<template>
  <div class="layout">
    <!-- 顶栏 -->
    <header>
      <span class="title">easy_vpn 管理面板</span>
      <div class="header-right">
        <span class="stat">在线设备: {{ onlineCount }}</span>
        <button class="btn-logout" @click="logout">退出</button>
      </div>
    </header>

    <main>
      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-num">{{ stats.online_clients ?? '-' }}</div>
          <div class="stat-label">在线设备</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.http_rules ?? '-' }}</div>
          <div class="stat-label">HTTP 隧道</div>
        </div>
        <div class="stat-card">
          <div class="stat-num">{{ stats.tcp_rules ?? '-' }}</div>
          <div class="stat-label">TCP 隧道</div>
        </div>
      </div>

      <!-- 规则列表 -->
      <div class="section-header">
        <h3>隧道规则</h3>
        <button class="btn-primary" @click="openModal()">+ 新增规则</button>
      </div>

      <table class="rule-table">
        <thead>
          <tr>
            <th>类型</th>
            <th>设备</th>
            <th>外部地址</th>
            <th>本地地址</th>
            <th>备注</th>
            <th>设备状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="rules.length === 0">
            <td colspan="7" class="empty">暂无规则，点击右上角新增</td>
          </tr>
          <tr v-for="rule in rules" :key="rule.id">
            <td><span :class="['badge', rule.type]">{{ rule.type.toUpperCase() }}</span></td>
            <td>{{ rule.client_id }}</td>
            <td class="mono">
              <template v-if="rule.type === 'http'">{{ rule.subdomain }}</template>
              <template v-else>:{{ rule.server_port }}</template>
            </td>
            <td class="mono">{{ rule.local_host }}:{{ rule.local_port }}</td>
            <td>{{ rule.label || '-' }}</td>
            <td>
              <span :class="['dot', isOnline(rule.client_id) ? 'online' : 'offline']"></span>
              {{ isOnline(rule.client_id) ? '在线' : '离线' }}
            </td>
            <td>
              <button class="btn-sm" @click="openModal(rule)">编辑</button>
              <button class="btn-sm danger" @click="deleteRule(rule)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </main>

    <!-- 新增/编辑弹窗 -->
    <div v-if="modal.visible" class="modal-mask" @click.self="modal.visible = false">
      <div class="modal">
        <h4>{{ modal.rule.id ? '编辑规则' : '新增规则' }}</h4>

        <div class="field">
          <label>类型</label>
          <select v-model="modal.rule.type" :disabled="!!modal.rule.id">
            <option value="http">HTTP（Web 服务）</option>
            <option value="tcp">TCP（SSH 等）</option>
          </select>
        </div>
        <div class="field">
          <label>设备 ID（Client ID）</label>
          <input v-model="modal.rule.client_id" placeholder="如 nas / mac" />
        </div>

        <template v-if="modal.rule.type === 'http'">
          <div class="field">
            <label>子域名</label>
            <input v-model="modal.rule.subdomain" placeholder="如 nas.ruanpengpeng.cn" />
          </div>
        </template>
        <template v-else>
          <div class="field">
            <label>服务器端口（2200-2299）</label>
            <select v-model.number="modal.rule.server_port">
              <option v-for="p in availablePorts" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
        </template>

        <div class="field row">
          <div>
            <label>本地 Host</label>
            <input v-model="modal.rule.local_host" placeholder="127.0.0.1" />
          </div>
          <div>
            <label>本地端口</label>
            <input v-model.number="modal.rule.local_port" type="number" placeholder="22" />
          </div>
        </div>
        <div class="field">
          <label>备注（可选）</label>
          <input v-model="modal.rule.label" placeholder="如 Mac SSH" />
        </div>

        <p v-if="modal.error" class="error">{{ modal.error }}</p>
        <div class="modal-footer">
          <button @click="modal.visible = false">取消</button>
          <button class="btn-primary" :disabled="modal.saving" @click="saveRule">
            {{ modal.saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { clientApi, rulesApi, statsApi, portsApi } from '../api/index'

const router = useRouter()
const auth   = useAuthStore()

const clients        = ref([])
const rules          = ref([])
const stats          = ref({})
const availablePorts = ref([])

const onlineCount = computed(() => clients.value.length)
const isOnline    = (clientId) => clients.value.some(c => c.client_id === clientId)

// 弹窗状态
const modal = ref({
  visible: false,
  saving:  false,
  error:   '',
  rule:    defaultRule(),
})

function defaultRule() {
  return { type: 'http', client_id: '', subdomain: '', server_port: null,
           local_host: '127.0.0.1', local_port: '', label: '' }
}

function openModal(rule = null) {
  modal.value.error   = ''
  modal.value.saving  = false
  modal.value.rule    = rule ? { ...rule } : defaultRule()
  modal.value.visible = true
  if (!rule) loadAvailablePorts()
}

async function loadAvailablePorts() {
  try { availablePorts.value = await portsApi.available() } catch {}
}

async function saveRule() {
  modal.value.saving = true
  modal.value.error  = ''
  try {
    if (modal.value.rule.id) {
      const { id, ...updates } = modal.value.rule
      await rulesApi.update(id, updates)
    } else {
      await rulesApi.add(modal.value.rule)
    }
    modal.value.visible = false
    await refresh()
  } catch (e) {
    modal.value.error = e.response?.data?.detail || '保存失败'
  } finally {
    modal.value.saving = false
  }
}

async function deleteRule(rule) {
  const label = rule.label || (rule.type === 'http' ? rule.subdomain : `:${rule.server_port}`)
  if (!confirm(`确认删除规则「${label}」？`)) return
  await rulesApi.delete(rule.id)
  await refresh()
}

async function refresh() {
  const [c, r, s] = await Promise.all([clientApi.list(), rulesApi.list(), statsApi.get()])
  clients.value = c
  rules.value   = r
  stats.value   = s
}

function logout() {
  auth.logout()
  router.push('/login')
}

// 每 10 秒自动刷新在线状态
let timer
onMounted(async () => { await refresh(); timer = setInterval(refresh, 10000) })
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
* { box-sizing: border-box; }
.layout { min-height: 100vh; background: #f5f6fa; }

header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 56px; background: #1677ff; color: #fff;
}
.title { font-size: 18px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 16px; }
.stat { font-size: 14px; }
.btn-logout {
  background: rgba(255,255,255,.2); border: none; color: #fff;
  padding: 4px 12px; border-radius: 4px; cursor: pointer;
}

main { padding: 24px; }

.stats-row { display: flex; gap: 16px; margin-bottom: 24px; }
.stat-card {
  flex: 1; background: #fff; border-radius: 8px; padding: 20px;
  text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.stat-num { font-size: 32px; font-weight: 700; color: #1677ff; }
.stat-label { color: #888; margin-top: 4px; font-size: 13px; }

.section-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}
.section-header h3 { margin: 0; font-size: 16px; }

.rule-table {
  width: 100%; border-collapse: collapse; background: #fff;
  border-radius: 8px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.rule-table th, .rule-table td {
  padding: 12px 14px; text-align: left; border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
}
.rule-table th { background: #fafafa; color: #666; font-weight: 500; }
.rule-table tr:last-child td { border-bottom: none; }
.mono { font-family: monospace; font-size: 13px; }
.empty { text-align: center; color: #aaa; padding: 32px; }

.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 12px; font-weight: 600;
}
.badge.http { background: #e6f4ff; color: #1677ff; }
.badge.tcp  { background: #f6ffed; color: #52c41a; }

.dot {
  display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; margin-right: 5px;
}
.dot.online  { background: #52c41a; }
.dot.offline { background: #d9d9d9; }

.btn-primary {
  background: #1677ff; color: #fff; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px;
}
.btn-sm {
  padding: 3px 10px; font-size: 13px; border: 1px solid #d9d9d9;
  border-radius: 4px; cursor: pointer; background: #fff; margin-right: 6px;
}
.btn-sm.danger { color: #ff4d4f; border-color: #ffccc7; }
.btn-sm.danger:hover { background: #fff1f0; }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0,0,0,.45);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal {
  background: #fff; border-radius: 8px; padding: 28px;
  width: 480px; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,.2);
}
.modal h4 { margin: 0 0 20px; font-size: 16px; }
.field { margin-bottom: 16px; }
.field.row { display: flex; gap: 12px; }
.field.row > div { flex: 1; }
label { display: block; margin-bottom: 5px; font-size: 13px; color: #555; }
input, select {
  width: 100%; padding: 7px 10px; border: 1px solid #d9d9d9;
  border-radius: 4px; font-size: 14px;
}
input:focus, select:focus { outline: none; border-color: #4096ff; }
.error { color: #ff4d4f; font-size: 13px; margin: -8px 0 12px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 8px; }
.modal-footer button { padding: 7px 20px; border-radius: 4px; cursor: pointer; border: 1px solid #d9d9d9; }
</style>
