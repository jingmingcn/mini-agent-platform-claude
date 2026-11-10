<template>
  <div class="page" v-loading="loading">
    <div class="page-header">
      <div><h2>{{ isNew ? '新建智能体' : `编辑：${form.name}` }}</h2>
        <div class="sub" v-if="!isNew">状态：<el-tag size="small" :type="agentStatusMap[status].type">{{ agentStatusMap[status].label }}</el-tag></div></div>
      <div>
        <el-button @click="$router.push('/agents')">返回</el-button>
        <template v-if="auth.canWrite">
          <el-button type="primary" :loading="saving" @click="save(false)">保存</el-button>
          <el-button type="success" :loading="saving" @click="save(true)">保存并发布</el-button>
        </template>
      </div>
    </div>
    <el-form ref="formRef" :model="form" :rules="rules" label-width="130px" :disabled="!auth.canWrite">
      <div class="card block">
        <div class="section-title">基本信息</div>
        <el-row :gutter="16">
          <el-col :md="12"><el-form-item label="名称" prop="name"><el-input v-model="form.name" maxlength="128" /></el-form-item></el-col>
          <el-col :md="6"><el-form-item label="头像"><el-input v-model="form.avatar" placeholder="Emoji 或图片 URL" /></el-form-item></el-col>
          <el-col :md="6"><el-form-item label="分类"><el-input v-model="form.category" placeholder="如：科研 / 客服" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" maxlength="1024" show-word-limit /></el-form-item>
      </div>

      <div class="card block">
        <div class="section-title">模型配置</div>
        <el-row :gutter="16">
          <el-col :md="12"><el-form-item label="绑定模型">
            <el-select v-model="form.llm_config_id" clearable placeholder="使用平台默认模型" style="width: 100%">
              <el-option v-for="m in chatModels" :key="m.id" :label="`${m.name}（${m.chat_model}）`" :value="m.id" :disabled="!m.enabled" />
            </el-select></el-form-item></el-col>
          <el-col :md="6"><el-form-item label="Temperature">
            <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" placeholder="继承" /></el-form-item></el-col>
          <el-col :md="6"><el-form-item label="Max Tokens">
            <el-input-number v-model="form.max_tokens" :min="1" :max="200000" placeholder="继承" controls-position="right" /></el-form-item></el-col>
        </el-row>
      </div>

      <div class="card block">
        <div class="section-title">Prompt 配置</div>
        <el-form-item label="从模板导入">
          <el-select placeholder="选择 Prompt 模板" style="width: 320px" @change="applyTemplate" :model-value="undefined">
            <el-option v-for="p in templates" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="系统提示词" prop="system_prompt">
          <el-input v-model="form.system_prompt" type="textarea" :rows="8" maxlength="20000" show-word-limit
                    placeholder="例如：你是一个专业的科研助手，回答需严谨并给出依据……" />
        </el-form-item>
        <el-form-item label="欢迎语"><el-input v-model="form.welcome_message" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="推荐问题">
          <div style="width: 100%">
            <div v-for="(_, i) in form.suggested_questions" :key="i" class="q-row">
              <el-input v-model="form.suggested_questions[i]" maxlength="100" />
              <el-button icon="Delete" circle @click="form.suggested_questions.splice(i, 1)" />
            </div>
            <el-button v-if="form.suggested_questions.length < 10" icon="Plus" size="small" @click="form.suggested_questions.push('')">添加问题</el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="!isNew && versions.length" label="历史版本">
          <el-select placeholder="回滚到历史版本" style="width: 320px" :model-value="undefined" @change="(id: number) => form.system_prompt = versions.find(v => v.id === id)!.content">
            <el-option v-for="v in versions" :key="v.id" :label="`v${v.version} · ${fmtTime(v.created_at)}`" :value="v.id" />
          </el-select>
        </el-form-item>
      </div>

      <div class="card block">
        <div class="section-title">知识库配置（RAG）</div>
        <el-form-item label="启用知识库检索"><el-switch v-model="form.enable_rag" /></el-form-item>
        <template v-if="form.enable_rag">
          <el-form-item label="关联知识库">
            <el-select v-model="form.knowledge_base_ids" multiple placeholder="可多选，联合检索" style="width: 100%">
              <el-option v-for="kb in kbs" :key="kb.id" :label="`${kb.name}（${kb.document_count} 文档 / ${kb.chunk_count} 切片）`" :value="kb.id" />
            </el-select>
          </el-form-item>
          <el-row :gutter="16">
            <el-col :md="8"><el-form-item label="Top-K"><el-input-number v-model="form.rag_top_k" :min="1" :max="20" /></el-form-item></el-col>
            <el-col :md="8"><el-form-item label="相似度阈值"><el-input-number v-model="form.rag_score_threshold" :min="0" :max="1" :step="0.05" :precision="2" /></el-form-item></el-col>
          </el-row>
          <el-form-item label="无结果策略">
            <el-radio-group v-model="form.rag_no_result_policy">
              <el-radio value="fallback">兜底回答（声明基于通用知识）</el-radio>
              <el-radio value="strict">严格拒答（不调用模型）</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="form.rag_no_result_policy === 'strict'" label="拒答话术">
            <el-input v-model="form.rag_refuse_message" placeholder="抱歉，知识库中没有找到相关内容……" />
          </el-form-item>
        </template>
      </div>

      <div class="card block">
        <div class="section-title">记忆配置</div>
        <el-form-item label="多轮上下文记忆"><el-switch v-model="form.enable_memory" /></el-form-item>
        <el-row :gutter="16" v-if="form.enable_memory">
          <el-col :md="8"><el-form-item label="最多历史消息"><el-input-number v-model="form.memory_max_messages" :min="0" :max="200" /></el-form-item></el-col>
          <el-col :md="8"><el-form-item label="历史 Token 上限"><el-input-number v-model="form.memory_max_tokens" :min="200" :max="128000" :step="500" /></el-form-item></el-col>
        </el-row>
      </div>

      <div class="card block">
        <div class="section-title">工具配置</div>
        <el-form-item label="启用工具调用"><el-switch v-model="form.enable_tools" /></el-form-item>
        <el-form-item v-if="form.enable_tools" label="可用工具">
          <el-checkbox-group v-model="form.tools">
            <el-checkbox v-for="t in tools" :key="t.name" :value="t.name">{{ t.name }}<span class="muted">（{{ t.description }}）</span></el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <div class="muted" style="margin-left: 130px">需模型支持 OpenAI function calling（如 DeepSeek、Qwen、Kimi、GPT 系列）。</div>
      </div>

      <div class="card block">
        <div class="section-title">发布配置</div>
        <el-row :gutter="16">
          <el-col :md="8"><el-form-item label="访问权限">
            <el-radio-group v-model="form.access_level"><el-radio value="public">公开</el-radio><el-radio value="restricted">受限</el-radio></el-radio-group>
          </el-form-item></el-col>
          <el-col :md="8"><el-form-item label="首页推荐"><el-switch v-model="form.is_featured" /></el-form-item></el-col>
          <el-col :md="8"><el-form-item label="排序权重"><el-input-number v-model="form.sort_order" /></el-form-item></el-col>
        </el-row>
        <el-form-item v-if="form.access_level === 'restricted' && !isNew" label="授权用户">
          <el-select v-model="permittedUsers" multiple filterable remote :remote-method="searchUsers" placeholder="搜索用户昵称" style="width: 100%">
            <el-option v-for="u in userOptions" :key="u.id" :label="`${u.nickname || '未命名'} (#${u.id})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <div v-if="form.access_level === 'restricted' && isNew" class="muted" style="margin-left: 130px">保存后可配置授权用户。</div>
      </div>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { agentApi, kbApi, modelApi, promptApi, systemApi, userApi } from '@/api'
import type { KnowledgeBase, LLMConfig, Prompt, ToolInfo } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { agentStatusMap, fmtTime } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const isNew = computed(() => !route.params.id)
const loading = ref(false)
const saving = ref(false)
const status = ref<'draft' | 'published' | 'offline'>('draft')
const formRef = ref<FormInstance>()
const models = ref<LLMConfig[]>([])
const kbs = ref<KnowledgeBase[]>([])
const templates = ref<Prompt[]>([])
const versions = ref<Prompt[]>([])
const tools = ref<ToolInfo[]>([])
const permittedUsers = ref<number[]>([])
const userOptions = ref<{ id: number; nickname: string | null }[]>([])
const chatModels = computed(() => models.value.filter((m) => m.chat_model))

const form = reactive({
  name: '', description: '', avatar: '🤖', category: '', system_prompt: '', welcome_message: '',
  suggested_questions: [] as string[], llm_config_id: null as number | null, temperature: undefined as number | undefined,
  max_tokens: undefined as number | undefined, knowledge_base_ids: [] as number[], enable_rag: false, rag_top_k: 5,
  rag_score_threshold: 0.3, rag_no_result_policy: 'fallback' as 'fallback' | 'strict', rag_refuse_message: '',
  enable_memory: true, memory_max_messages: 20, memory_max_tokens: 4000, enable_tools: false, tools: [] as string[],
  access_level: 'public' as 'public' | 'restricted', sort_order: 0, is_featured: false,
})
const rules: FormRules = {
  name: [{ required: true, message: '请输入名称' }],
  system_prompt: [{ required: true, message: '请配置系统提示词' }],
}

function applyTemplate(id: number) {
  const t = templates.value.find((p) => p.id === id)
  if (t) form.system_prompt = t.content
}
async function searchUsers(q: string) {
  const res = await userApi.list({ keyword: q || undefined, page_size: 50 })
  const existing = userOptions.value.filter((u) => permittedUsers.value.includes(u.id))
  userOptions.value = [...existing, ...res.items.filter((u) => !permittedUsers.value.includes(u.id))]
}

async function save(publish: boolean) {
  await formRef.value?.validate()
  saving.value = true
  try {
    const payload: Record<string, any> = { ...form, suggested_questions: form.suggested_questions.filter((q) => q.trim()) }
    payload.temperature = form.temperature ?? null
    payload.max_tokens = form.max_tokens ?? null
    const agent = isNew.value ? await agentApi.create(payload) : await agentApi.update(Number(route.params.id), payload)
    if (!isNew.value && form.access_level === 'restricted') await agentApi.setPermissions(agent.id, permittedUsers.value)
    if (publish) await agentApi.publish(agent.id)
    ElMessage.success(publish ? '已保存并发布' : '已保存')
    if (isNew.value) router.replace(`/agents/${agent.id}`)
    else status.value = publish ? 'published' : agent.status
  } finally { saving.value = false }
}

onMounted(async () => {
  loading.value = true
  try {
    const [m, k, t, tl] = await Promise.all([modelApi.list(), kbApi.list(), promptApi.list(), systemApi.tools()])
    models.value = m; kbs.value = k; templates.value = t; tools.value = tl
    if (!isNew.value) {
      const id = Number(route.params.id)
      const a = await agentApi.get(id)
      Object.assign(form, {
        ...a, description: a.description || '', avatar: a.avatar || '', category: a.category || '',
        welcome_message: a.welcome_message || '', suggested_questions: a.suggested_questions || [],
        temperature: a.temperature ?? undefined, max_tokens: a.max_tokens ?? undefined,
        rag_refuse_message: a.rag_refuse_message || '', tools: a.tools || [],
      })
      status.value = a.status
      versions.value = await promptApi.list(id)
      if (a.access_level === 'restricted') {
        const perms = await agentApi.permissions(id)
        userOptions.value = perms
        permittedUsers.value = perms.map((p) => p.id)
      }
    }
  } finally { loading.value = false }
})
</script>

<style scoped>
.block { margin-bottom: 16px; }
.q-row { display: flex; gap: 8px; margin-bottom: 8px; }
</style>
