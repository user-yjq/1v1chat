<template>
  <div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-100 to-blue-50">
    <div class="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
      <div class="text-center mb-8">
        <div class="w-16 h-16 bg-brand-500 rounded-2xl flex items-center justify-center text-white font-bold text-2xl mx-auto mb-4">1v1</div>
        <h2 class="text-2xl font-bold text-gray-800">登录</h2>
        <p class="text-gray-500 text-sm mt-1">欢迎回来</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">用户名</label>
          <input v-model="form.username" type="text" placeholder="输入用户名" required
                 class="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">密码</label>
          <input v-model="form.password" type="password" placeholder="输入密码" required
                 class="w-full px-4 py-2.5 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent text-sm" />
        </div>
        <div v-if="error" class="text-red-500 text-sm text-center">{{ error }}</div>
        <button type="submit" :disabled="loading"
                class="w-full py-2.5 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-300 text-white rounded-xl font-medium text-sm transition-colors">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="text-center mt-6">
        <span class="text-gray-500 text-sm">没有账号？</span>
        <router-link to="/register" class="text-brand-600 text-sm font-medium ml-1">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await userStore.login(form.value.username, form.value.password)
    router.push('/home')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>
