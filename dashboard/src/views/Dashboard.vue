<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 font-sans relative overflow-hidden">
    <!-- Atmospheric Background Blobs -->
    <div class="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
      <div class="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full bg-indigo-200/40 blur-3xl animate-pulse duration-[4000ms]"></div>
      <div class="absolute top-[20%] -right-[10%] w-[60%] h-[60%] rounded-full bg-violet-200/40 blur-3xl animate-pulse duration-[5000ms]"></div>
    </div>
    
    <!-- 顶栏 -->
    <header class="relative z-10 bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 flex items-center justify-center shadow-btn">
            <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
          </div>
          <span class="text-2xl font-extrabold tracking-tight text-slate-900">
            EASY_VPN <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-violet-600">NEXUS</span>
          </span>
        </div>
        <div class="flex items-center gap-6">
          <div class="flex items-center gap-2 bg-indigo-50 px-4 py-2 rounded-full border border-indigo-100">
            <span class="relative flex h-3 w-3">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span class="text-sm font-semibold text-indigo-900">在线设备: {{ onlineCount }}</span>
          </div>
          <button class="btn-secondary flex items-center gap-2" @click="logout">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"></path></svg>
            退出
          </button>
        </div>
      </div>
    </header>

    <main class="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
      <!-- 统计卡片 -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12 perspective-[2000px]">
        <div class="card p-6 flex items-center gap-6 group hover:rotate-x-[2deg] hover:rotate-y-[-2deg] transform-gpu">
          <div class="w-16 h-16 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
          </div>
          <div>
            <div class="text-4xl font-bold text-slate-900 mb-1">{{ stats.online_clients ?? '-' }}</div>
            <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider">在线设备</div>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-6 group hover:rotate-x-[2deg] hover:rotate-y-[0deg] transform-gpu">
          <div class="w-16 h-16 rounded-2xl bg-violet-50 text-violet-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path></svg>
          </div>
          <div>
            <div class="text-4xl font-bold text-slate-900 mb-1">{{ stats.http_rules ?? '-' }}</div>
            <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider">HTTP 隧道</div>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-6 group hover:rotate-x-[2deg] hover:rotate-y-[2deg] transform-gpu">
          <div class="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
          </div>
          <div>
            <div class="text-4xl font-bold text-slate-900 mb-1">{{ stats.tcp_rules ?? '-' }}</div>
            <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider">TCP 隧道</div>
          </div>
        </div>
      </div>

      <!-- 规则列表 -->
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="text-2xl font-bold text-slate-900">隧道规则</h3>
          <p class="text-slate-500 mt-1">管理您的内网穿透映射规则</p>
        </div>
        <button class="btn-primary flex items-center gap-2" @click="openModal()">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
          新增规则
        </button>
      </div>

      <div class="card overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-slate-50 border-b border-slate-200">
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">类型</th>
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">设备</th>
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">外部地址</th>
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">本地地址</th>
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">备注</th>
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider">状态</th>
                <th class="py-4 px-6 text-xs font-bold text-slate-500 uppercase tracking-wider text-right">操作</th>
              </tr>
            </thead>
            <TransitionGroup name="list" tag="tbody" class="divide-y divide-slate-100">
              <tr v-if="rules.length === 0" key="empty">
                <td colspan="7" class="py-16 text-center">
                  <div class="flex flex-col items-center justify-center text-slate-400">
                    <svg class="w-16 h-16 mb-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                    <p class="text-lg font-medium text-slate-600">暂无规则</p>
                    <p class="text-sm mt-1">点击右上角新增规则开始使用</p>
                  </div>
                </td>
              </tr>
              <tr v-for="rule in rules" :key="rule.id" class="hover:bg-indigo-50/30 transition-colors duration-200 group">
                <td class="py-4 px-6">
                  <span v-if="rule.type === 'http'" class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-indigo-100 text-indigo-700 border border-indigo-200">
                    HTTP
                  </span>
                  <span v-else class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">
                    TCP
                  </span>
                </td>
                <td class="py-4 px-6 font-semibold text-slate-900">{{ rule.client_id }}</td>
                <td class="py-4 px-6 font-mono text-sm text-indigo-600 font-medium">
                  <template v-if="rule.type === 'http'">{{ rule.subdomain }}</template>
                  <template v-else>:{{ rule.server_port }}</template>
                </td>
                <td class="py-4 px-6 font-mono text-sm text-slate-500">{{ rule.local_host }}:{{ rule.local_port }}</td>
                <td class="py-4 px-6 text-sm text-slate-600">{{ rule.label || '-' }}</td>
                <td class="py-4 px-6">
                  <div class="flex items-center gap-2">
                    <span :class="['w-2 h-2 rounded-full', isOnline(rule.client_id) ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-slate-300']"></span>
                    <span :class="['text-sm font-medium', isOnline(rule.client_id) ? 'text-emerald-600' : 'text-slate-500']">
                      {{ isOnline(rule.client_id) ? '在线' : '离线' }}
                    </span>
                  </div>
                </td>
                <td class="py-4 px-6 text-right">
                  <div class="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <button class="btn-icon" @click="openModal(rule)" title="编辑">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                    </button>
                    <button class="btn-icon danger" @click="deleteRule(rule)" title="删除">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                  </div>
                </td>
              </tr>
            </TransitionGroup>
          </table>
        </div>
      </div>
    </main>

    <!-- 新增/编辑弹窗 -->
    <Transition name="modal">
      <div v-if="modal.visible" class="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-0">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" @click="modal.visible = false"></div>
        
        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all">
          <div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <h4 class="text-lg font-bold text-slate-900">{{ modal.rule.id ? '编辑规则' : '新增规则' }}</h4>
            <button class="text-slate-400 hover:text-slate-600 transition-colors" @click="modal.visible = false">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
            </button>
          </div>

          <div class="p-6 space-y-5">
            <div>
              <label class="label">类型</label>
              <select v-model="modal.rule.type" :disabled="!!modal.rule.id" class="input-field">
                <option value="http">HTTP（Web 服务）</option>
                <option value="tcp">TCP（SSH 等）</option>
              </select>
            </div>
            
            <div>
              <label class="label">设备 ID (Client ID)</label>
              <input v-model="modal.rule.client_id" placeholder="如 nas / mac" class="input-field font-mono text-sm" />
            </div>

            <template v-if="modal.rule.type === 'http'">
              <div>
                <label class="label">子域名</label>
                <div class="relative">
                  <input v-model="modal.rule.subdomain" placeholder="如 nas" class="input-field font-mono text-sm pl-4 pr-32" />
                  <div class="absolute inset-y-0 right-0 flex items-center pr-4 pointer-events-none">
                    <span class="text-slate-400 text-sm font-mono">.ruanpengpeng.cn</span>
                  </div>
                </div>
              </div>
            </template>
            <template v-else>
              <div>
                <label class="label">服务器端口 (2200-2299)</label>
                <select v-model.number="modal.rule.server_port" class="input-field font-mono text-sm">
                  <option v-for="p in availablePorts" :key="p" :value="p">{{ p }}</option>
                </select>
              </div>
            </template>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="label">本地 Host</label>
                <input v-model="modal.rule.local_host" placeholder="127.0.0.1" class="input-field font-mono text-sm" />
              </div>
              <div>
                <label class="label">本地端口</label>
                <input v-model.number="modal.rule.local_port" type="number" placeholder="22" class="input-field font-mono text-sm" />
              </div>
            </div>
            
            <div>
              <label class="label">备注 (可选)</label>
              <input v-model="modal.rule.label" placeholder="如 Mac SSH" class="input-field" />
            </div>

            <Transition name="fade">
              <div v-if="modal.error" class="p-3 rounded-lg bg-red-50 border border-red-100 flex items-start gap-2">
                <svg class="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                <p class="text-sm text-red-600">{{ modal.error }}</p>
              </div>
            </Transition>
          </div>

          <div class="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end gap-3">
            <button class="btn-secondary" @click="modal.visible = false">取消</button>
            <button class="btn-primary" :disabled="modal.saving" @click="saveRule">
              {{ modal.saving ? '保存中...' : '确认保存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
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
/* Vue 动画过渡 */
.list-enter-active, .list-leave-active { transition: all 0.4s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateX(-20px); }

.modal-enter-active, .modal-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .transform, .modal-leave-to .transform { transform: scale(0.95) translateY(20px); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
