<template>
  <div class="flex h-screen bg-gray-100">
    <!-- 侧边栏 -->
    <aside class="w-72 bg-white border-r flex flex-col shadow-sm">
      <div class="p-4 border-b flex items-center gap-3">
        <div class="w-10 h-10 bg-brand-500 rounded-full flex items-center justify-center text-white font-bold text-lg">1v1</div>
        <div>
          <h1 class="font-semibold text-gray-800 text-sm">1v1Chat</h1>
          <p class="text-xs text-gray-500">自适应角色聊天</p>
        </div>
      </div>

      <!-- 新建对话 -->
      <div class="p-3">
        <button @click="startNewChat" class="w-full py-2.5 px-4 bg-brand-500 hover:bg-brand-600 text-white rounded-xl font-medium text-sm transition-colors flex items-center justify-center gap-2">
          <span class="text-lg">+</span> 新对话
        </button>
      </div>

      <!-- 对话列表 -->
      <div class="flex-1 overflow-y-auto px-2">
        <div v-for="conv in conversations" :key="conv.id"
             @click="selectConversation(conv.id)"
             :class="['p-3 rounded-xl cursor-pointer mb-1 transition-colors', currentConvId === conv.id ? 'bg-brand-50 border border-brand-100' : 'hover:bg-gray-50']">
          <div class="text-sm font-medium text-gray-800 truncate">{{ conv.title }}</div>
          <div class="text-xs text-gray-500 mt-0.5">{{ formatTime(conv.last_message_at) }}</div>
        </div>
        <div v-if="conversations.length === 0" class="text-center text-gray-400 text-sm py-8">
          暂无对话
        </div>
      </div>

      <!-- 用户信息 -->
      <div class="p-3 border-t">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center text-sm">{{ userStore.username?.[0]?.toUpperCase() }}</div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-gray-700 truncate">{{ userStore.nickname || userStore.username }}</div>
            <div class="text-xs text-gray-400">{{ userStore.username }}</div>
          </div>
          <div class="flex items-center gap-2">
            <button v-if="userStore.userInfo?.is_admin" @click="router.push('/admin')" class="text-gray-400 hover:text-brand-600 text-sm" title="管理后台">后台</button>
            <button @click="logout" class="text-gray-400 hover:text-red-500 text-sm" title="退出">登出</button>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主聊天区 -->
    <main class="flex-1 flex flex-col">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useConversationStore } from '@/stores/conversation'

const router = useRouter()
const userStore = useUserStore()
const convStore = useConversationStore()

const conversations = ref<any[]>([])
const currentConvId = ref<number | null>(null)

const formatTime = (t: string) => {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString('zh-CN')
}

const loadConversations = async () => {
  try {
    const res = await convStore.fetchConversations()
    conversations.value = res
  } catch (e) {
    // ignore
  }
}

const startNewChat = () => {
  router.push('/home')  // 到首页选择人设再开聊
}

const selectConversation = (id: number) => {
  currentConvId.value = id
  router.push(`/chat/${id}`)
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}

onMounted(async () => {
  if (!userStore.token) {
    router.push('/login')
    return
  }
  await loadConversations()
})
</script>
