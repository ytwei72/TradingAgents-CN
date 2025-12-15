<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-white">用量统计</h1>
      <div class="text-sm text-gray-400">
        最后更新: {{ lastUpdated }}
      </div>
    </div>

    <!-- Overall Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">📥 总输入</div>
        <div class="text-2xl font-bold text-white">{{ formatNumber(overallStats.total_input_tokens, 0) }}</div>
        <div class="text-xs text-gray-500 mt-2">
          占比: {{ overallStats.total_input_tokens + overallStats.total_output_tokens > 0 ? 
            ((overallStats.total_input_tokens / (overallStats.total_input_tokens + overallStats.total_output_tokens)) * 100).toFixed(1) + '%' : '0%' }}
        </div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">📤 总输出</div>
        <div class="text-2xl font-bold text-white">{{ formatNumber(overallStats.total_output_tokens, 0) }}</div>
        <div class="text-xs text-gray-500 mt-2">
          占比: {{ overallStats.total_input_tokens + overallStats.total_output_tokens > 0 ? 
            ((overallStats.total_output_tokens / (overallStats.total_input_tokens + overallStats.total_output_tokens)) * 100).toFixed(1) + '%' : '0%' }}
        </div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">🔢 请求数</div>
        <div class="text-2xl font-bold text-white">{{ formatNumber(overallStats.total_requests, 0) }}</div>
        <div class="text-xs text-gray-500 mt-2">所有历史数据</div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">💰 总费用</div>
        <div class="text-2xl font-bold text-white">${{ formatNumber(overallStats.total_cost, 4) }}</div>
        <div class="text-xs text-gray-500 mt-2">所有历史数据</div>
      </div>
    </div>

    <!-- Time Range Stats Section -->
    <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
      <div class="flex flex-col md:flex-row justify-between items-center mb-6 gap-4">
        <div class="flex items-center gap-4">
          <h2 class="text-lg font-semibold text-white">区间统计详情</h2>
          
          <!-- Toggle for Color Scheme -->
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-400">配色方案</span>
            <button
              @click="showColorScheme = !showColorScheme"
              class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900"
              :class="showColorScheme ? 'bg-blue-600' : 'bg-gray-600'"
            >
              <span
                class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                :class="showColorScheme ? 'translate-x-6' : 'translate-x-1'"
              ></span>
            </button>
          </div>
        </div>
        
        <!-- Date Range Picker -->
        <div class="flex items-center space-x-2 bg-[#0f172a] p-1 rounded-lg border border-gray-700">
          <button 
            v-for="days in [7, 30, 90]" 
            :key="days"
            @click="setDaysRange(days)"
            class="px-3 py-1.5 text-sm rounded-md transition-colors"
            :class="selectedRange.type === 'days' && selectedRange.value === days ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'"
          >
            近{{ days }}天
          </button>
          <div class="w-px h-4 bg-gray-700 mx-2"></div>
          <div class="flex items-center space-x-2 px-2">
            <input 
              type="date" 
              v-model="customDate.start"
              class="bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 border border-gray-600 cursor-pointer"
              :max="customDate.end || undefined"
            >
            <span class="text-gray-500">-</span>
            <input 
              type="date" 
              v-model="customDate.end"
              class="bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1 border border-gray-600 cursor-pointer"
              :min="customDate.start || undefined"
            >
            <button 
              @click="applyCustomDate"
              class="ml-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="!customDate.start || !customDate.end"
            >
              应用
            </button>
          </div>
        </div>
      </div>

      <!-- Color Scheme Selector -->
      <div v-show="showColorScheme" class="parchment-chart-container mb-6">
        <div class="flex flex-col md:flex-row items-start md:items-center gap-4">
          <div class="flex-1 relative z-10">
            <label class="text-sm font-medium text-[#3d2817] mb-2 block font-semibold">🎨 图表配色方案</label>
            <select 
              v-model="selectedColorScheme"
              @change="updateCharts"
              class="w-full bg-[#f9f0dd] text-[#3d2817] px-4 py-2 rounded-lg border-2 border-[#a0826d] focus:outline-none focus:border-[#8b6539] transition-colors shadow-inner"
            >
              <option v-for="(scheme, key) in colorSchemes" :key="key" :value="key">
                {{ key }} - {{ scheme.description }}
              </option>
            </select>
          </div>
          <div class="flex-shrink-0 relative z-10">
            <div class="text-sm font-medium text-[#3d2817] mb-2 font-semibold">配色预览</div>
            <div class="flex gap-2">
              <div 
                v-for="(color, idx) in colorSchemes[selectedColorScheme].colors" 
                :key="idx"
                :style="{ backgroundColor: color }"
                class="w-12 h-12 rounded-lg border-2 border-[#a0826d] shadow-md"
                :title="color"
              ></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <!-- Provider Distribution -->
        <div class="parchment-chart-container">
          <h3 class="chart-title">厂商消耗分布 (Cost)</h3>
          <div class="h-64 relative">
            <Pie v-if="charts.provider.data" :data="charts.provider.data" :options="pieOptions" />
            <div v-else class="flex items-center justify-center h-full text-[#8b6539]">加载中...</div>
          </div>
        </div>

        <!-- Model Distribution -->
        <div class="parchment-chart-container">
          <h3 class="chart-title">模型消耗分布 (Cost)</h3>
          <div class="h-64 relative">
            <Pie v-if="charts.model.data" :data="charts.model.data" :options="pieOptions" />
            <div v-else class="flex items-center justify-center h-full text-[#8b6539]">加载中...</div>
          </div>
        </div>

        <!-- Token Distribution -->
        <div class="parchment-chart-container">
          <h3 class="chart-title">输入/输出 Token 比例</h3>
          <div class="h-64 relative">
            <Pie v-if="charts.token.data" :data="charts.token.data" :options="pieOptions" />
            <div v-else class="flex items-center justify-center h-full text-[#8b6539]">加载中...</div>
          </div>
        </div>
      </div>

      <!-- Usage Trend Chart -->
      <div class="parchment-chart-container-large">
        <h3 class="chart-title">每日模型使用趋势 (Tokens)</h3>
        <div class="h-80 relative">
          <Bar v-if="charts.daily.data" :data="charts.daily.data" :options="barOptions" />
          <div v-else class="flex items-center justify-center h-full text-[#8b6539]">加载中...</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title
} from 'chart.js'
import ChartDataLabels from 'chartjs-plugin-datalabels'
import { Pie, Bar } from 'vue-chartjs'

// Register ChartJS components
ChartJS.register(
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  ChartDataLabels
)

// 配色方案定义 - 羊皮纸风格专属配色
const colorSchemes: Record<string, { colors: string[], description: string }> = {
  '彩绘古卷': {
    colors: ['#0891B2', '#D77A61', '#15803D', '#D35400', '#A0522D', '#B91C1C'],
    description: '色彩丰富，对比鲜明，如古卷彩绘'
  },
  '古典棕褐': {
    colors: ['#8B4513', '#A0522D', '#CD853F', '#D2691E', '#B8860B', '#DAA520'],
    description: '古典沉稳，与羊皮纸完美融合'
  },
  '暖秋大地': {
    colors: ['#C17817', '#E67E22', '#D35400', '#CA6F1E', '#AF601A', '#9C640C'],
    description: '秋日暖阳，大地色系'
  },
  '琥珀宝石': {
    colors: ['#D97706', '#F59E0B', '#FBBF24', '#B45309', '#92400E', '#78350F'],
    description: '琥珀光泽，贵气典雅'
  },
  '复古红棕': {
    colors: ['#B91C1C', '#DC2626', '#A0826D', '#8B4513', '#B8860B', '#CD853F'],
    description: '复古经典，红棕交织'
  },
  '橄榄青铜': {
    colors: ['#65A30D', '#84CC16', '#A16207', '#CA8A04', '#92400E', '#854D0E'],
    description: '橄榄枝叶，青铜古韵'
  },
  '深海琥珀': {
    colors: ['#0E7490', '#0891B2', '#B45309', '#D97706', '#92400E', '#065F46'],
    description: '深海蓝绿与琥珀融合'
  },
  '赤陶土': {
    colors: ['#BE4A2F', '#D77A61', '#B7410E', '#C1502E', '#9C5D34', '#8B5A3C'],
    description: '赤陶器色，泥土芬芳'
  },
  '森林棕绿': {
    colors: ['#166534', '#15803D', '#854D0E', '#A16207', '#78350F', '#065F46'],
    description: '森林深处，棕绿交错'
  },
  '酒红金棕': {
    colors: ['#991B1B', '#B91C1C', '#B45309', '#D97706', '#92400E', '#7C2D12'],
    description: '美酒佳酿，金棕辉映'
  },
  '岩石赭石': {
    colors: ['#57534E', '#78716C', '#A8A29E', '#A16207', '#92400E', '#78350F'],
    description: '岩石肌理，赭石天然'
  }
}

// State
const selectedColorScheme = ref('彩绘古卷')
const showColorScheme = ref(false) // 配色方案默认隐藏
const lastUpdated = ref(new Date().toLocaleString())
const overallStats = ref({
  total_cost: 0,
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_requests: 0,
  avg_cost: 0
})

const selectedRange = ref({ type: 'days', value: 30 })
const customDate = reactive({
  start: '',
  end: ''
})

const charts = reactive({
  provider: { data: null as any },
  model: { data: null as any },
  token: { data: null as any },
  daily: { data: null as any }
})

// Chart Options
const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  layout: {
    padding: {
      left: 20,
      right: 20,
      top: 20,
      bottom: 20
    }
  },
  plugins: {
    legend: {
      position: 'right' as const,
      labels: { 
        color: '#3d2817', // 羊皮纸深色文字
        boxWidth: 12,
        padding: 15,
        font: { size: 11 },
        generateLabels: function(chart: any) {
          const data = chart.data;
          if (data.labels.length && data.datasets.length) {
            const dataset = data.datasets[0];
            
            return data.labels.map((label: string, i: number) => {
              return {
                text: label, // 仅显示模型名称
                fillStyle: dataset.backgroundColor[i],
                hidden: false,
                index: i
              };
            });
          }
          return [];
        }
      }
    },
    datalabels: {
      color: '#3d2817',
      font: {
        weight: 'bold' as const,
        size: 11
      },
      formatter: (value: number, context: any) => {
        const dataset = context.dataset.data;
        const total = dataset.reduce((a: number, b: number) => a + b, 0);
        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
        return `${percentage}%`; // 在饼图上显示百分比
      },
      anchor: 'end' as const,
      align: 'end' as const,
      offset: 5,
      backgroundColor: 'rgba(249, 240, 221, 0.8)',
      borderRadius: 3,
      padding: 4
    },
    tooltip: {
      backgroundColor: 'rgba(244, 232, 208, 0.95)', // 羊皮纸背景色
      titleColor: '#3d2817', // 深色标题
      bodyColor: '#2d1810', // 深色内容
      borderColor: '#a0826d', // 羊皮纸边框色
      borderWidth: 2,
      callbacks: {
        title: function(context: any) {
          return context[0].label || ''; // 第一行：模型名
        },
        label: function(context: any) {
          const value = context.parsed || 0;
          const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0);
          const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0';
          return `${value.toLocaleString()} (${percentage}%)`; // 第二行：数值 (百分比)
        }
      }
    }
  }
}

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      grid: { 
        color: 'rgba(160, 130, 109, 0.2)', // 羊皮纸网格色
        borderColor: '#a0826d'
      },
      ticks: { 
        color: '#3d2817', // 羊皮纸深色文字
        font: { size: 11 }
      }
    },
    y: {
      grid: { 
        color: 'rgba(160, 130, 109, 0.2)', // 羊皮纸网格色
        borderColor: '#a0826d'
      },
      ticks: { 
        color: '#3d2817', // 羊皮纸深色文字
        font: { size: 11 }
      }
    }
  },
  plugins: {
    legend: {
      labels: { 
        color: '#3d2817', // 羊皮纸深色文字
        font: { size: 12 }
      }
    },
    datalabels: {
      display: false // 柱状图不显示数据标签
    },
    tooltip: {
      backgroundColor: 'rgba(244, 232, 208, 0.95)', // 羊皮纸背景色
      titleColor: '#3d2817', // 深色标题
      bodyColor: '#2d1810', // 深色内容
      borderColor: '#a0826d', // 羊皮纸边框色
      borderWidth: 2
    }
  }
}

// Helper Functions
const formatNumber = (num: number, decimals: number = 2) => {
  if (num === undefined || num === null) return '0'
  return num.toLocaleString('en-US', { 
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals 
  })
}

const getApiParams = () => {
  if (selectedRange.value.type === 'days') {
    return { days: selectedRange.value.value }
  } else {
    return {
      start_date: `${customDate.start}T00:00:00`,
      end_date: `${customDate.end}T23:59:59`
    }
  }
}

// Data Fetching
const fetchOverallStats = async () => {
  try {
    const res = await axios.get('/api/logs/model_usage/statistics') // 获取所有历史统计数据
    if (res.data.success) {
      overallStats.value = res.data.data
    }
  } catch (error) {
    console.error('Failed to fetch overall stats:', error)
  }
}

const fetchProviderStats = async () => {
  try {
    const res = await axios.get('/api/logs/model_usage/statistics/providers', { params: getApiParams() })
    if (res.data.success) {
      const data = res.data.data
      const labels = Object.keys(data)
      const values = Object.values(data).map((item: any) => item.cost)
      
      charts.provider.data = {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colorSchemes[selectedColorScheme.value].colors,
          borderWidth: 0
        }]
      }
    }
  } catch (error) {
    console.error('Failed to fetch provider stats:', error)
  }
}

const fetchModelStats = async () => {
  try {
    const res = await axios.get('/api/logs/model_usage/statistics/models', { params: getApiParams() })
    if (res.data.success) {
      const data = res.data.data
      // Sort by cost desc and take top 10
      const sortedItems = Object.entries(data)
        .sort(([, a]: any, [, b]: any) => b.cost - a.cost)
        .slice(0, 10)
      
      const labels = sortedItems.map(([key]) => key.split('/')[1] || key)
      const values = sortedItems.map(([, item]: any) => item.cost)

      // 扩展配色方案以支持更多项
      const colors = [...colorSchemes[selectedColorScheme.value].colors]
      while (colors.length < values.length) {
        colors.push(...colorSchemes[selectedColorScheme.value].colors)
      }

      charts.model.data = {
        labels,
        datasets: [{
          data: values,
          backgroundColor: colors.slice(0, values.length),
          borderWidth: 0
        }]
      }
    }
  } catch (error) {
    console.error('Failed to fetch model stats:', error)
  }
}

const fetchDailyStats = async () => {
  try {
    const res = await axios.get('/api/logs/model_usage/statistics/daily', { params: getApiParams() })
    if (res.data.success) {
      const data = res.data.data
      const dates = Object.keys(data).sort()
      
      const inputTokens = dates.map(date => {
        const dayData = Object.values(data[date])
        return dayData.reduce((sum: number, item: any) => sum + item.input_tokens, 0)
      })
      
      const outputTokens = dates.map(date => {
        const dayData = Object.values(data[date])
        return dayData.reduce((sum: number, item: any) => sum + item.output_tokens, 0)
      })

      // Calculate total input/output for pie chart
      const totalInput = inputTokens.reduce((a, b) => a + b, 0)
      const totalOutput = outputTokens.reduce((a, b) => a + b, 0)
      
      charts.token.data = {
        labels: ['输入令牌', '输出令牌'],
        datasets: [{
          data: [totalInput, totalOutput],
          backgroundColor: [colorSchemes[selectedColorScheme.value].colors[0], colorSchemes[selectedColorScheme.value].colors[1]],
          borderWidth: 0
        }]
      }

      charts.daily.data = {
        labels: dates,
        datasets: [
          {
            label: '输入令牌',
            data: inputTokens,
            backgroundColor: colorSchemes[selectedColorScheme.value].colors[0],
            stack: 'Stack 0'
          },
          {
            label: '输出令牌',
            data: outputTokens,
            backgroundColor: colorSchemes[selectedColorScheme.value].colors[1],
            stack: 'Stack 0'
          }
        ]
      }
    }
  } catch (error) {
    console.error('Failed to fetch daily stats:', error)
  }
}

const refreshCharts = async () => {
  lastUpdated.value = new Date().toLocaleString()
  await Promise.all([
    fetchProviderStats(),
    fetchModelStats(),
    fetchDailyStats()
  ])
}

const updateCharts = () => {
  // 当配色方案改变时，重新获取并更新图表
  refreshCharts()
}

const setDaysRange = (days: number) => {
  selectedRange.value = { type: 'days', value: days }
  
  // 计算起止日期并填充到日期选择器
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - days + 1) // 包含今天
  
  customDate.start = start.toISOString().split('T')[0]
  customDate.end = end.toISOString().split('T')[0]
  
  refreshCharts()
}

const applyCustomDate = () => {
  if (customDate.start && customDate.end) {
    selectedRange.value = { type: 'custom', value: 0 }
    refreshCharts()
  }
}

onMounted(() => {
  fetchOverallStats()
  refreshCharts()
})
</script>

<style scoped>
/* 羊皮纸风格图表容器 */
.parchment-chart-container {
  background: linear-gradient(
    to bottom,
    #f4e8d0 0%,
    #f9f0dd 20%,
    #f4e8d0 40%,
    #efe3c8 60%,
    #f4e8d0 80%,
    #f9f0dd 100%
  );
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #a0826d;
  box-shadow: 
    0 2px 8px rgba(101, 67, 33, 0.15),
    inset 0 0 60px rgba(194, 154, 108, 0.1);
  position: relative;
}

/* 羊皮纸大容器（用于柱状图） */
.parchment-chart-container-large {
  background: linear-gradient(
    to bottom,
    #f4e8d0 0%,
    #f9f0dd 20%,
    #f4e8d0 40%,
    #efe3c8 60%,
    #f4e8d0 80%,
    #f9f0dd 100%
  );
  padding: 1.5rem;
  border-radius: 8px;
  border: 2px solid #a0826d;
  box-shadow: 
    0 2px 8px rgba(101, 67, 33, 0.15),
    inset 0 0 80px rgba(194, 154, 108, 0.1);
  position: relative;
}

/* 羊皮纸纹理效果 */
.parchment-chart-container::before,
.parchment-chart-container-large::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-image: 
    repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(139, 101, 61, 0.03) 2px,
      rgba(139, 101, 61, 0.03) 4px
    ),
    repeating-linear-gradient(
      90deg,
      transparent,
      transparent 2px,
      rgba(139, 101, 61, 0.03) 2px,
      rgba(139, 101, 61, 0.03) 4px
    );
  pointer-events: none;
  border-radius: 8px;
}

/* 图表标题样式 */
.chart-title {
  position: relative;
  z-index: 1;
  font-size: 0.875rem;
  font-weight: 600;
  color: #3d2817;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid rgba(101, 67, 33, 0.2);
  text-shadow: 1px 1px 2px rgba(255, 255, 255, 0.5);
}

/* 日期选择器日历弹出框样式优化 */
input[type="date"]::-webkit-calendar-picker-indicator {
  cursor: pointer;
  filter: invert(1);
  opacity: 0.8;
}

input[type="date"]::-webkit-calendar-picker-indicator:hover {
  opacity: 1;
}

/* 针对 date input 的悬停效果 */
input[type="date"]:hover {
  border-color: #3b82f6 !important;
}
</style>
