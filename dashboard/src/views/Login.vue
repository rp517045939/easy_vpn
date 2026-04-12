<template>
  <div class="login-wrap">
    <div class="login-box">
      <h2>easy_vpn</h2>
      <form @submit.prevent="submit">
        <div class="field">
          <label>用户名</label>
          <input v-model="form.username" type="text" autocomplete="username" required />
        </div>
        <div class="field">
          <label>密码</label>
          <input v-model="form.password" type="password" autocomplete="current-password" required />
        </div>
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" :disabled="loading">{{ loading ? '登录中...' : '登录' }}</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
    error.value = '用户名或密码错误'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.login-box {
  background: #fff;
  padding: 40px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0,0,0,.1);
  width: 320px;
}
h2 { text-align: center; margin: 0 0 28px; font-size: 22px; }
.field { margin-bottom: 16px; }
label { display: block; margin-bottom: 6px; font-size: 13px; color: #555; }
input {
  width: 100%; padding: 8px 10px; box-sizing: border-box;
  border: 1px solid #d9d9d9; border-radius: 4px; font-size: 14px;
}
input:focus { outline: none; border-color: #4096ff; }
button {
  width: 100%; padding: 10px; background: #1677ff; color: #fff;
  border: none; border-radius: 4px; font-size: 15px; cursor: pointer;
}
button:disabled { opacity: .6; cursor: not-allowed; }
.error { color: #ff4d4f; font-size: 13px; margin: -8px 0 12px; }
</style>
