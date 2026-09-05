import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { useRouter } from 'vue-router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref<any>(null)

  const username = computed(() => userInfo.value?.username || '')
  const nickname = computed(() => userInfo.value?.nickname || '')
  const avatar = computed(() => userInfo.value?.avatar_url || '')

  const api = axios.create({
    baseURL: '/api',
    headers: { Authorization: token.value ? `Bearer ${token.value}` : '' },
  })

  api.interceptors.request.use((config) => {
    if (token.value) config.headers.Authorization = `Bearer ${token.value}`
    return config
  })

  async function login(username: string, password: string) {
    const res = await api.post('/auth/login', { username, password })
    token.value = res.data.access_token
    userInfo.value = res.data.user
    localStorage.setItem('token', token.value)
    return res.data
  }

  async function register(username: string, password: string, nickname: string) {
    const res = await api.post('/auth/register', { username, password, nickname })
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
      const res = await api.get('/auth/me')
      userInfo.value = res.data
    } catch (e) {
      logout()
    }
  }

  return { token, userInfo, username, nickname, avatar, login, register, logout, fetchMe, api }
})
