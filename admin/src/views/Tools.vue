<template>
  <div class="page">
    <div class="page-header"><div><h2>插件与工具</h2><div class="sub">已注册到 ToolManager 的工具，可在智能体「工具配置」中按需授权</div></div></div>
    <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px"
              title="MVP 阶段内置工具在后端代码中注册（app/agent/tool_manager.py），调用前进行授权与 Pydantic 参数校验。动态插件上传 / 第三方 HTTP 工具配置为后续规划（TODO）。" />
    <el-row :gutter="16">
      <el-col v-for="t in tools" :key="t.name" :md="12" style="margin-bottom: 16px">
        <div class="card">
          <div class="section-title">{{ t.name }}</div>
          <div style="margin-bottom: 8px">{{ t.description }}</div>
          <div class="muted">参数 Schema</div>
          <pre class="mono schema">{{ JSON.stringify(t.parameters, null, 2) }}</pre>
        </div>
      </el-col>
    </el-row>
  </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { systemApi } from '@/api'
import type { ToolInfo } from '@/api/types'
const tools = ref<ToolInfo[]>([])
onMounted(async () => { tools.value = await systemApi.tools() })
</script>
<style scoped>.schema { background: #f6f8fa; padding: 10px; border-radius: 8px; font-size: 12px; overflow: auto; }</style>
