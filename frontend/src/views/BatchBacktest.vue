<template>
  <div class="space-y-6">
    <header class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-100">批量回测</h1>
        <p class="mt-1 text-sm text-gray-400">
          在指定研究分析区间内选择多篇研报，基于统一的买卖规则计算 1~N 天收益序列，并输出策略平均收益曲线。
        </p>
      </div>
    </header>

    <!-- 时间区间和基础参数 -->
    <section class="bg-[#020617] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40 space-y-6">
      <h2 class="text-lg font-semibold text-gray-100 mb-2">时间区间与回测参数</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- 研究分析时间段 -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-200">研究分析时间段</span>
            <span class="text-xs text-gray-500">用于筛选候选研报</span>
          </div>
          <DateRangePicker
            class="w-full"
            :quick-days="[]"
            label=""
            v-model:modelStartDate="researchStart"
            v-model:modelEndDate="researchEnd"
            v-model:modelDays="researchDays"
          />
        </div>

        <!-- 回测参数 -->
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-medium text-gray-200">回测参数</span>
            <span class="text-xs text-gray-500">目前使用统一规则，后续可扩展</span>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs text-gray-400 mb-1">回测期限（天，1~100）</label>
              <input
                v-model.number="horizonDays"
                type="number"
                min="1"
                max="100"
                class="w-full px-3 py-2 rounded-lg bg-slate-900 border border-gray-700 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label class="block text-xs text-gray-400 mb-1">权重模式</label>
              <select
                v-model="weightMode"
                class="w-full px-3 py-2 rounded-lg bg-slate-900 border border-gray-700 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="equal">等权</option>
                <option value="confidence">按置信度加权</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <button
          type="button"
          class="inline-flex items-center px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-gray-100 border border-slate-600 transition disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="!researchStart || !researchEnd || loadingReports"
          @click="loadReports"
        >
          <svg
            v-if="loadingReports"
            class="w-4 h-4 mr-2 animate-spin text-blue-300"
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
          <span v-else class="w-4 h-4 mr-2 text-blue-300">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4h18M3 10h18M3 16h18" />
            </svg>
          </span>
          加载候选研报
        </button>

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
          启动批量回测
        </button>

        <p class="text-xs text-gray-500">
          回测期限与权重模式仅影响本次计算，不会修改任何历史数据。
        </p>
      </div>
    </section>

    <!-- 研报列表与多选 -->
    <section class="bg-[#020617] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40 space-y-4">
      <div class="flex items-center justify-between gap-4">
        <h2 class="text-lg font-semibold text-gray-100">候选研报列表</h2>
        <div class="flex items-center gap-3 text-xs text-gray-400">
          <span>共 {{ reports.length }} 条</span>
          <span>已选 {{ selectedAnalysisIds.length }} 条</span>
          <button
            class="px-2 py-1 rounded border border-slate-600 text-gray-200 hover:bg-slate-800"
            type="button"
            :disabled="!reports.length"
            @click="toggleSelectAll"
          >
            {{ isAllSelected ? '清空选择' : '全选' }}
          </button>
        </div>
      </div>

      <div v-if="!reports.length && !loadingReports" class="text-xs text-gray-500">
        请先选择研究分析时间段并点击「加载候选研报」。
      </div>

      <div v-else class="overflow-x-auto max-h-80 border border-slate-800 rounded-lg">
        <table class="min-w-full text-xs text-gray-200">
          <thead class="bg-slate-900/80 sticky top-0">
            <tr>
              <th class="px-3 py-2 text-left w-10">
                <input
                  type="checkbox"
                  :checked="isAllSelected"
                  :indeterminate.prop="isIndeterminate"
                  @change="toggleSelectAll"
                />
              </th>
              <th class="px-3 py-2 text-left">分析日期</th>
              <th class="px-3 py-2 text-left">股票</th>
              <th class="px-3 py-2 text-left">操作</th>
              <th class="px-3 py-2 text-left">置信度</th>
              <th class="px-3 py-2 text-left">风险</th>
              <th class="px-3 py-2 text-left">摘要</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="item in reports"
              :key="item.analysis_id"
              :class="[
                'border-t border-slate-800 hover:bg-slate-800/60 cursor-pointer',
                selectedAnalysisIds.includes(item.analysis_id) ? 'bg-slate-800/80' : ''
              ]"
              @click="toggleSelect(item.analysis_id)"
            >
              <td class="px-3 py-2">
                <input
                  type="checkbox"
                  :checked="selectedAnalysisIds.includes(item.analysis_id)"
                  @change.stop="toggleSelect(item.analysis_id)"
                />
              </td>
              <td class="px-3 py-2 text-gray-300">{{ item.analysis_date }}</td>
              <td class="px-3 py-2">
                <div class="flex flex-col">
                  <span class="font-medium text-gray-100">{{ item.stock_symbol }}</span>
                </div>
              </td>
              <td class="px-3 py-2 text-xs">
                <span
                  v-if="item.formatted_decision?.action"
                  class="inline-flex items-center px-2 py-1 rounded-full border border-slate-600"
                >
                  <span class="w-1.5 h-1.5 rounded-full mr-1.5"
                    :class="item.formatted_decision.action === 'buy' || item.formatted_decision.action === '持有'
                      ? 'bg-green-400'
                      : item.formatted_decision.action === 'sell' || item.formatted_decision.action === '卖出'
                        ? 'bg-red-400'
                        : 'bg-slate-400'"
                  />
                  <span class="text-gray-100">{{ item.formatted_decision.action }}</span>
                </span>
                <span v-else class="text-slate-500">-</span>
              </td>
              <td class="px-3 py-2 text-xs">
                <span v-if="item.formatted_decision?.confidence !== undefined" class="text-green-300">
                  {{
                    (item.formatted_decision.confidence > 1
                      ? item.formatted_decision.confidence
                      : item.formatted_decision.confidence * 100
                    ).toFixed(0)
                  }}%
                </span>
                <span v-else class="text-slate-500">未知</span>
              </td>
              <td class="px-3 py-2 text-xs">
                <span v-if="item.formatted_decision?.risk_score !== undefined" class="text-amber-300">
                  {{
                    (item.formatted_decision.risk_score > 1
                      ? item.formatted_decision.risk_score
                      : item.formatted_decision.risk_score * 100
                    ).toFixed(0)
                  }}%
                </span>
                <span v-else class="text-slate-500">未知</span>
              </td>
              <td class="px-3 py-2 max-w-xs truncate text-slate-300">
                {{ item.summary || '——' }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 回测结果 -->
    <section
      v-if="backtestResult"
      class="bg-[#020617] border border-gray-800 rounded-xl p-6 shadow-xl shadow-black/40 space-y-6"
    >
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-semibold text-gray-100">策略平均收益曲线</h2>
          <p class="text-xs text-gray-500">
            基于 {{ selectedAnalysisIds.length }} 篇研报的加权平均收益（{{ weightModeLabel }}）。
          </p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- 曲线图 -->
        <div class="lg:col-span-2 h-80 bg-slate-950/80 border border-slate-800 rounded-lg p-4">
          <Line v-if="averageChartData" :data="averageChartData" :options="averageChartOptions" />
        </div>

        <!-- 简要统计 -->
        <div class="space-y-3 text-sm text-gray-200">
          <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-2">
            <div class="flex justify-between">
              <span class="text-gray-400">第 1 天平均收益</span>
              <span class="font-semibold" :class="firstDayReturn >= 0 ? 'text-green-400' : 'text-red-400'">
                {{ (firstDayReturn * 100).toFixed(2) }}%
              </span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-400">第 {{ horizonDaysFromResult }} 天平均收益</span>
              <span class="font-semibold" :class="lastDayReturn >= 0 ? 'text-green-400' : 'text-red-400'">
                {{ (lastDayReturn * 100).toFixed(2) }}%
              </span>
            </div>
          </div>

          <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-4 max-h-56 overflow-y-auto">
            <div class="text-xs text-gray-400 mb-2">部分研报示例（第 1/5/10/30 天收益）</div>
            <table class="w-full text-xs text-gray-200">
              <thead>
                <tr class="border-b border-slate-800">
                  <th class="py-1 pr-2 text-left">研报</th>
                  <th class="py-1 px-1 text-right">D1</th>
                  <th class="py-1 px-1 text-right">D5</th>
                  <th class="py-1 px-1 text-right">D10</th>
                  <th class="py-1 pl-1 text-right">D30</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="report in sampleReportResults"
                  :key="report.analysis_id"
                  class="border-b border-slate-900/80"
                >
                  <td class="py-1 pr-2 truncate max-w-[120px]" :title="`${report.stock_symbol} - ${report.company_name}`">
                    {{ report.stock_symbol }}
                  </td>
                  <td class="py-1 px-1 text-right" :class="getCellClass(getReturnOnDay(report, 1))">
                    {{ formatReturnPct(getReturnOnDay(report, 1)) }}
                  </td>
                  <td class="py-1 px-1 text-right" :class="getCellClass(getReturnOnDay(report, 5))">
                    {{ formatReturnPct(getReturnOnDay(report, 5)) }}
                  </td>
                  <td class="py-1 px-1 text-right" :class="getCellClass(getReturnOnDay(report, 10))">
                    {{ formatReturnPct(getReturnOnDay(report, 10)) }}
                  </td>
                  <td class="py-1 pl-1 text-right" :class="getCellClass(getReturnOnDay(report, 30))">
                    {{ formatReturnPct(getReturnOnDay(report, 30)) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 单个研报收益序列 -->
      <div class="bg-slate-950/80 border border-slate-800 rounded-lg p-4 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold text-gray-100">单个研报收益序列</h3>
          <div class="flex items-center gap-2">
            <label class="text-xs text-gray-400">选择研报：</label>
            <select
              v-model="selectedReportId"
              class="px-3 py-1.5 rounded-lg bg-slate-900 border border-gray-700 text-xs text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-[200px]"
            >
              <option value="">请选择研报</option>
              <option
                v-for="report in allReportProfits"
                :key="report.analysis_id"
                :value="report.analysis_id"
              >
                {{ report.stock_symbol }} - {{ report.analysis_date }}
              </option>
            </select>
          </div>
        </div>
        <!-- formatted_decision 信息 -->
        <div v-if="selectedReportDetail && selectedReportDetail.formatted_decision" class="bg-slate-900/50 border border-slate-700 rounded-lg p-3">
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div>
              <span class="text-gray-400">操作：</span>
              <span class="text-gray-100 font-medium">{{ selectedReportDetail.formatted_decision.action || '未知' }}</span>
            </div>
            <div>
              <span class="text-gray-400">置信度：</span>
              <span class="text-green-300 font-medium">
                {{
                  selectedReportDetail.formatted_decision.confidence !== undefined
                    ? (selectedReportDetail.formatted_decision.confidence > 1
                        ? selectedReportDetail.formatted_decision.confidence.toFixed(0)
                        : (selectedReportDetail.formatted_decision.confidence * 100).toFixed(0)
                      ) + '%'
                    : '未知'
                }}
              </span>
            </div>
            <div>
              <span class="text-gray-400">风险评分：</span>
              <span class="text-amber-300 font-medium">
                {{
                  selectedReportDetail.formatted_decision.risk_score !== undefined
                    ? (selectedReportDetail.formatted_decision.risk_score > 1
                        ? selectedReportDetail.formatted_decision.risk_score.toFixed(0)
                        : (selectedReportDetail.formatted_decision.risk_score * 100).toFixed(0)
                      ) + '%'
                    : '未知'
                }}
              </span>
            </div>
            <div>
              <span class="text-gray-400">目标价格：</span>
              <span class="text-gray-100 font-medium">
                {{ selectedReportDetail.formatted_decision.target_price !== undefined && selectedReportDetail.formatted_decision.target_price !== null
                    ? selectedReportDetail.formatted_decision.target_price.toFixed(2)
                    : '未知'
                }}
              </span>
            </div>
          </div>
        </div>
        <div v-if="selectedReportDetail" class="overflow-x-auto max-h-80 border border-slate-800 rounded-lg">
          <table class="min-w-full text-xs text-gray-200">
            <thead class="bg-slate-900/80 sticky top-0 z-10">
              <tr class="border-b border-slate-800">
                <th class="px-3 py-2 text-left">天数</th>
                <th class="px-3 py-2 text-left">交易日期</th>
                <th class="px-3 py-2 text-right">成交价</th>
                <th class="px-3 py-2 text-right">收益(%)</th>
                <th class="px-3 py-2 text-right">平均收益(%)</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(profit, index) in selectedReportDetail.profits"
                :key="index + 1"
                class="border-b border-slate-900/80"
              >
                <td class="px-3 py-1.5">第 {{ index + 1 }} 天</td>
                <td class="px-3 py-1.5 text-gray-300">
                  {{ selectedReportDetail.trade_dates && selectedReportDetail.trade_dates[index] ? selectedReportDetail.trade_dates[index] : '--' }}
                </td>
                <td class="px-3 py-1.5 text-right text-gray-300">
                  {{ selectedReportDetail.trade_prices && selectedReportDetail.trade_prices[index] ? selectedReportDetail.trade_prices[index].toFixed(2) : '--' }}
                </td>
                <td class="px-3 py-1.5 text-right" :class="profit >= 0 ? 'text-green-400' : 'text-red-400'">
                  {{ profit.toFixed(2) }}%
                </td>
                <td class="px-3 py-1.5 text-right" :class="getAverageProfit(selectedReportDetail.profits, index) >= 0 ? 'text-green-400' : 'text-red-400'">
                  {{ getAverageProfit(selectedReportDetail.profits, index).toFixed(2) }}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="text-xs text-gray-500 text-center py-4">
          请选择一个研报查看其收益序列
        </div>
        
        <!-- 收益曲线图 -->
        <div v-if="selectedReportDetail && reportChartData" class="mt-4 h-80 bg-slate-950/80 border border-slate-800 rounded-lg p-4">
          <h4 class="text-sm font-semibold text-gray-100 mb-3">收益对比曲线</h4>
          <Line :data="reportChartData" :options="reportChartOptions" />
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import DateRangePicker from '../components/DateRangePicker.vue'
import {
  getFormattedDecisions,
  startBatchBacktest,
  type BatchBacktestResult,
  type FormattedDecisionItem,
  type SingleReportProfit
} from '../api/index.ts'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

// 初始化默认时间范围：近12个月
const getDefaultDateRange = () => {
  const endDate = new Date()
  const startDate = new Date()
  startDate.setMonth(startDate.getMonth() - 12)
  
  const formatDate = (date: Date) => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  return {
    start: formatDate(startDate),
    end: formatDate(endDate)
  }
}

const defaultRange = getDefaultDateRange()
const researchStart = ref(defaultRange.start)
const researchEnd = ref(defaultRange.end)
const researchDays = ref<number | null>(null)

// 回测参数
const horizonDays = ref<number>(90)
const weightMode = ref<'equal' | 'confidence'>('equal')

// 研报列表
const reports = ref<FormattedDecisionItem[]>([])
const loadingReports = ref(false)
const selectedAnalysisIds = ref<string[]>([])

// 回测结果
const backtestResult = ref<BatchBacktestResult | null>(null)

const starting = ref(false)

// 单个研报选择
const selectedReportId = ref<string>('')

const canStart = computed(() => {
  return (
    researchStart.value &&
    researchEnd.value &&
    selectedAnalysisIds.value.length > 0 &&
    !starting.value &&
    !loadingReports.value
  )
})

const isAllSelected = computed(() => {
  return reports.value.length > 0 && selectedAnalysisIds.value.length === reports.value.length
})

const isIndeterminate = computed(() => {
  return selectedAnalysisIds.value.length > 0 && !isAllSelected.value
})

const weightModeLabel = computed(() => {
  return weightMode.value === 'equal' ? '等权' : '按置信度加权'
})

const loadReports = async () => {
  if (!researchStart.value || !researchEnd.value) return
  loadingReports.value = true
  backtestResult.value = null
  try {
    const res = await getFormattedDecisions(researchStart.value, researchEnd.value)
    if (res.success) {
      reports.value = res.data || []
      selectedAnalysisIds.value = []
    }
  } catch (error) {
    console.error('加载候选研报失败', error)
  } finally {
    loadingReports.value = false
  }
}

const toggleSelect = (id: string) => {
  const idx = selectedAnalysisIds.value.indexOf(id)
  if (idx >= 0) {
    selectedAnalysisIds.value.splice(idx, 1)
  } else {
    selectedAnalysisIds.value.push(id)
  }
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedAnalysisIds.value = []
  } else {
    selectedAnalysisIds.value = reports.value.map(r => r.analysis_id)
  }
}

const onStart = async () => {
  if (!canStart.value) return
  starting.value = true
  backtestResult.value = null
  selectedReportId.value = ''
  try {
    // 只传递analysis_ids，其他参数从数据库的backtest_config中获取
    const payload = {
      analysis_ids: selectedAnalysisIds.value
    }
    const res = await startBatchBacktest(payload)
    if (res.success) {
      backtestResult.value = res
    }
  } catch (error) {
    console.error('批量回测失败', error)
  } finally {
    starting.value = false
  }
}

// 平均收益曲线图
const averageChartData = computed(() => {
  if (!backtestResult.value) return null
  const weightedAvg = backtestResult.value.data.stats.weighted_avg
  const labels = weightedAvg.map((_, index) => `第 ${index + 1} 天`)
  const values = weightedAvg
  return {
    labels,
    datasets: [
      {
        label: '平均收益(%)',
        data: values,
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.2,
        pointRadius: 0,
        pointHoverRadius: 0
      }
    ]
  }
})

const averageChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false
  },
  plugins: {
    legend: {
      display: true,
      labels: {
        color: 'rgb(203, 213, 225)'
      }
    },
    // 禁用数据标签，去掉每个点上的数值标识
    datalabels: {
      display: false
    },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      titleColor: 'rgb(226, 232, 240)',
      bodyColor: 'rgb(226, 232, 240)',
      borderColor: 'rgba(34, 197, 94, 0.6)',
      borderWidth: 1,
      callbacks: {
        label: (ctx: any) => {
          const value = ctx.parsed.y ?? 0
          return ` 平均收益：${value.toFixed(2)}%`
        }
      }
    }
  },
  scales: {
    x: {
      ticks: {
        color: 'rgb(148, 163, 184)',
        maxRotation: 0,
        minRotation: 0
      },
      grid: {
        color: 'rgba(148, 163, 184, 0.1)'
      }
    },
    y: {
      ticks: {
        color: 'rgb(148, 163, 184)',
        callback: (value: number | string) => `${value}%`
      },
      grid: {
        color: 'rgba(55, 65, 81, 0.6)'
      }
    }
  }
}))

// 简单统计
const firstDayReturn = computed(() => {
  if (!backtestResult.value || !backtestResult.value.data.stats.weighted_avg.length) return 0
  return backtestResult.value.data.stats.weighted_avg[0] / 100  // 转换为小数
})

const lastDayReturn = computed(() => {
  if (!backtestResult.value || !backtestResult.value.data.stats.weighted_avg.length) return 0
  const arr = backtestResult.value.data.stats.weighted_avg
  return arr[arr.length - 1] / 100  // 转换为小数
})

const horizonDaysFromResult = computed(() => {
  if (!backtestResult.value || !backtestResult.value.data.stats.weighted_avg.length) return 0
  return backtestResult.value.data.stats.weighted_avg.length
})

// 部分研报示例
const sampleReportResults = computed<SingleReportProfit[]>(() => {
  if (!backtestResult.value) return []
  const list = backtestResult.value.data.profits || []
  return list.slice(0, 5)
})

const getReturnOnDay = (report: SingleReportProfit, day: number): number | null => {
  // profits数组索引从0开始，对应第1天到第N天
  const index = day - 1
  if (index >= 0 && index < report.profits.length) {
    return report.profits[index] / 100  // 转换为小数
  }
  return null
}

const formatReturnPct = (value: number | null): string => {
  if (value === null || Number.isNaN(value)) return '--'
  return `${(value * 100).toFixed(2)}%`
}

const getCellClass = (value: number | null) => {
  if (value === null || Number.isNaN(value)) return 'text-slate-400'
  return value >= 0 ? 'text-green-400' : 'text-red-400'
}

// 所有研报收益数据
const allReportProfits = computed<SingleReportProfit[]>(() => {
  if (!backtestResult.value) return []
  return backtestResult.value.data.profits || []
})

// 选中的研报详情
const selectedReportDetail = computed<SingleReportProfit | null>(() => {
  if (!selectedReportId.value || !backtestResult.value) return null
  return allReportProfits.value.find(r => r.analysis_id === selectedReportId.value) || null
})

// 计算平均收益（从第1天到第index天的平均收益）
const getAverageProfit = (profits: number[], index: number): number => {
  if (!profits || profits.length === 0 || index < 0) return 0
  const slice = profits.slice(0, index + 1)
  const sum = slice.reduce((acc, val) => acc + val, 0)
  return sum / slice.length
}

// 单个研报的图表数据
const reportChartData = computed(() => {
  if (!selectedReportDetail.value) return null
  
  const report = selectedReportDetail.value
  const labels = report.trade_dates || report.profits.map((_, index) => `第 ${index + 1} 天`)
  
  const datasets = [
    {
      label: '收益(%)',
      data: report.profits,
      borderColor: 'rgb(34, 197, 94)',
      backgroundColor: 'rgba(34, 197, 94, 0.1)',
      fill: false,
      tension: 0.2,
      pointRadius: 0,
      pointHoverRadius: 3,
      yAxisID: 'y',
    }
  ]
  
  // 添加大盘指数曲线
  if (report.index_prices && report.index_prices.length > 0) {
    datasets.push({
      label: '大盘指数收益(%)',
      data: report.index_prices,
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      fill: false,
      tension: 0.2,
      pointRadius: 0,
      pointHoverRadius: 3,
      yAxisID: 'y',
    })
  }
  
  // 添加股票收盘价曲线（归一化到百分比）
  if (report.close_prices && report.close_prices.length > 0 && report.close_prices[0] > 0) {
    const basePrice = report.close_prices[0]
    const normalizedPrices = report.close_prices.map(price => ((price - basePrice) / basePrice) * 100)
    datasets.push({
      label: '股票收盘价收益(%)',
      data: normalizedPrices,
      borderColor: 'rgb(251, 146, 60)',
      backgroundColor: 'rgba(251, 146, 60, 0.1)',
      fill: false,
      tension: 0.2,
      pointRadius: 0,
      pointHoverRadius: 3,
      yAxisID: 'y',
    })
  }
  
  return {
    labels,
    datasets,
  }
})

const reportChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false
  },
  plugins: {
    legend: {
      display: true,
      labels: {
        color: 'rgb(203, 213, 225)'
      }
    },
    datalabels: {
      display: false
    },
    tooltip: {
      backgroundColor: 'rgba(15, 23, 42, 0.95)',
      titleColor: 'rgb(226, 232, 240)',
      bodyColor: 'rgb(226, 232, 240)',
      borderColor: 'rgba(34, 197, 94, 0.6)',
      borderWidth: 1,
      callbacks: {
        label: (ctx: any) => {
          const value = ctx.parsed.y ?? 0
          return ` ${ctx.dataset.label}：${value.toFixed(2)}%`
        }
      }
    }
  },
  scales: {
    x: {
      ticks: {
        color: 'rgb(148, 163, 184)',
        maxRotation: 45,
        minRotation: 0
      },
      grid: {
        color: 'rgba(148, 163, 184, 0.1)'
      }
    },
    y: {
      ticks: {
        color: 'rgb(148, 163, 184)',
        callback: (value: number | string) => `${value}%`
      },
      grid: {
        color: 'rgba(55, 65, 81, 0.6)'
      }
    }
  }
}))

// 页面初始化时自动加载候选研报
onMounted(() => {
  if (researchStart.value && researchEnd.value) {
    loadReports()
  }
})
</script>
