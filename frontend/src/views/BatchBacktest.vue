<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-100">批量回测</h1>
        <p class="mt-1 text-sm text-gray-400">
          配置研究分析区间与历史回测区间，启动批量回测任务。页面其他功能后续再补充。
        </p>
      </div>
    </header>

    <section class="bg-[#020617] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40">
      <h2 class="text-lg font-semibold text-gray-100 mb-4">时间区间设置</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 研究分析时间段 -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-200">研究分析时间段</span>
            <span class="text-xs text-gray-500">用于生成研判/分析结果</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-3 items-center">
            <input
              v-model="researchStart"
              type="date"
              class="w-full px-3 py-2 rounded-lg bg-slate-900 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="hidden sm:inline text-gray-500 text-xs text-center">至</span>
            <span class="sm:hidden text-gray-500 text-xs text-center">~</span>
            <input
              v-model="researchEnd"
              type="date"
              class="w-full px-3 py-2 rounded-lg bg-slate-900 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>

        <!-- 回测历史数据时间段 -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-200">回测历史数据时间段</span>
            <span class="text-xs text-gray-500">用于生成净值曲线等回测指标</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] gap-3 items-center">
            <input
              v-model="backtestStart"
              type="date"
              class="w-full px-3 py-2 rounded-lg bg-slate-900 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="hidden sm:inline text-gray-500 text-xs text-center">至</span>
            <span class="sm:hidden text-gray-500 text-xs text-center">~</span>
            <input
              v-model="backtestEnd"
              type="date"
              class="w-full px-3 py-2 rounded-lg bg-slate-900 border border-gray-700 text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        </div>
      </div>

      <div class="mt-6 flex flex-wrap items-center gap-4">
        <button
          type="button"
          class="inline-flex items-center px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-sm font-medium text-white shadow-lg shadow-blue-900/50 transition disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="!canStart || starting"
          @click="onStart"
        >
          <svg
            v-if="starting"
            class="w-4 h-4 mr-2 animate-spin text-blue-100"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            />
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 000 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z"
            />
          </svg>
          <svg
            v-else
            class="w-4 h-4 mr-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v18l7-5 7 5V3z" />
          </svg>
          启动回测任务
        </button>

        <p class="text-xs text-gray-500">
          目前仅配置基础时间参数，不触发真实任务提交逻辑，后续可接入后端批量回测 API。
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const researchStart = ref('')
const researchEnd = ref('')
const backtestStart = ref('')
const backtestEnd = ref('')

const starting = ref(false)

const canStart = computed(() => {
  return Boolean(
    researchStart.value &&
      researchEnd.value &&
      backtestStart.value &&
      backtestEnd.value
  )
})

const onStart = async () => {
  if (!canStart.value || starting.value) return
  starting.value = true
  try {
    // 这里暂时只做前端占位，后续可以接入真实的回测任务创建接口
    // eslint-disable-next-line no-console
    console.log('启动批量回测', {
      researchStart: researchStart.value,
      researchEnd: researchEnd.value,
      backtestStart: backtestStart.value,
      backtestEnd: backtestEnd.value
    })
  } finally {
    starting.value = false
  }
}
</script>


