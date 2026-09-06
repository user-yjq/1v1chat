<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" @click.self="$emit('close')">
    <div class="w-full max-w-md bg-white rounded-2xl shadow-xl p-6">
      <div class="flex items-center justify-between mb-1">
        <h3 class="text-lg font-semibold text-gray-800">账户数据</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-xl leading-none">×</button>
      </div>
      <p class="text-xs text-gray-500 mb-4">
        数据权口径：可随时导出全部数据，或彻底删除账号与全部对话（删除后不可恢复）。
      </p>

      <!-- 导出 -->
      <div class="rounded-xl border border-gray-200 p-4 mb-4">
        <div class="text-sm font-medium text-gray-800 mb-1">导出我的数据</div>
        <p class="text-xs text-gray-500 mb-3">下载 JSON：账号信息 + 全部会话与消息（不含内部运行数据）。</p>
        <button
          @click="exportData"
          :disabled="busy"
          class="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 disabled:opacity-50 text-white rounded-xl font-medium text-sm transition-colors"
        >{{ exporting ? '导出中…' : '下载 JSON' }}</button>
      </div>

      <!-- 删除 -->
      <div class="rounded-xl border border-red-200 bg-red-50 p-4">
        <div class="text-sm font-medium text-red-700 mb-1">删除账号与全部数据</div>
        <p class="text-xs text-red-600 mb-3">将彻底删除账号、全部会话与消息（含归档），<b>不可恢复</b>。共享人设/剧本目录不受影响。</p>
        <label class="flex items-center gap-2 text-xs text-gray-600 mb-3">
          <input v-model="confirmed" type="checkbox" class="accent-red-500" />
          我已了解删除后不可恢复
        </label>
        <button
          @click="confirmDelete"
          :disabled="!confirmed || busy"
          class="px-3 py-1.5 bg-red-500 hover:bg-red-600 disabled:opacity-50 text-white rounded-xl font-medium text-sm transition-colors"
        >{{ deleting ? '删除中…' : (needSecond ? '再次点击，确认删除' : '删除账号与全部数据') }}</button>
      </div>

      <p v-if="error" class="text-xs text-red-500 mt-3">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const emit = defineEmits<{ (e: 'close'): void }>()

const userStore = useUserStore()
const router = useRouter()

const busy = ref(false)
const exporting = ref(false)
const deleting = ref(false)
const confirmed = ref(false)
const needSecond = ref(false)
const error = ref('')

async function exportData() {
  busy.value = true
  exporting.value = true
  error.value = ''
  try {
    const res = await userStore.api.get('/me/data', { responseType: 'blob' })
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `1v1chat-data-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '导出失败，请稍后重试'
  } finally {
    busy.value = false
    exporting.value = false
  }
}

async function confirmDelete() {
  if (!needSecond.value) {
    needSecond.value = true
    return
  }
  busy.value = true
  deleting.value = true
  error.value = ''
  try {
    await userStore.api.delete('/me/data')
    userStore.logout()
    emit('close')
    await router.push('/login')
  } catch (e: any) {
    error.value = e?.response?.data?.detail || '删除失败，请稍后重试'
  } finally {
    busy.value = false
    deleting.value = false
  }
}
</script>
