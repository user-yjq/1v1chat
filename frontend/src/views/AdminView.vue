<template>
  <div class="flex-1 overflow-y-auto p-6">
    <div class="max-w-5xl mx-auto">
      <h2 class="text-xl font-bold text-gray-800 mb-4">管理后台</h2>

      <div class="flex gap-2 mb-4">
        <button v-for="t in tabs" :key="t.key" @click="activeTab = t.key"
                :class="['px-4 py-2 rounded-xl text-sm font-medium transition-colors',
                         activeTab === t.key ? 'bg-brand-500 text-white' : 'bg-white text-gray-600 border']">
          {{ t.label }}
        </button>
      </div>

      <!-- 人设 -->
      <div v-if="activeTab === 'personas'">
        <div class="space-y-3">
          <div v-for="p in personas" :key="p.id" class="bg-white rounded-xl border border-gray-200">
            <div class="p-3 flex items-center justify-between cursor-pointer" @click="toggleEdit(p)">
              <div class="flex items-center gap-3 min-w-0">
                <img :src="p.avatar_url" class="w-10 h-10 rounded-xl object-cover bg-gray-100" />
                <div class="min-w-0">
                  <div class="text-sm font-medium">{{ p.name }}
                    <span v-if="!p.is_active" class="ml-1 text-xs text-gray-400">(已停用)</span>
                  </div>
                  <div class="text-xs text-gray-500 truncate">{{ p.scenario_name || '无剧本' }} · 照片:{{ p.photo_policy?.mode }}</div>
                </div>
              </div>
              <span class="text-xs text-brand-500">{{ editingId === p.id ? '收起' : '编辑' }}</span>
            </div>
            <div v-if="editingId === p.id" class="border-t px-4 py-3 space-y-2 text-sm">
              <div class="grid grid-cols-2 gap-2">
                <label class="text-gray-500">姓名 <input v-model="edit.name" class="form-input w-full" /></label>
                <label class="text-gray-500">年龄 <input v-model.number="edit.age" type="number" class="form-input w-full" /></label>
                <label class="text-gray-500">城市 <input v-model="edit.city" class="form-input w-full" /></label>
                <label class="text-gray-500">职业 <input v-model="edit.occupation" class="form-input w-full" /></label>
                <label class="text-gray-500 col-span-2">头像URL <input v-model="edit.avatar_url" class="form-input w-full" /></label>
              </div>
              <label class="block text-gray-500">性格
                <textarea v-model="edit.personality" rows="1" class="form-input w-full"></textarea>
              </label>
              <label class="block text-gray-500">说话风格
                <textarea v-model="edit.speaking_style" rows="1" class="form-input w-full"></textarea>
              </label>
              <label class="block text-gray-500">开场白
                <textarea v-model="edit.opening_message" rows="2" class="form-input w-full"></textarea>
              </label>
              <label class="block text-gray-500">照片策略 JSON
                <textarea v-model="edit.photo_policy_text" rows="4" class="form-input w-full font-mono text-xs"></textarea>
              </label>
              <label class="block text-gray-500">照片素材 JSON（URL 数组）
                <textarea v-model="edit.photo_assets_text" rows="2" class="form-input w-full font-mono text-xs"></textarea>
              </label>
              <div class="flex items-center justify-between pt-1">
                <label class="text-gray-500 text-xs"><input v-model="edit.is_active" type="checkbox" class="mr-1" />启用</label>
                <button @click="savePersona(p)" class="px-4 py-1.5 bg-brand-500 text-white rounded-lg text-xs">保存</button>
              </div>
            </div>
          </div>
        </div>
        <p v-if="!personas.length" class="text-gray-400 text-sm py-8 text-center">暂无数据</p>
      </div>

      <!-- 剧本 -->
      <div v-if="activeTab === 'scenarios'" class="space-y-3">
        <div class="bg-white rounded-xl border border-gray-200 p-4">
          <p class="text-sm font-medium mb-2 text-gray-700">新增剧本</p>
          <div class="grid grid-cols-3 gap-2">
            <input v-model="newScenario.slug" placeholder="slug 如 tea2" class="form-input" />
            <input v-model="newScenario.name" placeholder="名称" class="form-input" />
            <button @click="createScenario" class="px-4 py-2 bg-brand-500 text-white rounded-lg text-xs">创建</button>
          </div>
          <input v-model="newScenario.goal" placeholder="剧本总目标（一行）" class="form-input mt-2 w-full" />
          <textarea v-model="newScenario.stages_text" rows="6" placeholder='stages JSON 数组：[{"key":"greet","label":"刚认识","min_turns":4,"objective":"...","advance_on":[]}]' class="form-input mt-2 w-full font-mono text-xs"></textarea>
        </div>
        <div v-for="sc in scenarios" :key="sc.id" class="bg-white rounded-xl border border-gray-200 p-4 text-sm">
          <div class="flex justify-between">
            <span class="font-medium">{{ sc.name }} <span class="text-gray-400 text-xs ml-1">({{ sc.slug }})</span></span>
            <span class="text-xs text-gray-400">{{ sc.stages?.length || 0 }} 个阶段</span>
          </div>
          <p class="text-gray-500 text-xs mt-1">{{ sc.goal }}</p>
          <div class="text-xs text-gray-400 mt-1">{{ scenarioChain(sc) }}</div>
        </div>
      </div>

      <!-- 会话 -->
      <div v-if="activeTab === 'conversations'">
        <div class="bg-white rounded-xl border border-gray-200 divide-y">
          <div v-for="c in convs" :key="c.id" class="p-3 text-sm cursor-pointer hover:bg-gray-50"
               @click="loadConvMessages(c.id)">
            <div class="flex justify-between">
              <span class="font-medium">#{{ c.id }} {{ c.persona_name }} <span class="text-gray-400">(user {{ c.user_id }})</span></span>
              <span class="text-xs text-gray-400">{{ c.message_count }} 条 · 阶段{{ c.stage_idx }}</span>
            </div>
            <div class="text-xs text-gray-500 mt-1 flex justify-between">
              <span>红包{{ c.red_packets }} · 照片{{ c.photos_sent }}</span>
              <span>{{ fmt(c.last_message_at) }}</span>
            </div>
          </div>
        </div>
        <div v-if="convMsgs.length" class="mt-4 bg-white rounded-xl border border-gray-200 p-4 text-sm space-y-1 max-h-80 overflow-y-auto">
          <div v-for="m in convMsgs" :key="m.id">
            <span :class="['text-xs mr-1', m.sender_type === 'user' ? 'text-gray-500' : 'text-brand-600']">
              {{ m.sender_type === 'user' ? '对方' : 'AI' }} [{{ m.content_type }}]:
            </span>
            <span class="text-gray-700">{{ m.content }} {{ m.media_url ? '🖼' : '' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const tabs = [
  { key: 'personas', label: '人设' },
  { key: 'scenarios', label: '剧本' },
  { key: 'conversations', label: '会话' },
]
const activeTab = ref('personas')
const personas = ref<any[]>([])
const scenarios = ref<any[]>([])
const convs = ref<any[]>([])
const convMsgs = ref<any[]>([])
const editingId = ref<number | null>(null)
const edit = ref<any>({})
const newScenario = ref<any>({ slug: '', name: '', goal: '', stages_text: '[]' })

async function load() {
  try {
    personas.value = await userStore.api.get('/admin/personas').then(r => r.data)
    scenarios.value = await userStore.api.get('/admin/scenarios').then(r => r.data)
    convs.value = await userStore.api.get('/admin/conversations').then(r => r.data)
  } catch (e) { /* 403 时忽略 */ }
}

function toggleEdit(p: any) {
  if (editingId.value === p.id) { editingId.value = null; return }
  editingId.value = p.id
  edit.value = {
    ...p,
    photo_policy_text: JSON.stringify(p.photo_policy || {}, null, 2),
    photo_assets_text: JSON.stringify(p.photo_assets || [], null, 2),
  }
}

async function savePersona(p: any) {
  const body = { ...edit.value }
  delete body.photo_policy_text; delete body.photo_assets_text; delete body.scenario_name; delete body.stage_count
  try {
    body.photo_policy = JSON.parse(edit.value.photo_policy_text)
    body.photo_assets = JSON.parse(edit.value.photo_assets_text)
  } catch (e: any) { alert('JSON 格式错误'); return }
  body.scenario_id = p.scenario_id
  const res = await userStore.api.put(`/admin/personas/${p.id}`, body)
  await load()
  editingId.value = null
}

async function createScenario() {
  try {
    const stages = JSON.parse(newScenario.value.stages_text || '[]')
    await userStore.api.post('/admin/scenarios', { ...newScenario.value, stages })
    newScenario.value = { slug: '', name: '', goal: '', stages_text: '[]' }
    await load()
  } catch (e: any) { alert('创建失败，请检查 JSON/slug'); }
}

async function loadConvMessages(id: number) {
  convMsgs.value = await userStore.api.get(`/admin/conversations/${id}/messages`).then(r => r.data)
}

function scenarioChain(sc: any) {
  return (sc.stages || []).map((s: any) => `${s.key}:${s.label}`).join(' → ')
}

function fmt(t: string) {
  return t ? new Date(t).toLocaleString('zh-CN', { hour12: false }) : ''
}

onMounted(load)
</script>

<style scoped>
.form-input {
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 0.35rem 0.6rem;
  font-size: 0.85rem;
}
.form-input:focus {
  outline: none;
  border-color: #0ea5e9;
}
</style>
