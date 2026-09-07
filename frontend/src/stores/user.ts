import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

// axios 实例提升到模块级：
// Pinia setup store 会把返回的函数当作 action 包装，axios 实例本身是“可调用函数对象”，
// 经 store 暴露后 .get/.post/.put/.delete 会丢失（此前 /api 调用全部报 api.get is not a function）。
export const http = axios.create({ baseURL: '/api' })

http.interceptors.request.use((config) => {
  const t = localStorage.getItem('token')
  if (t) config.headers.Authorization = `Bearer ${t}`
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    // token 过期/无效：清本地会话并回登录页（/login 本身不触发避免循环）
    if (err?.response?.status === 401 && window.location.pathname !== '/login') {
      localStorage.removeItem('token')
      window.location.assign('/login')
    }
    return Promise.reject(err)
  },
)

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref<any>(null)

  const username = computed(() => userInfo.value?.username || '')
  const nickname = computed(() => userInfo.value?.nickname || '')
  const avatar = computed(() => userInfo.value?.avatar_url || '')

  // 供组件/其他 store 使用的 HTTP 包装（普通对象，避免 Pinia action 包装副作用）
  const api = {
    get: (...args: Parameters<typeof http.get>) => http.get(...args),
    post: (...args: Parameters<typeof http.post>) => http.post(...args),
    put: (...args: Parameters<typeof http.put>) => http.put(...args),
    delete: (...args: Parameters<typeof http.delete>) => http.delete(...args),
  }

  async function login(username: string, password: string) {
    const res = await http.post('/auth/login', { username, password })
    token.value = res.data.access_token
    userInfo.value = res.data.user
    localStorage.setItem('token', token.value)
    return res.data
  }

  async function register(username: string, password: string, nickname: string) {
    const res = await http.post('/auth/register', { username, password, nickname })
    token.value = res.data.access_token
    userInfo.value = res.data.user
    localStorage.setItem('token', token.value)
    return res.data
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  async function fetchMe() {
    try {
      const res = await http.get('/auth/me')
      userInfo.value = res.data
    } catch (e) {
      logout()
    }
  }

  return { token, userInfo, username, nickname, avatar, login, register, logout, fetchMe, api }
})
