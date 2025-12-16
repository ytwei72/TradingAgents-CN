<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
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

// 数据源选择：'manual' 手动输入股票和时间，'report' 选择分析结果
const dataSource = ref<'manual' | 'report'>('manual')

// 手动输入模式
const stockCode = ref('')
const analysisDate = ref('')
const endDate = ref('')
const targetPrice = ref<number | null>(null)

// 分析结果选择模式
const selectedStockCode = ref('')
const analysisReports = ref<AnalysisReport[]>([])
const selectedReport = ref<AnalysisReport | null>(null)
const loadingReports = ref(false)

// 图表数据
const historicalData = ref<StockHistoricalData[]>([])
const loadingData = ref(false)
const stockInfo = ref<any>(null)

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
    dates.forEach((date, index) => {
      if (index >= analysisDateIndex) {
        targetPriceLine.push(targetPrice.value!)
      } else {
        targetPriceLine.push(null)
      }
    })
  }

  // 目标价格图例文本中追加置信度、风险度（仅在选择分析结果模式时）
  let targetLabel = targetPrice.value !== null ? `目标价格: ${targetPrice.value.toFixed(2)}` : ''
  if (targetPrice.value !== null && selectedReport.value?.formatted_decision) {
    const decision = selectedReport.value.formatted_decision
    const confidenceText = decision.confidence !== undefined
      ? `${(decision.confidence * 100).toFixed(0)}%`
      : '未知'
    const riskText = decision.risk_score !== undefined
      ? `${decision.risk_score}`
      : '未知'
    targetLabel = `目标价格: ${targetPrice.value.toFixed(2)}（置信度：${confidenceText}，风险度：${riskText}）`
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

// 计算默认结束日期（今天）
const getDefaultEndDate = () => {
  const today = new Date()
  return today.toISOString().split('T')[0]
}

// 初始化日期
onMounted(() => {
  endDate.value = getDefaultEndDate()
  const oneMonthAgo = new Date()
  oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1)
  analysisDate.value = oneMonthAgo.toISOString().split('T')[0]
})

// 查询分析结果
const queryAnalysisReports = async () => {
  if (!selectedStockCode.value) {
    return
  }

  loadingReports.value = true
  try {
    const response = await getAnalysisReportsByStock(selectedStockCode.value, 100)
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
  targetPrice.value = report.formatted_decision?.target_price || null
  
  // 自动加载数据
  loadBacktestData()
}

// 加载回测数据
const loadBacktestData = async () => {
  if (!stockCode.value || !analysisDate.value) {
    return
  }

  loadingData.value = true
  try {
    // 计算开始日期（分析日期前一个月）
    const analysisDateObj = new Date(analysisDate.value)
    const startDateObj = new Date(analysisDateObj)
    startDateObj.setMonth(startDateObj.getMonth() - 1)
    const startDate = startDateObj.toISOString().split('T')[0]

    // 使用endDate或默认今天
    const actualEndDate = endDate.value || getDefaultEndDate()

    // 获取历史数据（后端会自动处理数据量不足的情况）
    const response = await getStockHistoricalData(
      stockCode.value,
      startDate,
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
</script>

<template>
  <div class="space-y-6">
    <header class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-white">研判回测</h1>
    </header>

    <!-- 数据源选择 -->
    <div class="bg-[#1e293b] rounded-lg p-6 border border-gray-700">
      <div class="mb-4">
        <label class="block text-sm font-medium text-gray-300 mb-2">数据源选择</label>
        <div class="flex space-x-4">
          <label class="flex items-center">
            <input 
              type="radio" 
              value="manual" 
              v-model="dataSource"
              class="mr-2"
            />
            <span class="text-gray-300">手动输入</span>
          </label>
          <label class="flex items-center">
            <input 
              type="radio" 
              value="report" 
              v-model="dataSource"
              class="mr-2"
            />
            <span class="text-gray-300">选择分析结果</span>
          </label>
        </div>
      </div>

      <!-- 手动输入模式 -->
      <div v-if="dataSource === 'manual'" class="space-y-4">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">股票代码</label>
            <input
              v-model="stockCode"
              type="text"
              placeholder="如：000001"
              class="w-full px-4 py-2 bg-[#0f172a] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">分析日期</label>
            <input
              v-model="analysisDate"
              type="date"
              class="w-full px-4 py-2 bg-[#0f172a] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">结束日期</label>
            <input
              v-model="endDate"
              type="date"
              class="w-full px-4 py-2 bg-[#0f172a] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">目标价格（可选）</label>
            <input
              v-model.number="targetPrice"
              type="number"
              step="0.01"
              placeholder="输入目标价格"
              class="w-full px-4 py-2 bg-[#0f172a] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        <button
          @click="loadBacktestData"
          :disabled="loadingData || !stockCode || !analysisDate"
          class="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition"
        >
          {{ loadingData ? '加载中...' : '开始回测' }}
        </button>
      </div>

      <!-- 分析结果选择模式 -->
      <div v-if="dataSource === 'report'" class="space-y-4">
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
                :disabled="loadingReports || !selectedStockCode"
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition"
              >
                查询
              </button>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-300 mb-2">结束日期</label>
            <input
              v-model="endDate"
              type="date"
              class="w-full px-4 py-2 bg-[#0f172a] border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
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
                <div class="text-white font-semibold">{{ report.stock_symbol }}</div>
                <div class="text-sm text-gray-400 mt-1">
                  分析日期：{{ formatDate(report.analysis_date) }}
                </div>
                <div v-if="report.formatted_decision?.target_price" class="text-sm text-gray-400">
                  目标价：{{ report.formatted_decision.target_price.toFixed(2) }}
                </div>
              </div>
              <div class="text-xs text-gray-500">
                {{ formatDate(new Date(report.timestamp || 0).toISOString()) }}
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
            <!-- 目标价格 Tag -->
            <span
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-sky-900/70 text-sky-100 border border-sky-500/60"
            >
              <span class="mr-1 text-sky-300/90 tag-key">目标价</span>
              <span class="text-sky-100 tag-value">{{ targetPrice.toFixed(2) }}</span>
            </span>
            <!-- 置信度 Tag -->
            <span
              v-if="dataSource === 'report' && selectedReport?.formatted_decision"
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
              v-if="dataSource === 'report' && selectedReport?.formatted_decision"
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
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold text-white">价格对比</h2>
          <div class="text-sm text-gray-400">
            <span class="inline-block w-3 h-3 bg-orange-500 rounded mr-1"></span>
            分析日期：{{ formatDate(analysisDate) }}
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
                <th v-if="targetPrice !== null" class="text-right py-2 px-4 text-gray-300">目标价</th>
                <th v-if="targetPrice !== null" class="text-right py-2 px-4 text-gray-300">误差</th>
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
                <td v-if="targetPrice !== null" class="py-2 px-4 text-right text-red-400">
                  {{ item.date >= analysisDate ? targetPrice.toFixed(2) : '-' }}
                </td>
                <td v-if="targetPrice !== null" class="py-2 px-4 text-right text-gray-400">
                  {{ item.date >= analysisDate && item.close 
                    ? Math.abs(item.close - targetPrice).toFixed(2) 
                    : '-' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loadingData" class="text-center py-12 text-gray-400">
      <p>请选择数据源并加载回测数据</p>
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
</style>

