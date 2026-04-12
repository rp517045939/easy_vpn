import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截：自动带上 token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：401 跳转登录
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (username, password) => http.post('/auth/login', { username, password }),
}

export const clientApi = {
  list: ()                          => http.get('/clients'),
  getRules: (clientId)              => http.get(`/clients/${clientId}/rules`),
  addRule: (clientId, rule)         => http.post(`/clients/${clientId}/rules`, rule),
  updateRule: (clientId, subdomain, rule) => http.put(`/clients/${clientId}/rules/${subdomain}`, rule),
  deleteRule: (clientId, subdomain) => http.delete(`/clients/${clientId}/rules/${subdomain}`),
}

export const statsApi = {
  get: () => http.get('/stats'),
}
