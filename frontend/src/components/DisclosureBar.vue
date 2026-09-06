<template>
  <div v-if="show"
       class="bg-amber-50 border-b border-amber-200 px-6 py-2 text-xs text-amber-800 flex items-center gap-2">
    <span class="shrink-0" aria-hidden="true">⚠️</span>
    <span class="flex-1 min-w-0">{{ text }}</span>
    <router-link to="/terms" class="underline shrink-0 whitespace-nowrap">用户协议</router-link>
    <router-link to="/privacy" class="underline shrink-0 whitespace-nowrap">隐私说明</router-link>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const DEFAULT_TEXT = '对面是AI扮演的虚拟角色，仅供角色扮演/销售陪练/反诈演练等实验用途，请勿当真，不要进行真实交易或转账。'
const show = ref(true)
const text = ref(DEFAULT_TEXT)

onMounted(async () => {
  try {
    const res = await userStore.api.get('/meta')
    const d = res.data?.disclosure || {}
    show.value = d.enabled !== false
    text.value = d.text || DEFAULT_TEXT
  } catch (e) {
    // 后端不可达时保持披露（fail-safe），不静默隐藏
    show.value = true
    text.value = DEFAULT_TEXT
  }
})
</script>
