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
  list: () => http.get('/clients'),
}

export const rulesApi = {
  list:   ()              => http.get('/rules'),
  add:    (rule)          => http.post('/rules', rule),
  // rule 示例：
  // HTTP: { type:'http', client_id:'nas', subdomain:'nas.ruanpengpeng.cn',
  //         local_host:'127.0.0.1', local_port:5000, label:'NAS 管理页面' }
  // TCP:  { type:'tcp',  client_id:'mac', server_port:2222,
  //         local_host:'127.0.0.1', local_port:22,   label:'Mac SSH' }
  // RDP:  { type:'tcp',  app_protocol:'rdp', udp_enabled:true, client_id:'win',
  //         server_port:2233, local_host:'127.0.0.1', local_port:3389, label:'Windows RDP' }
  update: (ruleId, rule)  => http.put(`/rules/${ruleId}`, rule),
  toggle: (ruleId)        => http.patch(`/rules/${ruleId}/toggle`),
  delete: (ruleId)        => http.delete(`/rules/${ruleId}`),
}

export const portsApi = {
  available: () => http.get('/ports/available'),
}

export const configApi = {
  get: () => http.get('/config'),
}

export const statsApi = {
  get: () => http.get('/stats'),
}

export const trafficApi = {
  getAll:    ()           => http.get('/traffic'),
  getDetail: (clientId)  => http.get(`/traffic/${clientId}`),
}
