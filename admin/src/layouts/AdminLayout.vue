<template>
  <el-container class="layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="aside">
      <div class="brand"><span class="logo">🤖</span><span v-if="!collapsed">Mini-Agent</span></div>
      <el-menu :default-active="activeMenu" :collapse="collapsed" router background-color="#0f172a"
               text-color="#cbd5e1" active-text-color="#ffffff">
        <el-menu-item v-for="r in menuRoutes" :key="r.path" :index="r.path">
          <el-icon><component :is="r.meta.icon" /></el-icon>
          <template #title>{{ r.meta.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="left">
          <el-icon class="toggle" @click="collapsed = !collapsed"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="parentTitle" :to="{ path: String(route.meta.parent) }">{{ parentTitle }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <el-dropdown @command="onCommand">
          <span class="user">
            <el-avatar :size="28">{{ auth.profile?.username?.[0]?.toUpperCase() }}</el-avatar>
            <span>{{ auth.profile?.display_name || auth.profile?.username }}</span>
            <el-tag size="small" effect="plain">{{ roleLabel }}</el-tag>
          </span>
          <template #dropdown>
            <el-dropdown-menu><el-dropdown-item command="logout">退出登录</el-dropdown-item></el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { menuRoutes } from '@/router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const collapsed = ref(false)
const activeMenu = computed(() => (route.meta.parent as string) || route.path)
const parentTitle = computed(() => menuRoutes.find((r) => r.path === route.meta.parent)?.meta.title)
const roleLabel = computed(() => ({ super_admin: '超级管理员', admin: '管理员', viewer: '只读' })[auth.profile?.role || 'viewer'])

function onCommand(cmd: string) {
  if (cmd === 'logout') { auth.logout(); router.push('/login') }
}
</script>

<style scoped>
.layout { height: 100vh; }
.aside { background: #0f172a; transition: width .2s; overflow-x: hidden; }
.aside :deep(.el-menu) { border-right: none; }
.aside :deep(.el-menu-item.is-active) { background: #1e293b !important; }
.brand { height: 56px; display: flex; align-items: center; gap: 8px; padding: 0 20px; color: #fff; font-weight: 700; font-size: 17px; white-space: nowrap; }
.logo { font-size: 22px; }
.header { background: #fff; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #eef0f4; }
.left { display: flex; align-items: center; gap: 14px; }
.toggle { cursor: pointer; font-size: 18px; }
.user { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.main { padding: 0; overflow-y: auto; }
</style>
