import { defineStore } from 'pinia'
import { authApi } from '../api/index'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const res = await authApi.login(username, password)
      this.token = res.access_token
      localStorage.setItem('token', res.access_token)
    },
    logout() {
      this.token = null
      localStorage.removeItem('token')
    },
  },
})
