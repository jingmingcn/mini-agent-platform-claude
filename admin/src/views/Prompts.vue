<template>
  <div class="page">
    <div class="page-header">
      <div><h2>Prompt 管理</h2><div class="sub">维护可复用的系统提示词模板；智能体的提示词变更会自动记录历史版本</div></div>
      <el-button v-if="auth.canWrite" type="primary" icon="Plus" @click="open(null)">新建模板</el-button>
    </div>
    <div class="card">
      <el-tabs v-model="tab" @tab-change="load">
        <el-tab-pane label="模板库" name="templates" />
        <el-tab-pane label="智能体版本历史" name="versions" />
      </el-tabs>
      <div class="toolbar" v-if="tab === 'versions'">
        <el-select v-model="agentId" placeholder="选择智能体" style="width: 260px" @change="load">
          <el-option v-for="a in agents" :key="a.id" :label="a.name" :value="a.id" />
        </el-select>
      </div>
      <el-table :data="list" v-loading="loading">
        <el-table-column prop="name" label="名称" width="200" />
        <el-table-column label="版本" width="70"><template #default="{ row }: { row: any }">v{{ row.version }}</template></el-table-column>
        <el-table-column label="内容" min-width="360"><template #default="{ row }: { row: any }"><div class="pre clip">{{ row.content }}</div></template></el-table-column>
        <el-table-column prop="description" label="说明" width="180" show-overflow-tooltip />
        <el-table-column label="更新时间" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.updated_at) }}</template></el-table-column>
        <el-table-column v-if="tab === 'templates' && auth.canWrite" label="操作" width="130">
          <template #default="{ row }: { row: any }">
            <el-button link type="primary" @click="open(row)">编辑</el-button>
            <el-popconfirm title="确认删除？" @confirm="remove(row)"><template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <el-dialog v-model="dialog" :title="editing ? '编辑模板' : '新建模板'" width="640px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="说明"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="内容"><el-input v-model="form.content" type="textarea" :rows="12" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="dialog = false">取消</el-button><el-button type="primary" @click="submit">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { agentApi, promptApi } from '@/api'
import type { Agent, Prompt } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { fmtTime } from '@/utils/format'

const auth = useAuthStore()
const tab = ref('templates')
const list = ref<Prompt[]>([])
const agents = ref<Agent[]>([])
const agentId = ref<number>()
const loading = ref(false)
const dialog = ref(false)
const editing = ref<Prompt | null>(null)
const form = reactive({ name: '', description: '', content: '' })

async function load() {
  loading.value = true
  try {
    if (tab.value === 'templates') list.value = await promptApi.list()
    else list.value = agentId.value ? await promptApi.list(agentId.value) : []
  } finally { loading.value = false }
}
function open(p: Prompt | null) { editing.value = p; Object.assign(form, { name: p?.name || '', description: p?.description || '', content: p?.content || '' }); dialog.value = true }
async function submit() {
  if (!form.name || !form.content) return ElMessage.warning('请填写名称和内容')
  if (editing.value) await promptApi.update(editing.value.id, form)
  else await promptApi.create(form)
  dialog.value = false
  ElMessage.success('已保存')
  load()
}
async function remove(p: Prompt) { await promptApi.remove(p.id); load() }
onMounted(async () => { load(); agents.value = await agentApi.list() })
</script>
<style scoped>.clip { max-height: 66px; overflow: hidden; font-size: 13px; }</style>
