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
        <div class="flex items-center">
          <img :src="logoUrl" alt="EASY_VPN Nexus" class="h-10 w-auto" />
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
            <div v-if="isBootstrapping" class="h-10 w-16 rounded-xl bg-slate-200 animate-pulse mb-1"></div>
            <div v-else class="text-4xl font-bold text-slate-900 mb-1">{{ stats.online_clients ?? '-' }}</div>
            <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider">在线设备</div>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-6 group hover:rotate-x-[2deg] hover:rotate-y-[0deg] transform-gpu">
          <div class="w-16 h-16 rounded-2xl bg-violet-50 text-violet-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"></path></svg>
          </div>
          <div>
            <div v-if="isBootstrapping" class="h-10 w-16 rounded-xl bg-slate-200 animate-pulse mb-1"></div>
            <div v-else class="text-4xl font-bold text-slate-900 mb-1">{{ stats.http_rules ?? '-' }}</div>
            <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider">HTTP 隧道</div>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-6 group hover:rotate-x-[2deg] hover:rotate-y-[2deg] transform-gpu">
          <div class="w-16 h-16 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
            <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
          </div>
          <div>
            <div v-if="isBootstrapping" class="h-10 w-16 rounded-xl bg-slate-200 animate-pulse mb-1"></div>
            <div v-else class="text-4xl font-bold text-slate-900 mb-1">{{ stats.tcp_rules ?? '-' }}</div>
            <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider">TCP 隧道</div>
          </div>
        </div>
      </div>

      <!-- 设备列表 -->
      <div v-if="isBootstrapping" class="mb-12">
        <div class="mb-6">
          <h3 class="text-2xl font-bold text-slate-900">设备概览</h3>
          <p class="text-slate-500 mt-1">正在加载设备与流量数据...</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="i in 3" :key="i" class="card p-5">
            <div class="animate-pulse space-y-4">
              <div class="flex items-center justify-between">
                <div class="h-5 w-24 rounded bg-slate-200"></div>
                <div class="h-5 w-12 rounded-full bg-slate-200"></div>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div class="h-16 rounded-2xl bg-slate-100"></div>
                <div class="h-16 rounded-2xl bg-slate-100"></div>
              </div>
              <div class="h-4 w-2/3 rounded bg-slate-100"></div>
            </div>
          </div>
        </div>
      </div>
      <div v-else-if="allDevices.length > 0" class="mb-12">
        <div class="mb-6">
          <h3 class="text-2xl font-bold text-slate-900">设备概览</h3>
          <p class="text-slate-500 mt-1">点击卡片查看详细流量历史</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div v-for="d in allDevices" :key="d.client_id"
               class="card p-5 flex flex-col gap-4 cursor-pointer hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 active:scale-[0.98]"
               @click="openDetail(d.client_id)">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span v-if="d.online"
                      class="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]"></span>
                <span v-else class="w-2.5 h-2.5 rounded-full bg-slate-300"></span>
                <span class="font-bold text-slate-900 font-mono">{{ d.client_id }}</span>
              </div>
              <div class="flex items-center gap-2">
                <span v-if="d.online" class="text-xs font-semibold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">在线</span>
                <span v-else class="text-xs text-slate-400">{{ fmtTime(d.last_active) }}</span>
                <svg class="w-4 h-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div class="bg-indigo-50 rounded-xl p-3">
                <div class="text-xs text-indigo-500 font-semibold mb-1">↑ 上行</div>
                <div class="text-lg font-bold text-indigo-700 font-mono">{{ fmtBytes(d.bytes_out) }}</div>
              </div>
              <div class="bg-violet-50 rounded-xl p-3">
                <div class="text-xs text-violet-500 font-semibold mb-1">↓ 下行</div>
                <div class="text-lg font-bold text-violet-700 font-mono">{{ fmtBytes(d.bytes_in) }}</div>
              </div>
            </div>
            <div class="flex justify-between text-xs text-slate-500 border-t border-slate-100 pt-3">
              <span>HTTP <strong class="text-slate-700">{{ (d.http_requests ?? 0).toLocaleString() }}</strong></span>
              <span>TCP <strong class="text-slate-700">{{ (d.tcp_connections ?? 0).toLocaleString() }}</strong></span>
              <span v-if="d.online" class="text-emerald-600">在线 {{ fmtUptime(d.online_seconds) }}</span>
            </div>
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
            <tbody v-if="isBootstrapping" class="divide-y divide-slate-100">
              <tr v-for="i in 4" :key="`skeleton-${i}`">
                <td colspan="7" class="py-4 px-6">
                  <div class="animate-pulse flex items-center gap-4">
                    <div class="h-5 w-14 rounded-md bg-slate-200"></div>
                    <div class="h-4 w-24 rounded bg-slate-200"></div>
                    <div class="h-4 w-28 rounded bg-slate-100"></div>
                    <div class="h-4 w-32 rounded bg-slate-100"></div>
                    <div class="h-4 w-20 rounded bg-slate-100"></div>
                    <div class="h-4 w-16 rounded bg-slate-100"></div>
                  </div>
                </td>
              </tr>
            </tbody>
            <TransitionGroup v-else name="list" tag="tbody" class="divide-y divide-slate-100">
              <tr v-if="rules.length === 0" key="empty">
                <td colspan="7" class="py-16 text-center">
                  <div class="flex flex-col items-center justify-center text-slate-400">
                    <svg class="w-16 h-16 mb-4 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                    <p class="text-lg font-medium text-slate-600">暂无规则</p>
                    <p class="text-sm mt-1">点击右上角新增规则开始使用</p>
                  </div>
                </td>
              </tr>
              <tr v-for="rule in rules" :key="rule.id"
                  :class="['hover:bg-indigo-50/30 transition-colors duration-200 group',
                           rule.enabled === false ? 'opacity-50' : '']">
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
                  <div class="flex items-center justify-end gap-3">
                    <!-- 启用/暂停开关（常驻显示） -->
                    <button
                      @click="toggleRule(rule)"
                      :title="rule.enabled === false ? '点击启用' : '点击暂停'"
                      :class="['relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 focus:outline-none',
                               rule.enabled === false ? 'bg-slate-200' : 'bg-emerald-500']"
                    >
                      <span :class="['pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow transition duration-200',
                                     rule.enabled === false ? 'translate-x-0' : 'translate-x-4']">
                      </span>
                    </button>
                    <!-- 编辑/删除（hover 显示） -->
                    <div class="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                      <button class="btn-icon" @click="openModal(rule)" title="编辑">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg>
                      </button>
                      <button class="btn-icon danger" @click="deleteRule(rule)" title="删除">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                      </button>
                    </div>
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
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity" @click="modal.visible = false; clientDropdownOpen = false"></div>

        <div class="relative bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden transform transition-all">
          <div class="px-6 py-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
            <h4 class="text-lg font-bold text-slate-900">{{ modal.rule.id ? '编辑规则' : '新增规则' }}</h4>
            <button class="text-slate-400 hover:text-slate-600 transition-colors" @click="modal.visible = false; clientDropdownOpen = false">
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
              <div class="relative" v-click-outside="() => clientDropdownOpen = false">
                <div class="flex">
                  <input
                    v-model="modal.rule.client_id"
                    placeholder="如 nas / mac"
                    class="input-field font-mono text-sm rounded-r-none flex-1"
                    @focus="clientDropdownOpen = clients.length > 0"
                  />
                  <button
                    v-if="clients.length > 0"
                    type="button"
                    @click="clientDropdownOpen = !clientDropdownOpen"
                    class="px-3 bg-white border border-l-0 border-slate-200 rounded-r-xl text-slate-400 hover:text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    <svg class="w-4 h-4 transition-transform" :class="clientDropdownOpen ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
                    </svg>
                  </button>
                </div>
                <div
                  v-if="clientDropdownOpen && clients.length > 0"
                  class="absolute z-50 mt-1 w-full bg-white border border-slate-200 rounded-xl shadow-lg overflow-hidden"
                >
                  <div
                    v-for="c in clients"
                    :key="c.client_id"
                    @mousedown.prevent="modal.rule.client_id = c.client_id; clientDropdownOpen = false"
                    class="flex items-center gap-3 px-4 py-2.5 cursor-pointer hover:bg-slate-50 transition-colors"
                    :class="modal.rule.client_id === c.client_id ? 'bg-indigo-50' : ''"
                  >
                    <span class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)] flex-shrink-0"></span>
                    <span class="font-mono text-sm text-slate-800 flex-1">{{ c.client_id }}</span>
                    <span v-if="modal.rule.client_id === c.client_id" class="text-indigo-500">
                      <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/></svg>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <template v-if="modal.rule.type === 'http'">
              <div>
                <label class="label">子域名前缀</label>
                <div class="flex items-center">
                  <input v-model="modal.rule.subdomain" placeholder="如 nas" class="input-field font-mono text-sm rounded-r-none flex-1" />
                  <span class="px-3 h-10 flex items-center bg-slate-100 border border-l-0 border-slate-200 rounded-r-xl text-sm font-mono text-slate-500 whitespace-nowrap">.{{ httpDomain }}</span>
                </div>
                <p class="mt-1 text-xs text-slate-400">最终访问地址：<code class="bg-slate-100 px-1 rounded">{{ modal.rule.subdomain || 'xxx' }}.{{ httpDomain }}</code></p>
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
            <button class="btn-secondary" @click="modal.visible = false; clientDropdownOpen = false">取消</button>
            <button class="btn-primary" :disabled="modal.saving" @click="saveRule">
              {{ modal.saving ? '保存中...' : '确认保存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 设备详情抽屉 -->
    <Transition name="drawer">
      <div v-if="detail.visible" class="fixed inset-0 z-50 flex justify-end">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="detail.visible = false"></div>
        <div class="relative w-full max-w-lg bg-white shadow-2xl flex flex-col overflow-hidden">
          <!-- 抽屉顶部 -->
          <div class="px-6 py-5 border-b border-slate-100 bg-slate-50/80 flex items-center justify-between flex-shrink-0">
            <div class="flex items-center gap-3">
              <div class="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-500 flex items-center justify-center">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
              </div>
              <div>
                <div class="flex items-center gap-2">
                  <span class="font-bold text-slate-900 font-mono text-lg">{{ detail.clientId }}</span>
                  <span v-if="isOnline(detail.clientId)"
                        class="text-xs font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full">在线</span>
                  <span v-else class="text-xs text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">离线</span>
                </div>
                <div class="text-xs text-slate-400 mt-0.5">流量历史统计</div>
              </div>
            </div>
            <button class="text-slate-400 hover:text-slate-600 transition-colors p-1" @click="detail.visible = false">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
          </div>

          <!-- 抽屉内容 -->
          <div class="flex-1 overflow-y-auto p-6 space-y-6">
            <!-- 加载状态 -->
            <div v-if="detail.loading" class="flex items-center justify-center py-16">
              <div class="w-8 h-8 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
            </div>

            <template v-else-if="detail.data">
              <!-- 今日 / 本月 / 本年 -->
              <div>
                <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">流量汇总</div>
                <div class="grid grid-cols-3 gap-3">
                  <div v-for="item in summaryCards" :key="item.label"
                       :class="['rounded-xl p-4 flex flex-col gap-1', item.bg]">
                    <div :class="['text-xs font-bold uppercase tracking-wider mb-1', item.label_color]">{{ item.label }}</div>
                    <div :class="['text-base font-bold font-mono', item.value_color]">
                      ↑ {{ fmtBytes(item.data.bytes_out) }}
                    </div>
                    <div :class="['text-base font-bold font-mono', item.value_color2]">
                      ↓ {{ fmtBytes(item.data.bytes_in) }}
                    </div>
                    <div class="text-xs text-slate-400 mt-1">
                      HTTP {{ (item.data.http_requests || 0).toLocaleString() }}
                    </div>
                  </div>
                </div>
              </div>

              <!-- 累计总量 -->
              <div class="bg-slate-50 rounded-xl p-4 border border-slate-100">
                <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">累计总量</div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <div class="text-xs text-slate-400 mb-1">↑ 上行总计</div>
                    <div class="text-xl font-bold text-slate-800 font-mono">{{ fmtBytes(detail.data.total.bytes_out) }}</div>
                  </div>
                  <div>
                    <div class="text-xs text-slate-400 mb-1">↓ 下行总计</div>
                    <div class="text-xl font-bold text-slate-800 font-mono">{{ fmtBytes(detail.data.total.bytes_in) }}</div>
                  </div>
                  <div>
                    <div class="text-xs text-slate-400 mb-1">HTTP 请求</div>
                    <div class="text-lg font-bold text-slate-700 font-mono">{{ (detail.data.total.http_requests || 0).toLocaleString() }}</div>
                  </div>
                  <div>
                    <div class="text-xs text-slate-400 mb-1">TCP 连接</div>
                    <div class="text-lg font-bold text-slate-700 font-mono">{{ (detail.data.total.tcp_connections || 0).toLocaleString() }}</div>
                  </div>
                </div>
              </div>

              <!-- 近 30 天明细 -->
              <div>
                <div class="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-3">近 30 天明细</div>
                <div v-if="detail.data.daily.length === 0"
                     class="text-center py-8 text-slate-400 text-sm bg-slate-50 rounded-xl">
                  暂无历史记录（数据从启用此功能后开始累积）
                </div>
                <div v-else class="rounded-xl border border-slate-100 overflow-hidden">
                  <table class="w-full text-sm">
                    <thead>
                      <tr class="bg-slate-50 border-b border-slate-100">
                        <th class="py-3 px-4 text-left text-xs font-bold text-slate-500 uppercase">日期</th>
                        <th class="py-3 px-4 text-right text-xs font-bold text-slate-500 uppercase">↑ 上行</th>
                        <th class="py-3 px-4 text-right text-xs font-bold text-slate-500 uppercase">↓ 下行</th>
                        <th class="py-3 px-4 text-right text-xs font-bold text-slate-500 uppercase">HTTP</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-50">
                      <tr v-for="row in detail.data.daily" :key="row.date"
                          class="hover:bg-slate-50 transition-colors">
                        <td class="py-3 px-4 font-mono text-slate-600">{{ row.date }}</td>
                        <td class="py-3 px-4 text-right font-mono text-indigo-600">{{ fmtBytes(row.bytes_out) }}</td>
                        <td class="py-3 px-4 text-right font-mono text-violet-600">{{ fmtBytes(row.bytes_in) }}</td>
                        <td class="py-3 px-4 text-right text-slate-500">{{ (row.http_requests || 0).toLocaleString() }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </template>
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
import { clientApi, rulesApi, statsApi, portsApi, trafficApi, configApi } from '../api/index'
import logoUrl from '../assets/logo.svg'

function fmtBytes(n) {
  if (!n || n === 0) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(n) / Math.log(1024))
  return (n / Math.pow(1024, i)).toFixed(i ? 1 : 0) + ' ' + u[i]
}

function fmtUptime(s) {
  if (!s) return '-'
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), ss = s % 60
  return (h ? h + 'h ' : '') + (m ? m + 'm ' : '') + ss + 's'
}

function fmtTime(ts) {
  if (!ts) return '从未连接'
  const d = new Date(ts * 1000)
  const now = new Date()
  const diff = Math.floor((now - d) / 1000)
  if (diff < 60)   return `${diff}秒前`
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

const router = useRouter()
const auth   = useAuthStore()

const clients            = ref([])
const allTraffic         = ref([])
const rules              = ref([])
const stats              = ref({})
const availablePorts     = ref([])
const clientDropdownOpen = ref(false)
const httpDomain         = ref('')
const isBootstrapping    = ref(true)

// v-click-outside 指令
const vClickOutside = {
  mounted(el, binding) {
    el._clickOutside = (e) => { if (!el.contains(e.target)) binding.value(e) }
    document.addEventListener('mousedown', el._clickOutside)
  },
  unmounted(el) {
    document.removeEventListener('mousedown', el._clickOutside)
  },
}

const onlineCount = computed(() => clients.value.length)
const isOnline    = (clientId) => clients.value.some(c => c.client_id === clientId)

// 合并在线设备 + 历史流量，全量展示
const allDevices = computed(() => {
  const onlineMap = Object.fromEntries(clients.value.map(c => [c.client_id, c]))
  // 以历史流量为基准（包含离线设备）
  const fromHistory = allTraffic.value.map(t => {
    const onlineInfo = onlineMap[t.client_id]
    return {
      client_id:       t.client_id,
      online:          !!onlineInfo,
      online_seconds:  onlineInfo?.online_seconds ?? 0,
      last_active:     t.last_active,
      bytes_in:        t.bytes_in        + (onlineInfo?.traffic?.bytes_recv  ?? 0),
      bytes_out:       t.bytes_out       + (onlineInfo?.traffic?.bytes_sent  ?? 0),
      http_requests:   t.http_requests   + (onlineInfo?.traffic?.http_requests  ?? 0),
      tcp_connections: t.tcp_connections + (onlineInfo?.traffic?.tcp_connections ?? 0),
    }
  })
  // 在线设备中有但历史里没有的（首次连接）
  const historyIds = new Set(allTraffic.value.map(t => t.client_id))
  const onlyOnline = clients.value
    .filter(c => !historyIds.has(c.client_id))
    .map(c => ({
      client_id:       c.client_id,
      online:          true,
      online_seconds:  c.online_seconds,
      last_active:     c.connected_at,
      bytes_in:        c.traffic?.bytes_recv       ?? 0,
      bytes_out:       c.traffic?.bytes_sent        ?? 0,
      http_requests:   c.traffic?.http_requests     ?? 0,
      tcp_connections: c.traffic?.tcp_connections   ?? 0,
    }))
  return [...onlyOnline, ...fromHistory]
})

// ── 规则弹窗 ─────────────────────────────────────────────────────────────
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
  modal.value.error  = ''
  modal.value.saving = false
  if (rule) {
    const r = { ...rule }
    if (r.type === 'http' && httpDomain.value && r.subdomain) {
      const suffix = '.' + httpDomain.value
      if (r.subdomain.endsWith(suffix)) {
        r.subdomain = r.subdomain.slice(0, -suffix.length)
      }
    }
    modal.value.rule = r
  } else {
    modal.value.rule = defaultRule()
  }
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
    const rule = { ...modal.value.rule }
    if (rule.type === 'http' && httpDomain.value && rule.subdomain) {
      rule.subdomain = rule.subdomain.trim() + '.' + httpDomain.value
    }
    if (rule.id) {
      const { id, ...updates } = rule
      await rulesApi.update(id, updates)
    } else {
      await rulesApi.add(rule)
    }
    modal.value.visible  = false
    clientDropdownOpen.value = false
    await refresh()
  } catch (e) {
    modal.value.error = e.response?.data?.detail || '保存失败'
  } finally {
    modal.value.saving = false
  }
}

async function toggleRule(rule) {
  await rulesApi.toggle(rule.id)
  await refresh()
}

async function deleteRule(rule) {
  const label = rule.label || (rule.type === 'http' ? rule.subdomain : `:${rule.server_port}`)
  if (!confirm(`确认删除规则「${label}」？`)) return
  await rulesApi.delete(rule.id)
  await refresh()
}

// ── 设备详情抽屉 ─────────────────────────────────────────────────────────
const detail = ref({
  visible:  false,
  clientId: '',
  loading:  false,
  data:     null,
})

const summaryCards = computed(() => {
  if (!detail.value.data) return []
  return [
    {
      label: '今日', data: detail.value.data.today,
      bg: 'bg-indigo-50', label_color: 'text-indigo-500',
      value_color: 'text-indigo-700', value_color2: 'text-indigo-600',
    },
    {
      label: '本月', data: detail.value.data.month,
      bg: 'bg-violet-50', label_color: 'text-violet-500',
      value_color: 'text-violet-700', value_color2: 'text-violet-600',
    },
    {
      label: '本年', data: detail.value.data.year,
      bg: 'bg-emerald-50', label_color: 'text-emerald-500',
      value_color: 'text-emerald-700', value_color2: 'text-emerald-600',
    },
  ]
})

async function openDetail(clientId) {
  detail.value.visible  = true
  detail.value.clientId = clientId
  detail.value.loading  = true
  detail.value.data     = null
  try {
    detail.value.data = await trafficApi.getDetail(clientId)
  } catch {
    detail.value.data = null
  } finally {
    detail.value.loading = false
  }
}

// ── 数据刷新 ─────────────────────────────────────────────────────────────
async function refresh() {
  const [c, t, r, s] = await Promise.all([
    clientApi.list(), trafficApi.getAll(), rulesApi.list(), statsApi.get()
  ])
  clients.value    = c
  allTraffic.value = t
  rules.value      = r
  stats.value      = s
}

function logout() {
  auth.logout()
  router.push('/login')
}

let timer
onMounted(async () => {
  isBootstrapping.value = true
  const [cfgResult] = await Promise.allSettled([configApi.get(), refresh()])
  if (cfgResult.status === 'fulfilled') {
    httpDomain.value = cfgResult.value.http_domain
  }
  isBootstrapping.value = false
  timer = setInterval(refresh, 10000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
/* Vue 动画过渡 */
.list-enter-active, .list-leave-active { transition: all 0.4s ease; }
.list-enter-from, .list-leave-to { opacity: 0; transform: translateX(-20px); }

.modal-enter-active, .modal-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .transform, .modal-leave-to .transform { transform: scale(0.95) translateY(20px); }

.drawer-enter-active, .drawer-leave-active { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
.drawer-enter-from, .drawer-leave-to { opacity: 0; }
.drawer-enter-from .relative, .drawer-leave-to .relative { transform: translateX(100%); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
