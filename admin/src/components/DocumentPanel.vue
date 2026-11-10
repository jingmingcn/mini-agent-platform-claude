<template>
  <div>
    <el-upload v-if="auth.canWrite" drag multiple :auto-upload="false" :show-file-list="false" :on-change="onPick"
               accept=".pdf,.docx,.txt,.md,.markdown,.html,.htm,.csv" class="uploader">
      <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
      <div class="el-upload__text">拖拽文件到此处，或 <em>点击选择</em></div>
      <template #tip><div class="muted">支持 PDF / DOCX / TXT / Markdown / HTML / CSV，单文件不超过 20MB，一次最多 20 个。上传后自动异步解析与向量化。</div></template>
    </el-upload>
    <div v-if="pending.length" class="pending">
      <el-tag v-for="(f, i) in pending" :key="i" closable @close="pending.splice(i, 1)" style="margin: 0 6px 6px 0">{{ f.name }}</el-tag>
      <div><el-button type="primary" size="small" :loading="uploading" @click="upload">上传 {{ pending.length }} 个文件</el-button>
        <el-progress v-if="uploading" :percentage="uploadPct" style="width: 240px; display: inline-flex; margin-left: 12px" /></div>
    </div>

    <div class="toolbar" style="margin-top: 12px">
      <el-input v-model="keyword" placeholder="搜索文件名" clearable style="width: 200px" @change="refresh" prefix-icon="Search" />
      <el-select v-model="status" placeholder="处理状态" clearable style="width: 130px" @change="refresh">
        <el-option v-for="(v, k) in docStatusMap" :key="k" :label="v.label" :value="k" />
      </el-select>
      <el-button icon="Refresh" @click="refresh">刷新</el-button>
    </div>
    <el-table :data="docs" v-loading="loading">
      <el-table-column label="文件名" min-width="220"><template #default="{ row }: { row: any }">
        <el-icon><Document /></el-icon> {{ row.filename }}<div class="muted">{{ row.file_type.toUpperCase() }} · {{ fmtSize(row.file_size) }}</div></template></el-table-column>
      <el-table-column label="状态 / 进度" width="230"><template #default="{ row }: { row: any }">
        <el-tag :type="docStatusMap[row.status].type" size="small">{{ docStatusMap[row.status].label }}</el-tag>
        <el-progress v-if="row.status === 'processing' || row.status === 'pending'" :percentage="row.progress" :stroke-width="6" style="margin-top: 4px" />
        <el-tooltip v-if="row.status === 'failed'" :content="row.error_message || ''" placement="top">
          <div class="err">{{ row.error_message }}</div></el-tooltip>
        <span v-if="row.status === 'processing'" class="muted"> {{ row.stage }}</span></template></el-table-column>
      <el-table-column label="切片 / 字符" width="120"><template #default="{ row }: { row: any }">{{ row.chunk_count }} / {{ row.char_count }}</template></el-table-column>
      <el-table-column label="上传时间" width="170"><template #default="{ row }: { row: any }">{{ fmtTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="操作" width="260" fixed="right"><template #default="{ row }: { row: any }">
        <el-button link type="primary" :disabled="!row.chunk_count" @click="openChunks(row)">查看切片</el-button>
        <template v-if="auth.canWrite">
          <el-button link :disabled="row.status === 'processing'" @click="reparse(row)">重新解析</el-button>
          <el-popconfirm title="仅删除向量与切片，保留文件？" @confirm="delVectors(row)">
            <template #reference><el-button link type="warning" :disabled="!row.chunk_count">删向量</el-button></template></el-popconfirm>
          <el-popconfirm title="删除文档及其向量？" @confirm="remove(row)">
            <template #reference><el-button link type="danger">删除</el-button></template></el-popconfirm>
        </template></template></el-table-column>
    </el-table>
    <div class="pager"><el-pagination v-model:current-page="page" :page-size="pageSize" :total="total" layout="total, prev, pager, next" @current-change="refresh" /></div>

    <el-drawer v-model="chunkDrawer" :title="`切片结果 · ${chunkDoc?.filename}`" size="50%">
      <div v-loading="chunkLoading">
        <div v-for="c in chunks" :key="c.id" class="chunk">
          <div class="muted">#{{ c.chunk_index }} · {{ c.char_count }} 字<span v-if="c.page_number"> · 第 {{ c.page_number }} 页</span> · <span class="mono">{{ c.chunk_id.slice(0, 8) }}</span></div>
          <div class="pre">{{ c.content }}</div>
        </div>
        <div class="pager"><el-pagination v-model:current-page="chunkPage" :page-size="20" :total="chunkTotal" layout="total, prev, pager, next" @current-change="loadChunks" /></div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, type UploadFile } from 'element-plus'
import { docApi, kbApi } from '@/api'
import type { Chunk, DocumentItem } from '@/api/types'
import { useAuthStore } from '@/stores/auth'
import { docStatusMap, fmtSize, fmtTime } from '@/utils/format'

const props = defineProps<{ kbId: number }>()
const emit = defineEmits<{ changed: [] }>()
const auth = useAuthStore()
const docs = ref<DocumentItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const keyword = ref('')
const status = ref('')
const pending = ref<File[]>([])
const uploading = ref(false)
const uploadPct = ref(0)
let timer: number | undefined

async function load(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await kbApi.documents(props.kbId, { page: page.value, page_size: pageSize, status: status.value || undefined, keyword: keyword.value || undefined })
    docs.value = res.items
    total.value = res.total
  } finally { loading.value = false }
  schedulePoll()
}
const refresh = () => load()
function schedulePoll() {
  clearTimeout(timer)
  if (docs.value.some((d) => d.status === 'pending' || d.status === 'processing')) {
    timer = window.setTimeout(async () => { await load(true); emit('changed') }, 2000)
  }
}
function onPick(f: UploadFile) { if (f.raw) pending.value.push(f.raw) }
async function upload() {
  uploading.value = true
  uploadPct.value = 0
  try {
    await kbApi.upload(props.kbId, pending.value, (p) => (uploadPct.value = p))
    ElMessage.success('上传成功，正在后台处理')
    pending.value = []
    page.value = 1
    load()
    emit('changed')
  } finally { uploading.value = false }
}
async function reparse(d: DocumentItem) { await docApi.reparse(d.id); ElMessage.success('已重新提交解析'); load() }
async function delVectors(d: DocumentItem) { await docApi.deleteVectors(d.id); ElMessage.success('已删除向量'); load(); emit('changed') }
async function remove(d: DocumentItem) { await docApi.remove(d.id); ElMessage.success('已删除'); load(); emit('changed') }

const chunkDrawer = ref(false)
const chunkDoc = ref<DocumentItem>()
const chunks = ref<Chunk[]>([])
const chunkPage = ref(1)
const chunkTotal = ref(0)
const chunkLoading = ref(false)
async function loadChunks() {
  chunkLoading.value = true
  try { const r = await docApi.chunks(chunkDoc.value!.id, chunkPage.value); chunks.value = r.items; chunkTotal.value = r.total } finally { chunkLoading.value = false }
}
function openChunks(d: DocumentItem) { chunkDoc.value = d; chunkPage.value = 1; chunkDrawer.value = true; loadChunks() }

watch(() => props.kbId, () => { page.value = 1; load() })
onMounted(() => load())
onBeforeUnmount(() => clearTimeout(timer))
defineExpose({ load })
</script>

<style scoped>
.uploader :deep(.el-upload-dragger) { padding: 24px; }
.pending { margin-top: 10px; }
.err { color: var(--el-color-danger); font-size: 12px; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chunk { border: 1px solid #eef0f4; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; font-size: 13px; line-height: 1.6; }
</style>
