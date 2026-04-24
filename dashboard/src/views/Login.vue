<template>
  <div class="min-h-screen bg-slate-50 flex items-center justify-center relative overflow-hidden font-sans">
    <!-- Atmospheric Background Blobs -->
    <div class="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
      <div class="absolute -top-[20%] -left-[10%] w-[70%] h-[70%] rounded-full bg-indigo-200/40 blur-3xl animate-pulse duration-[4000ms]"></div>
      <div class="absolute top-[20%] -right-[10%] w-[60%] h-[60%] rounded-full bg-violet-200/40 blur-3xl animate-pulse duration-[5000ms]"></div>
    </div>

    <div class="relative z-10 w-full max-w-md px-4 sm:px-0 perspective-[2000px]">
      <div class="card p-8 sm:p-10 transform-gpu transition-transform duration-500 hover:rotate-x-[2deg] hover:rotate-y-[-2deg]">
        <div class="flex flex-col items-center mb-8">
          <img :src="logoUrl" alt="EASY_VPN Nexus" class="h-14 w-auto mb-4" />
          <p class="text-slate-500 mt-2 font-medium">登录以管理您的内网穿透服务</p>
        </div>

        <form @submit.prevent="submit" class="space-y-5">
          <div>
            <label class="label">用户名</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
              </div>
              <input v-model="form.username" type="text" autocomplete="username" required class="input-field pl-10" placeholder="请输入用户名" />
            </div>
          </div>
          
          <div>
            <label class="label">密码</label>
            <div class="relative">
              <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg class="h-5 w-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
              </div>
              <input v-model="form.password" type="password" autocomplete="current-password" required class="input-field pl-10" placeholder="请输入密码" />
            </div>
          </div>

          <Transition name="fade">
            <div v-if="error" class="p-3 rounded-lg bg-red-50 border border-red-100 flex items-start gap-2">
              <svg class="w-5 h-5 text-red-500 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              <p class="text-sm text-red-600 font-medium">{{ error }}</p>
            </div>
          </Transition>

          <button type="submit" class="btn-primary w-full flex justify-center items-center gap-2 mt-2" :disabled="loading">
            <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ loading ? '正在验证...' : '登录系统' }}
          </button>
        </form>
      </div>
      
      <p class="text-center text-slate-400 text-sm mt-8">
        &copy; {{ new Date().getFullYear() }} EASY_VPN. All rights reserved.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import logoUrl from '../assets/logo.svg'

const router = useRouter()
const auth   = useAuthStore()

const form    = ref({ username: '', password: '' })
const error   = ref('')
const loading = ref(false)

async function submit() {
  error.value   = ''
  loading.value = true
  try {
    await auth.login(form.value.username, form.value.password)
    router.push('/')
  } catch {
    error.value = '用户名或密码错误，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
