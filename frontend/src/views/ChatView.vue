<template>
  <div class="flex-1 flex flex-col h-full">
    <!-- 顶部信息栏 -->
    <div v-if="conversation" class="bg-white border-b px-6 py-3 flex items-center gap-3">
      <img :src="conversation.persona?.avatar_url" :alt="conversation.persona?.name"
           class="w-10 h-10 rounded-full object-cover bg-gray-100" />
      <div class="min-w-0">
        <h2 class="font-semibold text-gray-800 truncate">
          {{ conversation.persona?.name || conversation.title }}
        </h2>
        <p class="text-xs text-gray-400 truncate">
          {{ personaDesc }}
        </p>
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="msgListRef" class="flex-1 overflow-y-auto p-6 space-y-4 bg-[#f5f5f5]">
      <div v-for="msg in messages" :key="msg.id" class="flex items-end gap-2"
           :class="msg.sender_type === 'user' ? 'justify-end' : 'justify-start'">
        <img v-if="msg.sender_type === 'ai'" :src="conversation?.persona?.avatar_url"
             class="w-8 h-8 rounded-full object-cover bg-gray-100 shrink-0" />
        <div :class="['max-w-[70%]', msg.sender_type === 'user' ? 'order-2' : 'order-1']">
          <template v-if="msg.content_type === 'image'">
            <div :class="['inline-block overflow-hidden rounded-2xl msg-enter',
                          msg.sender_type === 'user' ? 'rounded-br-md' : 'rounded-bl-md shadow-sm']">
              <img :src="msg.media_url" alt="照片" class="max-w-56 max-h-80 block object-cover cursor-pointer"
                   @click="previewUrl = msg.media_url" />
            </div>
            <div v-if="msg.content" class="text-sm text-gray-500 mt-0.5">{{ msg.content }}</div>
          </template>
          <template v-else>
            <div :class="['inline-block px-4 py-2.5 rounded-2xl text-sm leading-relaxed msg-enter',
                          msg.sender_type === 'user'
                            ? 'bg-brand-500 text-white rounded-br-md'
                            : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm']">
              {{ msg.content }}
            </div>
          </template>
          <div :class="['text-xs text-gray-400 mt-1', msg.sender_type === 'user' ? 'text-right' : 'text-left']">
            {{ formatTime(msg.sent_at) }}
          </div>
        </div>
      </div>

      <!-- 正在输入 -->
      <div v-if="aiTyping" class="flex items-end gap-2 justify-start">
        <img :src="conversation?.persona?.avatar_url" class="w-8 h-8 rounded-full object-cover bg-gray-100" />
        <div class="bg-white border border-gray-200 rounded-2xl rounded-bl-md shadow-sm px-4 py-3">
          <div class="flex gap-1">
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
            <span class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片预览 -->
    <div v-if="previewUrl" class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-6" @click="previewUrl = ''">
      <img :src="previewUrl" class="max-h-[85vh] max-w-full rounded-xl" />
    </div>

    <!-- 输入区 -->
    <div class="bg-white border-t p-4">
      <div class="flex gap-3 items-end max-w-4xl mx-auto">
        <textarea
          v-model="inputText"
          @keydown.enter.exact.prevent="sendMessage"
          placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
          rows="1"
          class="flex-1 px-4 py-3 border border-gray-200 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 text-sm"
          :disabled="sending"
        ></textarea>
        <button @click="sendMessage" :disabled="!inputText.trim() || sending"
                class="px-6 py-3 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-300 text-white rounded-2xl font-medium text-sm transition-colors">
          {{ sending ? '...' : '发送' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { useConversationStore } from '@/stores/conversation'

const props = defineProps<{ id: string }>()
const route = useRoute()
const convStore = useConversationStore()

const messages = ref<any[]>([])
const conversation = ref<any>(null)
const inputText = ref('')
const sending = ref(false)
const aiTyping = ref(false)
const previewUrl = ref('')
const msgListRef = ref<HTMLElement>()

const convId = Number(props.id) || Number(route.params.id)

const personaDesc = computed(() => {
  const p = conversation.value?.persona
  if (!p) return ''
  return `${p.age}岁 · ${p.city} · ${p.occupation}`
})

function formatTime(t: string) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const sameDay = d.toDateString() === now.toDateString()
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }) +
    (sameDay ? '' : ' ' + d.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' }))
}

function scrollToBottom() {
  nextTick(() => {
    if (msgListRef.value) msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  })
}

async function loadConversation() {
  try {
    conversation.value = await convStore.getConversation(convId)
    document.title = `${conversation.value.persona?.name || '对话'} · 1v1Chat`
  } catch (e) { /* ignore */ }
}

async function loadMessages() {
  try {
    messages.value = await convStore.getMessages(convId)
    scrollToBottom()
  } catch (e) { /* ignore */ }
}

async function sendMessage() {
  const text = inputText.value.trim()
  if (!text || sending.value) return
  inputText.value = ''
  sending.value = true
  aiTyping.value = true
  scrollToBottom()
  try {
    const result = await convStore.sendMessage(convId, text)
    messages.value.push(result.user_message)
    scrollToBottom()
    await new Promise(r => setTimeout(r, 400))  // 更真实的“正在输入”感
    for (const m of result.ai_messages || []) {
      messages.value.push(m)
      scrollToBottom()
    }
  } catch (e) {
    // ignore
  } finally {
    aiTyping.value = false
    sending.value = false
    scrollToBottom()
  }
}

onMounted(async () => {
  await loadConversation()
  await loadMessages()
})
</script>
