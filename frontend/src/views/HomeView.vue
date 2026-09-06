<template>
  <div class="flex-1 overflow-y-auto p-8">
    <div class="max-w-3xl mx-auto">
      <div class="text-center mb-8">
        <h2 class="text-2xl font-bold text-gray-800 mb-2">选一个“微信好友”开始聊天</h2>
        <p class="text-sm text-gray-500">每个人设都有不同的性格、聊天方式和“照片原则”，试试看你能聊到哪一步</p>
      </div>

      <div v-if="loading" class="text-center text-gray-400 py-16">加载人设中...</div>

      <div v-else-if="error" class="text-center text-red-400 py-16">{{ error }}</div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-for="p in personas" :key="p.id"
             @click="startWith(p)"
             class="bg-white border border-gray-200 rounded-2xl p-4 flex gap-3 cursor-pointer hover:shadow-md hover:border-brand-500 transition-all">
          <img :src="p.avatar_url" :alt="p.name"
               class="w-16 h-16 rounded-2xl object-cover bg-gray-100 shrink-0" />
          <div class="min-w-0">
            <div class="flex items-baseline gap-2">
              <span class="font-semibold text-gray-800">{{ p.name }}</span>
              <span class="text-xs text-gray-400">{{ p.age }}岁 · {{ p.city }} · {{ p.occupation }}</span>
            </div>
            <p class="text-xs text-gray-500 mt-1 line-clamp-2">{{ p.bio }}</p>
            <span class="inline-block mt-2 text-xs px-2 py-0.5 rounded-full bg-brand-50 text-brand-700">
              {{ policyLabel(p.photo_policy) }}
            </span>
          </div>
        </div>
      </div>
      <p v-if="!loading && personas.length === 0" class="text-center text-gray-400 py-10">还没有可用的人设，请先执行 `python seed.py`</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConversationStore } from '@/stores/conversation'

const router = useRouter()
const convStore = useConversationStore()
const personas = ref<any[]>([])
const loading = ref(true)
const error = ref('')

const POLICY_TEXT: Record<string, string> = {
  instant: '爱分享，要照片就给',
  friendly: '聊熟了才给照片',
  red_packet: '收红包才解锁照片',
  dangle: '一直吊着不给照片',
}

function policyLabel(policy: any) {
  return POLICY_TEXT[policy?.mode] ?? '随缘'
}

async function startWith(p: any) {
  const conv = await convStore.createConversation(p.id)
  router.push(`/chat/${conv.id}`)
}

onMounted(async () => {
  try {
    personas.value = await convStore.fetchPersonas()
  } catch (e) {
    error.value = '人设加载失败，请刷新重试；若持续失败请联系管理员'
  } finally {
    loading.value = false
  }
})
</script>
