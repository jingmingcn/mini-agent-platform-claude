<template>
  <div class="stat card">
    <div class="icon" :style="{ background: color }"><el-icon><component :is="icon" /></el-icon></div>
    <div>
      <div class="label">{{ label }}</div>
      <div class="value">{{ value }}</div>
      <div v-if="hint" class="muted">{{ hint }}</div>
    </div>
  </div>
</template>
<script setup lang="ts">
defineProps<{ label: string; value: string | number; icon: string; color: string; hint?: string }>()
</script>
<style scoped>
.stat { display: flex; align-items: center; gap: 14px; }
.icon { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 20px; }
.label { color: #8a919f; font-size: 13px; }
.value { font-size: 24px; font-weight: 700; margin-top: 2px; }
</style>
