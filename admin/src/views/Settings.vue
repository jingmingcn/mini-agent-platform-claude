<template>
  <div class="page">
    <div class="page-header"><div><h2>系统设置</h2><div class="sub">小程序首页展示内容</div></div></div>
    <div class="card" style="max-width: 760px" v-loading="loading">
      <el-form :model="form" label-width="110px" :disabled="!auth.canWrite">
        <el-form-item label="平台名称"><el-input v-model="form.platform_name" maxlength="64" /></el-form-item>
        <el-form-item label="首页欢迎语"><el-input v-model="form.welcome_text" type="textarea" :rows="3" maxlength="500" /></el-form-item>
        <el-form-item label="快捷提问">
          <div style="width: 100%">
            <div v-for="(_, i) in form.quick_questions" :key="i" style="display: flex; gap: 8px; margin-bottom: 8px">
              <el-input v-model="form.quick_questions[i]" /><el-button icon="Delete" circle @click="form.quick_questions.splice(i, 1)" />
            </div>
            <el-button size="small" icon="Plus" @click="form.quick_questions.push('')">添加</el-button>
          </div>
        </el-form-item>
        <el-form-item><el-button type="primary" @click="save">保存</el-button></el-form-item>
      </el-form>
      <el-divider />
      <div class="section-title">安全说明</div>
      <ul class="muted" style="line-height: 2">
        <li>API Key 使用 Fernet（AES-128-CBC + HMAC）加密存储，密钥来自环境变量 ENCRYPTION_KEY / SECRET_KEY。</li>
        <li>管理员密码使用 bcrypt 哈希；身份认证使用 JWT，管理员与小程序用户 Token 类型隔离。</li>
        <li>接口限流、上传类型/大小/魔数校验、审计日志在后端统一实施。</li>
      </ul>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { systemApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
const loading = ref(false)
const form = reactive({ platform_name: '', welcome_text: '', quick_questions: [] as string[] })
async function save() {
  await systemApi.saveSettings({ ...form, quick_questions: form.quick_questions.filter((q) => q.trim()) })
  ElMessage.success('已保存')
}
onMounted(async () => { loading.value = true; try { Object.assign(form, await systemApi.settings()) } finally { loading.value = false } })
</script>
