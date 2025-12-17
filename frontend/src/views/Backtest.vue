<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import DateRangePicker from '../components/DateRangePicker.vue'
import { 
  getStockHistoricalData, 
  getAnalysisReportsByStock,
  getStockBasicInfo,
  type StockHistoricalData,
  type AnalysisReport
} from '../api/index.ts'
import { Line, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// 计算默认结束日期（今天）
const getDefaultEndDate = () => {
  const today = new Date()
  return today.toISOString().split('T')[0]
}

// 根据分析日期计算默认结束日期（分析日期后 3 个月）
const getEndDateByAnalysis = (analysisDateStr: string) => {
  if (!analysisDateStr) {
    return getDefaultEndDate()
  }
  const d = new Date(analysisDateStr)
  if (Number.isNaN(d.getTime())) {
    return getDefaultEndDate()
  }
  d.setMonth(d.getMonth() + 3)
  return d.toISOString().split('T')[0]
}

// 选择分析结果模式
const stockCode = ref('')           // 当前用于回测的股票代码（从分析结果中选择）
const analysisDate = ref('')        // 分析日期（从分析结果中选择）
const startDate = ref('')           // 数据区间开始日期
const endDate = ref('')             // 数据区间结束日期
const rangeDays = ref<number | null>(null)
const targetPrice = ref<number | null>(null)

// 分析结果列表与筛选
const selectedStockCode = ref('')
const analysisReports = ref<AnalysisReport[]>([])
const selectedReport = ref<AnalysisReport | null>(null)
const loadingReports = ref(false)

// 分析结果筛选的起止日期（仅用于报告筛选，不影响价格对比中的价格数据区间）
const reportsStartDate = ref('') // 默认在 onMounted 中设置为结束日期往前 1 个月
const reportsEndDate = ref(getDefaultEndDate())
const reportsDays = ref<number | null>(null)

// 图表数据
const historicalData = ref<StockHistoricalData[]>([])
const loadingData = ref(false)
const stockInfo = ref<any>(null)

// 分析日期对应的收盘价（用于计算预期收益）
const analysisClosePrice = computed(() => {
  if (!historicalData.value.length || !analysisDate.value) {
    return null
  }

  const dates = historicalData.value.map(d => d.date)
  // 先尝试精确匹配分析日期
  let index = dates.findIndex(d => d === analysisDate.value)

  // 如果没有精确匹配，则取「分析日期之前最近的一个交易日」
  if (index < 0) {
    const analysisDateObj = new Date(analysisDate.value)
    for (let i = dates.length - 1; i >= 0; i--) {
      const dateObj = new Date(dates[i])
      if (dateObj <= analysisDateObj) {
        index = i
        break
      }
    }
  }

  if (index < 0) {
    return null
  }

  const item = historicalData.value[index]
  return typeof item.close === 'number' ? item.close : null
})

// 计算标签颜色（0% 绿色 → 100% 红色）
const getGradientColor = (value: number) => {
  const v = Math.max(0, Math.min(1, value)) // 0~1
  const hue = (1 - v) * 120 // 0=红,1=绿；这里我们会根据场景反转
  return `hsl(${hue}, 70%, 45%)`
}

// 风险度：0% 绿色，100% 红色
const getRiskTagStyle = (rawValue: number | undefined) => {
  if (rawValue === undefined || Number.isNaN(rawValue)) {
    return {}
  }
  // 支持传入 0~1 或 0~100，统一转成 0~1
  const value = rawValue > 1 ? rawValue / 100 : rawValue
  return {
    backgroundColor: getGradientColor(value),
    color: '#0b1120',
  }
}

// 置信度：0% 红色，100% 绿色（与风险度相反）
const getConfidenceTagStyle = (rawValue: number | undefined) => {
  if (rawValue === undefined || Number.isNaN(rawValue)) {
    return {}
  }
  const value = rawValue > 1 ? rawValue / 100 : rawValue
  // 与风险相反：高置信度更绿、低置信度更红
  return {
    backgroundColor: getGradientColor(1 - value),
    color: '#0b1120',
  }
}

// 图表配置
const chartData = computed(() => {
  if (!historicalData.value || historicalData.value.length === 0) {
    return null
  }

  const dates = historicalData.value.map(d => d.date)
  const closes = historicalData.value.map(d => d.close)

  // 找到分析日期在数据中的位置（使用最接近的日期）
  let analysisDateIndex = -1
  if (analysisDate.value) {
    // 尝试精确匹配
    analysisDateIndex = dates.findIndex(d => d === analysisDate.value)
    // 如果找不到，尝试找最接近的日期（分析日期之后最近的）
    if (analysisDateIndex < 0) {
      const analysisDateObj = new Date(analysisDate.value)
      for (let i = 0; i < dates.length; i++) {
        const dateObj = new Date(dates[i])
        if (dateObj >= analysisDateObj) {
          analysisDateIndex = i
          break
        }
      }
      // 如果还是找不到，使用最后一个索引
      if (analysisDateIndex < 0) {
        analysisDateIndex = dates.length - 1
      }
    }
  }
  
  // 目标价格线（仅在分析日期之后）
  const targetPriceLine: (number | null)[] = []
  if (targetPrice.value !== null && analysisDateIndex >= 0) {
    dates.forEach((_date, index) => {
      if (index >= analysisDateIndex) {
        targetPriceLine.push(targetPrice.value!)
      } else {
        targetPriceLine.push(null)
      }
    })
  }

  // 目标价格图例文本中追加置信度、风险度（仅在选择分析结果模式时）
  let targetLabel = targetPrice.value !== null ? `目标价格: ${targetPrice.value.toFixed(2)}` : ''
  // 这里保留 targetLabel 为简单的目标价格描述，详细的置信度 / 风险度通过标签单独展示

  // 预期收益(%)线（仅在分析日期之后）
  const profitPercentLine: (number | null)[] = []
  if (analysisClosePrice.value !== null && analysisDateIndex >= 0) {
    dates.forEach((_date, index) => {
      if (index >= analysisDateIndex && historicalData.value[index].close !== undefined) {
        const close = historicalData.value[index].close!
        const profitPercent = ((close - analysisClosePrice.value!) / analysisClosePrice.value!) * 100
        profitPercentLine.push(profitPercent)
      } else {
        profitPercentLine.push(null)
      }
    })
  }

  return {
    labels: dates,
    datasets: [
      {
        label: '收盘价',
        data: closes,
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: false,
        tension: 0.1,
        yAxisID: 'y',
      },
      ...(targetPrice.value !== null && analysisDateIndex >= 0 ? [{
        label: targetLabel,
        data: targetPriceLine,
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'transparent',
        borderDash: [5, 5],
        borderWidth: 2,
        fill: false,
        pointRadius: 0,
        yAxisID: 'y',
      }] : []),
      ...(analysisClosePrice.value !== null && analysisDateIndex >= 0 ? [{
        label: '预期收益(%)',
        data: profitPercentLine,
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'transparent',
        borderDash: [3, 3],
        borderWidth: 2,
        fill: false,
        pointRadius: 3,
        yAxisID: 'y1',
      }] : []),
    ]
  }
})

const volumeChartData = computed(() => {
  if (!historicalData.value || historicalData.value.length === 0) {
    return null
  }

  const dates = historicalData.value.map(d => d.date)
  const volumes = historicalData.value.map(d => d.volume || 0)

  return {
    labels: dates,
    datasets: [
      {
        label: '成交量',
        data: volumes,
        backgroundColor: 'rgba(107, 114, 128, 0.5)',
        yAxisID: 'y1',
      }
    ]
  }
})

const chartOptions = computed(() => {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: {
          color: 'rgb(203, 213, 225)',
        }
      },
      // 仅保留悬浮提示，去掉每个点上的数值标识
      datalabels: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(30, 41, 59, 0.9)',
        titleColor: 'rgb(203, 213, 225)',
        bodyColor: 'rgb(203, 213, 225)',
        borderColor: 'rgb(59, 130, 246)',
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        ticks: {
          color: 'rgb(203, 213, 225)',
          maxRotation: 45,
          minRotation: 45,
        },
        grid: {
          color: 'rgba(203, 213, 225, 0.1)',
        }
      },
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        ticks: {
          color: 'rgb(203, 213, 246)',
        },
        grid: {
          color: 'rgba(59, 130, 246, 0.1)',
        },
        title: {
          display: true,
          text: '价格',
          color: 'rgb(203, 213, 225)',
        }
      },
      y1: {
        type: 'linear' as const,
        display: true,
        position: 'right' as const,
        ticks: {
          color: 'rgb(34, 197, 94)',
          callback: function(value: number | string) {
            return value + '%'
          }
        },
        grid: {
          drawOnChartArea: false,
        },
        title: {
          display: true,
          text: '预期收益(%)',
          color: 'rgb(203, 213, 225)',
        }
      },
    },
  }
})

const volumeChartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  interaction: {
    mode: 'index' as const,
    intersect: false,
  },
  plugins: {
    legend: {
      display: false,
    },
    tooltip: {
      backgroundColor: 'rgba(30, 41, 59, 0.9)',
      titleColor: 'rgb(203, 213, 225)',
      bodyColor: 'rgb(203, 213, 225)',
      borderColor: 'rgb(107, 114, 128)',
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      ticks: {
        color: 'rgb(203, 213, 225)',
        maxRotation: 45,
        minRotation: 45,
      },
      grid: {
        color: 'rgba(203, 213, 225, 0.1)',
      }
    },
    y1: {
      type: 'linear' as const,
      display: true,
      position: 'left' as const,
      ticks: {
        color: 'rgb(156, 163, 175)',
      },
      grid: {
        color: 'rgba(107, 114, 128, 0.1)',
      },
      title: {
        display: true,
        text: '成交量',
        color: 'rgb(203, 213, 225)',
      }
    },
  },
}))

// 初始化日期
onMounted(() => {
  // 默认分析日期为今天，数据区间为：今天往前推 6 个月 ~ 今天
  const todayStr = getDefaultEndDate()
  analysisDate.value = todayStr
  
  // 计算默认开始日期（今天往前推 6 个月）
  const startDateObj = new Date(todayStr)
  startDateObj.setMonth(startDateObj.getMonth() - 6)
  startDate.value = startDateObj.toISOString().split('T')[0]
  
  // 默认结束日期为今天（而不是分析日后 3 个月），即最近一个月
  endDate.value = todayStr

  // 报告筛选区间同样使用「近一个月」：起始日期为今天往前推 1 个月，结束日期为今天
  reportsStartDate.value = startDate.value
  reportsEndDate.value = todayStr

  // 首次初始化时就查询一次研究报告（无股票代码，结束日期为当天）
  queryAnalysisReports()
})

// 查询分析结果
const queryAnalysisReports = async () => {
  loadingReports.value = true
  try {
    // 当股票代码未填写时，传递空字符串，具体是否使用 all 由 API 层处理
    const stockSymbol = selectedStockCode.value || ''

    // 报告筛选起始日期：优先使用用户选择的起始日期，否则使用「结束日期往前 1 个月」
    const actualReportsEndDate = reportsEndDate.value || getDefaultEndDate()
    const actualReportsStartDate = reportsStartDate.value || (() => {
      const endObj = new Date(actualReportsEndDate)
      endObj.setMonth(endObj.getMonth() - 1)
      return endObj.toISOString().split('T')[0]
    })()

    const response = await getAnalysisReportsByStock(
      stockSymbol,
      100,
      actualReportsStartDate || undefined,
      actualReportsEndDate || undefined
    )
    if (response.success) {
      analysisReports.value = response.data
    }
  } catch (error) {
    console.error('查询分析结果失败:', error)
  } finally {
    loadingReports.value = false
  }
}

// 选择分析结果
const selectReport = (report: AnalysisReport) => {
  selectedReport.value = report
  stockCode.value = report.stock_symbol
  analysisDate.value = report.analysis_date
  
  // 计算默认开始日期（分析日前 1 个月）
  const startDateObj = new Date(report.analysis_date)
  startDateObj.setMonth(startDateObj.getMonth() - 1)
  startDate.value = startDateObj.toISOString().split('T')[0]
  
  // 使用分析日期后 3 个月作为默认结束日期（用户仍可手动修改）
  endDate.value = getEndDateByAnalysis(report.analysis_date)
  targetPrice.value = report.formatted_decision?.target_price || null
  
  // 自动加载数据
  loadBacktestData()
}

// 加载回测数据
const loadBacktestData = async () => {
  if (!stockCode.value) {
    return
  }

  // 如果尚未设置分析日期，则在当前数据区间内自动选用「结束日期」（若无结束日期则使用开始日期）
  if (!analysisDate.value) {
    if (endDate.value) {
      analysisDate.value = endDate.value
    } else if (startDate.value) {
      analysisDate.value = startDate.value
    }
  }

  loadingData.value = true
  try {
    // 使用用户设置的起止日期，如果没有设置则使用默认值
    const actualStartDate = startDate.value || (() => {
      const analysisDateObj = new Date(analysisDate.value)
      const startDateObj = new Date(analysisDateObj)
      startDateObj.setMonth(startDateObj.getMonth() - 1)
      return startDateObj.toISOString().split('T')[0]
    })()

    const actualEndDate = endDate.value || getDefaultEndDate()

    // 获取历史数据（后端会自动处理数据量不足的情况）
    const response = await getStockHistoricalData(
      stockCode.value,
      actualStartDate,
      actualEndDate,
      60,  // 期望60条数据
      analysisDate.value  // 传递分析日期，用于智能调整数据范围
    )

    if (response.success && response.data) {
      historicalData.value = response.data
      
      // 获取股票基本信息
      try {
        const infoResponse = await getStockBasicInfo(stockCode.value)
        if (infoResponse.success) {
          stockInfo.value = infoResponse.data
        }
      } catch (error) {
        console.error('获取股票信息失败:', error)
      }
    }
  } catch (error) {
    console.error('加载回测数据失败:', error)
  } finally {
    loadingData.value = false
  }
}

// 格式化日期
const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  })
}


// 打开日期选择器
const openDatePicker = (inputId: string) => {
  const input = document.getElementById(inputId) as HTMLInputElement | null
  if (!input) return

  // 支持原生 showPicker 的浏览器
  if ('showPicker' in input && typeof (input as any).showPicker === 'function') {
    ;(input as any).showPicker()
  } else {
    input.focus()
    input.click()
  }
}
</script>

<template>
  <div class="space-y-6">
    <header class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-white">研判回测</h1>
    </header>

    <!-- 数据源选择 -->
    <div class="bg-[#1e293b] rounded-lg p-6 border border-gray-700">
      <!-- 分析结果选择 -->
      <div class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">股票代码</label>
            <div class="flex space-x-2">
              <input
                v-model="selectedStockCode"
                type="text"
                placeholder="如：000001"
                class="flex-1 px-4 py-2 bg-[#0f172a] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                @click="queryAnalysisReports"
                :disabled="loadingReports"
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition"
              >
                查询
              </button>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">结束日期（报告筛选）</label>
            <div class="relative">
              <DateRangePicker
                :quick-days="[]"
                label=""
                v-model:modelStartDate="reportsStartDate"
                v-model:modelEndDate="reportsEndDate"
                v-model:modelDays="reportsDays"
                :range-separator="'到'"
                :start-placeholder="'开始日期'"
                :end-placeholder="'结束日期'"
                :end-input-id="'report-end-date-input'"
                :start-input-id="'report-end-date-input'"
              />
              <label
                for="report-end-date-input"
                class="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer text-blue-400 hover:text-blue-300 transition-colors z-10"
                @click="openDatePicker('report-end-date-input')"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 002 2z"></path>
                </svg>
              </label>
            </div>
          </div>
        </div>

        <!-- 分析结果列表 -->
        <div v-if="loadingReports" class="text-center py-4 text-gray-400">
          加载中...
        </div>
        <div v-else-if="analysisReports.length > 0" class="max-h-60 overflow-y-auto">
          <div
            v-for="report in analysisReports"
            :key="report.analysis_id"
            @click="selectReport(report)"
            :class="[
              'p-4 mb-2 border rounded-lg cursor-pointer transition',
              selectedReport?.analysis_id === report.analysis_id
                ? 'bg-blue-900/30 border-blue-500'
                : 'bg-[#0f172a] border-gray-600 hover:border-gray-500'
            ]"
          >
            <div class="flex justify-between items-start">
              <div>
                <!-- 上市公司名称 + 股票代码 -->
                <div class="text-white font-semibold">
                  <span v-if="report.stock_name || report.company_name">
                    {{ report.stock_name || report.company_name }}
                  </span>
                  <span class="ml-1 text-gray-300">
                    （{{ report.stock_symbol }}）
                  </span>
                </div>
                <div
                  v-if="report.formatted_decision?.target_price"
                  class="text-sm text-gray-400 mt-1 space-y-1"
                >
                  <div v-if="report.formatted_decision">
                    目标价：{{ report.formatted_decision.target_price.toFixed(2) }}
                    ，置信度：
                    {{
                      report.formatted_decision.confidence !== undefined
                        ? (
                            (report.formatted_decision.confidence > 1
                              ? report.formatted_decision.confidence
                              : report.formatted_decision.confidence * 100
                            ).toFixed(0)
                          ) + '%'
                        : '未知'
                    }}
                    ，风险度：
                    {{
                      report.formatted_decision.risk_score !== undefined
                        ? (
                            (report.formatted_decision.risk_score > 1
                              ? report.formatted_decision.risk_score
                              : report.formatted_decision.risk_score * 100
                            ).toFixed(0)
                          ) + '%'
                        : '未知'
                    }}
                  </div>
                </div>
              </div>
              <!-- 右上角日期使用分析日期 -->
              <div class="text-xs text-gray-500">
                分析日期：{{ formatDate(report.analysis_date) }}
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="selectedStockCode && !loadingReports" class="text-center py-4 text-gray-400">
          未找到分析结果
        </div>
      </div>
    </div>

    <!-- 图表展示 -->
    <div v-if="historicalData.length > 0" class="space-y-6">
      <!-- 股票信息 -->
          <div v-if="stockInfo" class="bg-[#1e293b] rounded-lg p-4 border border-gray-700">
        <div class="flex flex-wrap items-center gap-3">
          <div class="text-white font-bold text-lg">{{ stockInfo.name || stockCode }}</div>
          <div class="text-gray-400 text-sm">{{ stockCode }}</div>
          <div v-if="targetPrice !== null" class="flex flex-wrap items-center gap-2 ml-auto">
            <!-- 操作 Action Tag -->
            <span
              v-if="selectedReport?.formatted_decision?.action"
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-900/70 text-emerald-100 border border-emerald-500/60"
            >
              <span class="mr-1 text-emerald-300/90 tag-key">建议操作</span>
              <span class="text-emerald-100 tag-value">
                {{ selectedReport!.formatted_decision!.action }}
              </span>
            </span>
            <!-- 目标价格 Tag -->
            <span
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-sky-900/70 text-sky-100 border border-sky-500/60"
            >
              <span class="mr-1 text-sky-300/90 tag-key">目标价</span>
              <span class="text-sky-100 tag-value">{{ targetPrice.toFixed(2) }}</span>
            </span>
            <!-- 置信度 Tag -->
            <span
              v-if="selectedReport?.formatted_decision"
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border border-slate-700/70"
              :style="getConfidenceTagStyle(selectedReport!.formatted_decision!.confidence)"
            >
              <span class="mr-1 tag-key">置信度</span>
              <span class="tag-value">
                {{
                  selectedReport!.formatted_decision!.confidence !== undefined
                    ? (
                        (selectedReport!.formatted_decision!.confidence > 1
                          ? selectedReport!.formatted_decision!.confidence
                          : selectedReport!.formatted_decision!.confidence * 100
                        ).toFixed(0)
                      ) + '%'
                    : '未知'
                }}
              </span>
            </span>
            <!-- 风险度 Tag -->
            <span
              v-if="selectedReport?.formatted_decision"
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold border border-slate-700/70"
              :style="getRiskTagStyle(selectedReport!.formatted_decision!.risk_score)"
            >
              <span class="mr-1 tag-key">风险度</span>
              <span class="tag-value">
                {{
                  selectedReport!.formatted_decision!.risk_score !== undefined
                    ? (
                        (selectedReport!.formatted_decision!.risk_score > 1
                          ? selectedReport!.formatted_decision!.risk_score
                          : selectedReport!.formatted_decision!.risk_score * 100
                        ).toFixed(0)
                      ) + '%'
                    : '未知'
                }}
              </span>
            </span>
          </div>
        </div>
      </div>

      <!-- 价格图表 -->
      <div class="bg-[#1e293b] rounded-lg p-6 border border-gray-700">
        <div class="flex flex-col md:flex-row md:items-center md:justify-between mb-4 gap-3">
          <div class="flex items-center gap-3">
            <h2 class="text-xl font-bold text-white">价格对比</h2>
            <div class="text-sm text-gray-400 flex items-center">
              <span class="inline-block w-3 h-3 bg-orange-500 rounded mr-1"></span>
              分析日期：{{ formatDate(analysisDate) }}
            </div>
          </div>
          <!-- 数据区间编辑（起止日期都可编辑） -->
          <div class="flex items-center gap-2 text-sm">
            <span class="text-gray-300">📅 数据区间</span>
            <div class="flex items-center space-x-2">
              <div class="flex-1 min-w-[140px] relative">
                <DateRangePicker
                  :quick-days="[]"
                  label=""
                  v-model:modelStartDate="startDate"
                  v-model:modelEndDate="endDate"
                  v-model:modelDays="rangeDays"
                  :range-separator="'至'"
                  :start-placeholder="'开始日期'"
                  :end-placeholder="'结束日期'"
                  :start-input-id="'backtest-start-date-input'"
                  :end-input-id="'backtest-end-date-input'"
                />
              </div>
              <button
                @click="loadBacktestData"
                :disabled="loadingData || !stockCode"
                class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-md transition-colors text-xs md:text-sm"
              >
                应用
              </button>
            </div>
          </div>
        </div>
        <div class="h-96">
          <Line v-if="chartData" :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <!-- 成交量图表 -->
      <div class="bg-[#1e293b] rounded-lg p-6 border border-gray-700">
        <h2 class="text-xl font-bold text-white mb-4">成交量</h2>
        <div class="h-64">
          <Bar v-if="volumeChartData" :data="volumeChartData" :options="volumeChartOptions" />
        </div>
      </div>

      <!-- 数据表格 -->
      <div class="bg-[#1e293b] rounded-lg p-6 border border-gray-700">
        <h2 class="text-xl font-bold text-white mb-4">数据明细</h2>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-600">
                <th class="text-left py-2 px-4 text-gray-300">日期</th>
                <th class="text-right py-2 px-4 text-gray-300">收盘价</th>
                <th class="text-right py-2 px-4 text-gray-300">开盘价</th>
                <th class="text-right py-2 px-4 text-gray-300">最高价</th>
                <th class="text-right py-2 px-4 text-gray-300">最低价</th>
                <th class="text-right py-2 px-4 text-gray-300">成交量</th>
                <th class="text-right py-2 px-4 text-gray-300">预期收益(元)</th>
                <th class="text-right py-2 px-4 text-gray-300">预期收益(%)</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(item, index) in historicalData"
                :key="index"
                :class="[
                  'border-b border-gray-700',
                  item.date === analysisDate || (index > 0 && historicalData[index - 1].date < analysisDate && item.date >= analysisDate) 
                    ? 'bg-orange-900/20' : ''
                ]"
              >
                <td class="py-2 px-4 text-gray-300">
                  {{ item.date }}
                  <span v-if="item.date === analysisDate" class="ml-2 text-xs text-orange-400">分析日期</span>
                </td>
                <td class="py-2 px-4 text-right text-white">{{ item.close?.toFixed(2) }}</td>
                <td class="py-2 px-4 text-right text-gray-400">{{ item.open?.toFixed(2) }}</td>
                <td class="py-2 px-4 text-right text-gray-400">{{ item.high?.toFixed(2) }}</td>
                <td class="py-2 px-4 text-right text-gray-400">{{ item.low?.toFixed(2) }}</td>
                <td class="py-2 px-4 text-right text-gray-400">{{ item.volume?.toLocaleString() }}</td>
                <td class="py-2 px-4 text-right text-gray-400">
                  {{
                    analysisClosePrice !== null &&
                    item.close !== undefined &&
                    item.date >= analysisDate
                      ? (item.close - analysisClosePrice).toFixed(2)
                      : '--'
                  }}
                </td>
                <td class="py-2 px-4 text-right text-gray-400">
                  {{
                    analysisClosePrice !== null &&
                    item.close !== undefined &&
                    item.date >= analysisDate
                      ? (((item.close - analysisClosePrice) / analysisClosePrice) * 100).toFixed(2) + '%'
                      : '--'
                  }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loadingData" class="text-center py-12 text-gray-400">
      <p>请选择分析结果并加载回测数据</p>
    </div>
  </div>
</template>

<style scoped>
/* Chart.js 样式覆盖 */
:deep(.chartjs-render-monitor) {
  color: rgb(203, 213, 225);
}

/* Tag 中文本排版：key: value，key 放大 1.5 倍，value 放大 2 倍 */
.tag-key {
  font-size: 1.3em;
}

.tag-value {
  font-size: 1.8em;
}

/* 日期选择器样式 */
.date-input {
  color-scheme: dark;
  position: relative;
}

.date-input::-webkit-calendar-picker-indicator {
  display: none;
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
  pointer-events: none;
}

/* Firefox 日期选择器样式 - 隐藏原生图标 */
.date-input::-moz-calendar-picker-indicator {
  display: none;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

/* 日期选择器文字颜色 */
.date-input::-webkit-datetime-edit-text {
  color: #e5e7eb;
}

.date-input::-webkit-datetime-edit-month-field,
.date-input::-webkit-datetime-edit-day-field,
.date-input::-webkit-datetime-edit-year-field {
  color: #e5e7eb;
}

.date-input::-webkit-datetime-edit-month-field:focus,
.date-input::-webkit-datetime-edit-day-field:focus,
.date-input::-webkit-datetime-edit-year-field:focus {
  background-color: rgba(59, 130, 246, 0.2);
  color: #ffffff;
  border-radius: 2px;
}

/* 确保输入框内的文字和图标对比度足够 */
.date-input:focus {
  border-color: #3b82f6;
  background-color: #0f172a;
}

.date-input:hover {
  border-color: #3b82f6;
}

/* 日历弹出窗口样式（Chrome/Edge） - 使用深色主题 */
.date-input::-webkit-calendar-picker-indicator {
  color-scheme: dark;
}
</style>

