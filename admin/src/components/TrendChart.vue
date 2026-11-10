<template><div ref="el" style="height: 280px" /></template>
<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])
const props = defineProps<{ data: { date: string; requests: number; tokens: number }[] }>()
const el = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function render() {
  if (!chart) return
  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['调用次数', 'Token 消耗'] },
    grid: { left: 50, right: 60, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: props.data.map((d) => d.date.slice(5)) },
    yAxis: [{ type: 'value', name: '次数', minInterval: 1 }, { type: 'value', name: 'Tokens' }],
    series: [
      { name: '调用次数', type: 'bar', data: props.data.map((d) => d.requests), itemStyle: { color: '#3b82f6', borderRadius: [4, 4, 0, 0] } },
      { name: 'Token 消耗', type: 'line', yAxisIndex: 1, smooth: true, data: props.data.map((d) => d.tokens), itemStyle: { color: '#10b981' } },
    ],
  })
}
const onResize = () => chart?.resize()
onMounted(() => { chart = echarts.init(el.value!); render(); window.addEventListener('resize', onResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', onResize); chart?.dispose() })
watch(() => props.data, render, { deep: true })
</script>
