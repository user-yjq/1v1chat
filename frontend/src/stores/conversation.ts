import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useUserStore } from './user'

export const useConversationStore = defineStore('conversation', () => {
  const userStore = useUserStore()

  async function fetchConversations() {
    const res = await userStore.api.get('/conversations')
    return res.data
  }

  async function createConversation(personaId?: number) {
    const res = await userStore.api.post('/conversations', {
      persona_id: personaId ?? null,
    })
    return res.data
  }

  async function getConversation(convId: number) {
    const res = await userStore.api.get(`/conversations/${convId}`)
    return res.data
  }

  async function getMessages(convId: number) {
    const res = await userStore.api.get(`/conversations/${convId}/messages`)
    return res.data
  }

  async function fetchPersonas() {
    const res = await userStore.api.get('/personas')
    return res.data
  }

  async function sendMessage(convId: number, content: string) {
    const res = await userStore.api.post('/chat/send', {
      conversation_id: convId,
      content,
      content_type: 'text',
    })
    return res.data
  }

  return { fetchConversations, createConversation, getConversation, getMessages, fetchPersonas, sendMessage }
})
