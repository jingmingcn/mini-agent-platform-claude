<template>
  <div class="page">
    <div class="page-header">
      <div><h2>大模型配置</h2><div class="sub">统一使用 OpenAI 兼容接口；API Key 服务端加密存储，任何接口都不会返回明文</div></div>
      <el-button v-if="auth.canWrite" type="primary" icon="Plus" @click="openCreate">新增模型</el-button>
    </div>
    <div class="card">
      <el-table :data="list" v-loading="loading">
        <el-table-column label="名称" min-width="170">
          <template #default="{ row }: { row: any }"><b>{{ row.name }}</b> <el-tag v-if="row.is_default" size="small" type="success">默认</el-tag>
            <div class="muted">{{ row.provider }}</div></template>
        </el-table-column>
        <el-table-column prop="base_url" label="Base URL" min-width="230" show-overflow-tooltip />
        <el-table-column label="API Key" width="110"><template #default="{ row }: { row: any }"><span class="mono">{{ row.api_key_masked }}</span></template></el-table-column>
        <el-table-column label="Chat / Embedding" min-width="200">
          <template #default="{ row }: { row: any }"><div>{{ row.chat_model || '—' }}</div><div class="muted">{{ row.embedding_model || '无 Embedding' }}</div></template>
        </el-table-column>
        <el-table-column prop="temperature" label="温度" width="70" />
        <el-table-column label="启用" width="70"><template #default="{ row }: { row: any }">
          <el-switch :model-value="row.enabled" :disabled="!auth.canWrite" @change="(v: any) => toggle(row, !!v)" /></template></el-table-column>
        <el-table-column label="连接测试" width="110"><template #default="{ row }: { row: any }">
          <el-tooltip v-if="row.last_test_status" :content="row.last_test_message || ''">
            <el-tag :type="row.last_test_status === 'success' ? 'success' : 'danger'" size="small">{{ row.last_test_status === 'success' ? '成功' : '失败' }}</el-tag>
          </el-tooltip><span v-else class="muted">未测试</span></template></el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }: { row: any }">
            <template v-if="auth.canWrite">
              <el-button link type="primary" :loading="testing === row.id" @click="test(row)">测试连接</el-button>
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button v-if="!row.is_default && row.chat_model" link @click="setDefault(row)">设为默认</el-button>
              <el-popconfirm title="确认删除？" @confirm="remove(row)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog" :title="editing ? '编辑模型' : '新增模型'" width="620px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="Provider">
          <el-select v-model="form.provider" @change="applyPreset" style="width: 100%">
            <el-option v-for="p in presets" :key="p.provider" :label="p.label" :value="p.provider" />
          </el-select>
        </el-form-item>
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="API Base URL" required><el-input v-model="form.base_url" placeholder="https://api.deepseek.com/v1" /></el-form-item>
        <el-form-item label="API Key" :required="!editing">
          <el-input v-model="form.api_key" type="password" show-password autocomplete="new-password"
                    :placeholder="editing ? '留空则不修改（当前 ' + editing.api_key_masked + '）' : 'sk-...'" />
        </el-form-item>
        <el-form-item label="Chat Model"><el-input v-model="form.chat_model" placeholder="deepseek-chat" /></el-form-item>
        <el-form-item label="Embedding Model">
          <el-input v-model="form.embedding_model" placeholder="text-embedding-v3（DeepSeek/Kimi 无 Embedding 接口可留空）" />
        </el-form-item>
        <el-row>
          <el-col :span="12"><el-form-item label="Temperature"><el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Max Tokens"><el-input-number v-model="form.max_tokens" :min="1" :max="200000" controls-position="right" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="超时(秒)"><el-input-number v-model="form.timeout_seconds" :min="1" :max="600" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="重试次数"><el-input-number v-model="form.max_retries" :min="0" :max="10" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
        <el-form-item label="设为默认"><el-switch v-model="form.is_default" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="resultDialog" title="连接测试结果" width="520px">
      <el-result :icon="testResult?.success ? 'success' : 'error'" :title="testResult?.success ? '连接成功' : '连接失败'"
                 :sub-title="testResult?.error || `耗时 ${testResult?.latency_ms} ms`" />
      <pre class="pre mono" style="background: #f6f8fa; padding: 12px; border-radius: 8px; max-height: 260px; overflow: auto">{{ JSON.stringify(testResult, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi } from '@/api'
import type { LLMConfig, ProviderPreset } from '@/api/types'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const list = ref<LLMConfig[]>([])
const presets = ref<ProviderPreset[]>([])
const loading = ref(false)
const dialog = ref(false)
const saving = ref(false)
const editing = ref<LLMConfig | null>(null)
const testing = ref<number | null>(null)
const resultDialog = ref(false)
const testResult = ref<Record<string, any>>()
const blank = () => ({ provider: 'deepseek', name: '', base_url: '', api_key: '', chat_model: '', embedding_model: '',
  temperature: 0.7, max_tokens: undefined as number | undefined, timeout_seconds: 60, max_retries: 2, enabled: true, is_default: false })
const form = reactive(blank())

async function load() { loading.value = true; try { list.value = await modelApi.list() } finally { loading.value = false } }
function applyPreset(p: string) {
  const preset = presets.value.find((x) => x.provider === p)
  if (!preset) return
  form.base_url = preset.base_url
  form.chat_model = preset.chat_model || ''
  form.embedding_model = preset.embedding_model || ''
  if (!form.name || presets.value.some((x) => x.label === form.name)) form.name = preset.label
}
function openCreate() { editing.value = null; Object.assign(form, blank()); applyPreset('deepseek'); dialog.value = true }
function openEdit(row: LLMConfig) {
  editing.value = row
  Object.assign(form, { ...row, api_key: '', chat_model: row.chat_model || '', embedding_model: row.embedding_model || '',
    max_tokens: row.max_tokens ?? undefined, timeout_seconds: row.timeout_seconds ?? 60, max_retries: row.max_retries ?? 2 })
  dialog.value = true
}
async function submit() {
  if (!form.name || !form.base_url) return ElMessage.warning('请填写名称和 Base URL')
  if (!editing.value && !form.api_key) return ElMessage.warning('请填写 API Key')
  saving.value = true
  try {
    const payload: Record<string, unknown> = { ...form, max_tokens: form.max_tokens ?? null }
    if (editing.value) {
      if (!form.api_key) delete payload.api_key
      await modelApi.update(editing.value.id, payload)
    } else await modelApi.create(payload)
    form.api_key = ''
    dialog.value = false
    ElMessage.success('已保存')
    load()
  } finally { saving.value = false }
}
async function test(row: LLMConfig) {
  testing.value = row.id
  try { testResult.value = await modelApi.test(row.id); resultDialog.value = true; load() } finally { testing.value = null }
}
async function toggle(row: LLMConfig, enabled: boolean) { await modelApi.update(row.id, { enabled }); load() }
async function setDefault(row: LLMConfig) { await modelApi.setDefault(row.id); ElMessage.success('已设为默认'); load() }
async function remove(row: LLMConfig) { await modelApi.remove(row.id); ElMessage.success('已删除'); load() }
onMounted(async () => { presets.value = await modelApi.providers(); load() })
</script>
