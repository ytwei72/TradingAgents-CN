<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-white">Cursor 用量统计</h1>
      <div class="text-sm text-gray-400">
        最后更新: {{ lastUpdated }}
      </div>
    </div>

    <!-- Overall Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">📥 总输入 Tokens</div>
        <div class="text-2xl font-bold text-white">{{ formatNumber(totalStats.total_input_tokens, 0) }}</div>
        <div class="text-xs text-gray-500 mt-2">
          含缓存写入/不写入
        </div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">📤 总输出 Tokens</div>
        <div class="text-2xl font-bold text-white">{{ formatNumber(totalStats.total_output_tokens, 0) }}</div>
        <div class="text-xs text-gray-500 mt-2">
          输出 Token 数
        </div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">🔢 总请求数</div>
        <div class="text-2xl font-bold text-white">{{ formatNumber(totalStats.total_requests, 0) }}</div>
        <div class="text-xs text-gray-500 mt-2">
          所有历史数据
        </div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">💰 总费用</div>
        <div class="text-2xl font-bold text-white">${{ formatNumber(totalStats.total_cost, 2) }}</div>
        <div class="text-xs text-gray-500 mt-2">
          所有历史数据
        </div>
      </div>
    </div>

    <!-- Date Range Picker -->
    <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
      <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
        <h2 class="text-lg font-semibold text-white">日期范围选择</h2>
        <div class="flex items-center space-x-2 bg-[#0f172a] p-1 rounded-lg border border-gray-700">
          <DateRangePicker
            class="flex-1"
            :quick-days="[7, 30, 90]"
            label=""
            v-model:modelStartDate="startDate"
            v-model:modelEndDate="endDate"
            v-model:modelDays="rangeDays"
            :start-placeholder="'开始日期'"
            :end-placeholder="'结束日期'"
          />
          <button
            @click="loadStatistics"
            class="ml-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !startDate || !endDate"
          >
            {{ loading ? '加载中...' : '查询' }}
          </button>
        </div>
      </div>

      <!-- CSV Files List -->
      <div v-if="filteredDates.length > 0" class="mt-4">
        <h3 class="text-sm font-semibold text-white mb-2">符合条件的 CSV 文件 ({{ filteredDates.length }} 个)</h3>
        <div class="max-h-48 overflow-y-auto bg-[#0f172a] rounded border border-gray-700 p-3">
          <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
            <div
              v-for="date in filteredDates"
              :key="date"
              class="text-xs text-gray-400 bg-[#1e293b] px-2 py-1 rounded border border-gray-700"
            >
              usage-events-{{ date }}.csv
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Charts Section -->
    <div v-if="!loading && hasData" class="space-y-6">
      <!-- Daily Statistics Chart (Mixed: Bar + Line) -->
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-4">每日用量趋势</h3>
        <div class="h-80">
          <Bar :data="dailyChartData" :options="mixedChartOptions" />
        </div>
      </div>

      <!-- Kind Statistics Chart -->
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-4">按类型分类统计</h3>
        <div class="h-80">
          <Doughnut :data="kindChartData" :options="doughnutChartOptions" />
        </div>
      </div>

      <!-- Model Statistics Chart -->
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-4">按模型分类统计</h3>
        <div class="h-80">
          <Bar :data="modelChartData" :options="barChartOptions" />
        </div>
      </div>

      <!-- Hourly Statistics Chart -->
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-4">按小时统计</h3>
        <div class="h-80">
          <Bar :data="hourlyChartData" :options="barChartOptions" />
        </div>
      </div>

      <!-- Cost Statistics Table -->
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-4">费用统计（区分 Free 和 Included）</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-700">
                <th class="text-left py-3 px-4 text-gray-400">类型</th>
                <th class="text-left py-3 px-4 text-gray-400">模型</th>
                <th class="text-right py-3 px-4 text-gray-400">请求数</th>
                <th class="text-right py-3 px-4 text-gray-400">总 Tokens</th>
                <th class="text-right py-3 px-4 text-gray-400">总费用 ($)</th>
                <th class="text-right py-3 px-4 text-gray-400">平均费用/请求</th>
                <th class="text-left py-3 px-4 text-gray-400">备注</th>
              </tr>
            </thead>
            <tbody>
              <!-- Free Section -->
              <template v-if="costStats.free">
                <tr class="border-b border-gray-800 bg-gray-800/30">
                  <td class="py-3 px-4 text-white font-semibold" rowspan="2">Free (免费)</td>
                  <td class="py-3 px-4 text-gray-300">auto</td>
                  <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(costStats.free.auto_requests, 0) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">-</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(costStats.free.auto_cost, 2) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(costStats.free.auto_requests > 0 ? costStats.free.auto_cost / costStats.free.auto_requests : 0, 4) }}</td>
                  <td class="py-3 px-4 text-gray-400 text-xs">仅作参考</td>
                </tr>
                <tr
                  v-for="(model, modelName) in costStats.free.models"
                  :key="`free-${modelName}`"
                  class="border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <td class="py-3 px-4 text-gray-300">{{ modelName }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(model.total_requests, 0) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(model.total_tokens, 0) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(model.total_cost, 2) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(model.total_requests > 0 ? model.total_cost / model.total_requests : 0, 4) }}</td>
                  <td class="py-3 px-4 text-gray-400 text-xs">-</td>
                </tr>
                <tr class="border-b-2 border-gray-600 bg-gray-800/50">
                  <td class="py-3 px-4 text-white font-semibold" colspan="2">Free 小计</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">{{ formatNumber(costStats.free.total_requests, 0) }}</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">-</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">${{ formatNumber(costStats.free.total_cost, 2) }}</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">${{ formatNumber(costStats.free.total_requests > 0 ? costStats.free.total_cost / costStats.free.total_requests : 0, 4) }}</td>
                  <td class="py-3 px-4 text-gray-400 text-xs">-</td>
                </tr>
              </template>
              
              <!-- Included Section -->
              <template v-if="costStats.Included">
                <tr class="border-b border-gray-800 bg-gray-800/30">
                  <td class="py-3 px-4 text-white font-semibold" rowspan="2">Included (套餐内)</td>
                  <td class="py-3 px-4 text-gray-300">auto</td>
                  <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(costStats.Included.auto_requests, 0) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">-</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(costStats.Included.auto_cost, 2) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(costStats.Included.auto_requests > 0 ? costStats.Included.auto_cost / costStats.Included.auto_requests : 0, 4) }}</td>
                  <td class="py-3 px-4 text-gray-400 text-xs">仅作参考</td>
                </tr>
                <tr
                  v-for="(model, modelName) in costStats.Included.models"
                  :key="`included-${modelName}`"
                  class="border-b border-gray-800 hover:bg-gray-800/50"
                >
                  <td class="py-3 px-4 text-gray-300">{{ modelName }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(model.total_requests, 0) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(model.total_tokens, 0) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(model.total_cost, 2) }}</td>
                  <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(model.total_requests > 0 ? model.total_cost / model.total_requests : 0, 4) }}</td>
                  <td class="py-3 px-4 text-gray-400 text-xs">-</td>
                </tr>
                <tr class="border-b-2 border-gray-600 bg-gray-800/50">
                  <td class="py-3 px-4 text-white font-semibold" colspan="2">Included 小计</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">{{ formatNumber(costStats.Included.total_requests, 0) }}</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">-</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">${{ formatNumber(costStats.Included.total_cost, 2) }}</td>
                  <td class="py-3 px-4 text-right text-white font-semibold">${{ formatNumber(costStats.Included.total_requests > 0 ? costStats.Included.total_cost / costStats.Included.total_requests : 0, 4) }}</td>
                  <td class="py-3 px-4 text-gray-400 text-xs">-</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Daily Statistics Table -->
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
        <h3 class="text-lg font-semibold text-white mb-4">每日详细统计</h3>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-700">
                <th class="text-left py-3 px-4 text-gray-400">日期</th>
                <th class="text-right py-3 px-4 text-gray-400">请求数</th>
                <th class="text-right py-3 px-4 text-gray-400">总 Tokens</th>
                <th class="text-right py-3 px-4 text-gray-400">总费用</th>
                <th class="text-right py-3 px-4 text-gray-400">平均费用/请求</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(stats, date) in dailyStats"
                :key="date"
                class="border-b border-gray-800 hover:bg-gray-800/50"
              >
                <td class="py-3 px-4 text-white">{{ date }}</td>
                <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(stats.total_requests, 0) }}</td>
                <td class="py-3 px-4 text-right text-gray-300">{{ formatNumber(stats.total_tokens, 0) }}</td>
                <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(stats.total_cost, 2) }}</td>
                <td class="py-3 px-4 text-right text-gray-300">${{ formatNumber(stats.average_cost_per_request, 4) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex justify-center items-center h-64">
      <div class="text-gray-400">加载中...</div>
    </div>

    <!-- Empty State -->
    <div v-if="!loading && !hasData" class="flex justify-center items-center h-64">
      <div class="text-gray-400 text-center">
        <p class="text-lg mb-2">暂无数据</p>
        <p class="text-sm">请选择日期范围并点击查询</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line, Bar, Doughnut } from 'vue-chartjs'
import DateRangePicker from '../components/DateRangePicker.vue'
import {
  getCursorUsageDates,
  getCursorUsageDatesWithRange,
  getCursorUsageTotalStatistics,
  getCursorUsageDailyStatistics,
  getCursorUsageKindStatistics,
  getCursorUsageModelStatistics,
  getCursorUsageHourlyStatistics,
  getCursorUsageCostStatistics,
} from '../api'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
)

// State
const loading = ref(false)
const lastUpdated = ref(new Date().toLocaleString())
const availableDates = ref<string[]>([])
const filteredDates = ref<string[]>([])
const startDate = ref('')
const endDate = ref('')
const rangeDays = ref<number | null>(null)

const totalStats = reactive({
  total_requests: 0,
  total_cost: 0,
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_tokens: 0,
  average_cost_per_request: 0,
})

const dailyStats = ref<Record<string, any>>({})
const kindStats = ref<Record<string, any>>({})
const modelStats = ref<Record<string, any>>({})
const hourlyStats = ref<Record<string, any>>({})
const costStats = ref<Record<string, any>>({})

// Computed
const hasData = computed(() => {
  return Object.keys(dailyStats.value).length > 0
})

const dailyChartData = computed(() => {
  const dates = Object.keys(dailyStats.value).sort()
  return {
    labels: dates,
    datasets: [
      {
        type: 'bar' as const,
        label: '总输入 Tokens (千)',
        data: dates.map(date => dailyStats.value[date].total_input_tokens / 1000),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        yAxisID: 'y',
      },
      {
        type: 'bar' as const,
        label: '总输出 Tokens (千)',
        data: dates.map(date => dailyStats.value[date].total_output_tokens / 1000),
        backgroundColor: 'rgba(34, 197, 94, 0.8)',
        yAxisID: 'y',
      },
      {
        type: 'line' as const,
        label: '请求总量',
        data: dates.map(date => dailyStats.value[date].total_requests),
        borderColor: 'rgb(251, 191, 36)',
        backgroundColor: 'rgba(251, 191, 36, 0.1)',
        tension: 0.4,
        yAxisID: 'y1',
      },
    ],
  }
})

const kindChartData = computed(() => {
  const kinds = Object.keys(kindStats.value)
  const colors = ['rgb(59, 130, 246)', 'rgb(34, 197, 94)', 'rgb(251, 191, 36)', 'rgb(239, 68, 68)']
  return {
    labels: kinds,
    datasets: [
      {
        data: kinds.map(kind => kindStats.value[kind].total_cost),
        backgroundColor: kinds.map((_, i) => colors[i % colors.length]),
        borderColor: 'rgb(30, 41, 59)',
        borderWidth: 2,
      },
    ],
  }
})

const modelChartData = computed(() => {
  const models = Object.keys(modelStats.value).sort((a, b) => 
    modelStats.value[b].total_cost - modelStats.value[a].total_cost
  ).slice(0, 10) // 只显示前10个
  return {
    labels: models,
    datasets: [
      {
        label: '总费用 ($)',
        data: models.map(model => modelStats.value[model].total_cost),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
      },
      {
        label: '总 Tokens (千)',
        data: models.map(model => modelStats.value[model].total_tokens / 1000),
        backgroundColor: 'rgba(34, 197, 94, 0.8)',
      },
    ],
  }
})

const hourlyChartData = computed(() => {
  const hours = Array.from({ length: 24 }, (_, i) => i)
  return {
    labels: hours.map(h => `${h}:00`),
    datasets: [
      {
        label: '请求数',
        data: hours.map(h => hourlyStats.value[String(h)]?.total_requests || 0),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
      },
      {
        label: '总费用 ($)',
        data: hours.map(h => hourlyStats.value[String(h)]?.total_cost || 0),
        backgroundColor: 'rgba(34, 197, 94, 0.8)',
      },
    ],
  }
})

// Chart Options
const mixedChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
      beginAtZero: true,
      ticks: { color: '#9ca3af' },
      grid: { color: 'rgba(156, 163, 175, 0.1)' },
      title: {
        display: true,
        text: 'Tokens (千)',
        color: '#9ca3af',
      },
    },
    y1: {
      type: 'linear' as const,
      display: true,
      position: 'right' as const,
      beginAtZero: true,
      ticks: { color: '#9ca3af' },
      grid: { drawOnChartArea: false },
      title: {
        display: true,
        text: '请求数',
        color: '#9ca3af',
      },
    },
    x: {
      ticks: { color: '#9ca3af' },
      grid: { color: 'rgba(156, 163, 175, 0.1)' },
    },
  },
  plugins: {
    legend: {
      labels: { color: '#9ca3af' },
    },
  },
}

const doughnutChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right' as const,
      labels: { color: '#9ca3af' },
    },
  },
}

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    y: {
      beginAtZero: true,
      ticks: { color: '#9ca3af' },
      grid: { color: 'rgba(156, 163, 175, 0.1)' },
    },
    x: {
      ticks: { color: '#9ca3af' },
      grid: { color: 'rgba(156, 163, 175, 0.1)' },
    },
  },
  plugins: {
    legend: {
      labels: { color: '#9ca3af' },
    },
  },
}

// Helper Functions
const formatNumber = (num: number, decimals: number = 2) => {
  if (num === undefined || num === null) return '0'
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

// Load Functions
const loadAvailableDates = async () => {
  try {
    const response = await getCursorUsageDates()
    if (response.success) {
      availableDates.value = response.dates
      if (response.dates.length > 0) {
        // 设置默认日期范围为最近30天
        const end = new Date()
        const start = new Date()
        start.setDate(start.getDate() - 30)
        endDate.value = end.toISOString().split('T')[0]
        startDate.value = start.toISOString().split('T')[0]
      }
    }
  } catch (error) {
    console.error('加载可用日期失败:', error)
  }
}

const loadStatistics = async () => {
  if (!startDate.value || !endDate.value) {
    return
  }

  loading.value = true
  try {
    // 加载符合条件的CSV文件列表
    const datesRes = await getCursorUsageDatesWithRange(startDate.value, endDate.value)
    if (datesRes.success) {
      filteredDates.value = datesRes.dates
    }

    // 并行加载所有统计数据
    const [totalRes, dailyRes, kindRes, modelRes, hourlyRes, costRes] = await Promise.all([
      getCursorUsageTotalStatistics(startDate.value, endDate.value),
      getCursorUsageDailyStatistics(startDate.value, endDate.value),
      getCursorUsageKindStatistics(startDate.value, endDate.value),
      getCursorUsageModelStatistics(startDate.value, endDate.value),
      getCursorUsageHourlyStatistics(startDate.value, endDate.value),
      getCursorUsageCostStatistics(startDate.value, endDate.value),
    ])

    if (totalRes.success) {
      Object.assign(totalStats, totalRes.data)
    }

    if (dailyRes.success) {
      dailyStats.value = dailyRes.data
    }

    if (kindRes.success) {
      kindStats.value = kindRes.data
    }

    if (modelRes.success) {
      modelStats.value = modelRes.data
    }

    if (hourlyRes.success) {
      hourlyStats.value = hourlyRes.data
    }

    if (costRes.success) {
      costStats.value = costRes.data
    }

    lastUpdated.value = new Date().toLocaleString()
  } catch (error) {
    console.error('加载统计数据失败:', error)
  } finally {
    loading.value = false
  }
}

// Lifecycle
onMounted(async () => {
  await loadAvailableDates()
  if (startDate.value && endDate.value) {
    await loadStatistics()
  }
})
</script>

<style scoped>
/* 自定义样式 */
</style>

