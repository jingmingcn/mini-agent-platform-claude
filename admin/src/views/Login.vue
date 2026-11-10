<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="title">🤖 Mini-Agent Platform</div>
      <div class="sub">通用智能体开发平台 · 管理后台</div>
      <el-form :model="form" @submit.prevent="submit" size="large">
        <el-form-item><el-input v-model="form.username" placeholder="用户名" prefix-icon="User" /></el-form-item>
        <el-form-item><el-input v-model="form.password" type="password" show-password placeholder="密码" prefix-icon="Lock" /></el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading" style="width: 100%">登录</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const form = reactive({ username: '', password: '' })
const loading = ref(false)
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function submit() {
  if (!form.username || !form.password) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.replace((route.query.redirect as string) || '/dashboard')
  } finally { loading.value = false }
}
</script>

<style scoped>
.login-wrap { height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0f172a, #1e3a8a); }
.login-card { width: 380px; background: #fff; border-radius: 14px; padding: 36px 32px; box-shadow: 0 20px 60px rgba(0,0,0,.25); }
.title { font-size: 22px; font-weight: 700; text-align: center; }
.sub { text-align: center; color: #8a919f; margin: 6px 0 26px; font-size: 13px; }
</style>
