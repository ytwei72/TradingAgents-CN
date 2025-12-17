<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-white">运行日志-老</h1>
      <div class="text-sm text-gray-400" v-if="stats">
        共 {{ stats.total_files }} 个日志文件
      </div>
    </div>

    <!-- Filter Section -->
    <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6">
      <div class="space-y-6">
        <!-- First Row: Date Range and Quick Filters -->
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <!-- Date Range Filter -->
          <div class="space-y-3 w-full lg:col-span-3">
            <DateRangePicker
              label="📅 时间范围"
              :quick-days="[1, 3, 7, 30]"
              v-model:modelStartDate="filters.startDate"
              v-model:modelEndDate="filters.endDate"
              v-model:modelDays="filters.days"
              @change="loadLogs"
            />
          </div>

          <!-- Keyword Search -->
          <div class="space-y-3 lg:col-span-2">
            <label class="text-sm font-medium text-gray-300 block">🔍 关键字搜索</label>
            <input
              type="text"
              v-model="filters.keyword"
              @input="debounceSearch"
              placeholder="搜索日志内容..."
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors placeholder-gray-500"
            />
          </div>
        </div>

        <!-- Second Row: Level and Logger Filters -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <!-- Level Filter -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">📊 日志级别</label>
            <select
              v-model="filters.level"
              @change="loadLogs"
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors cursor-pointer"
            >
              <option value="" class="bg-[#0f172a] text-white">全部</option>
              <option value="INFO" class="bg-[#0f172a] text-white">INFO</option>
              <option value="WARNING" class="bg-[#0f172a] text-white">WARNING</option>
              <option value="ERROR" class="bg-[#0f172a] text-white">ERROR</option>
            </select>
          </div>

          <!-- Logger Filter -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">📝 Logger</label>
            <input
              type="text"
              v-model="filters.logger"
              @input="debounceSearch"
              placeholder="过滤Logger..."
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors placeholder-gray-500"
            />
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex justify-end space-x-3 mt-6 pt-4 border-t border-gray-700">
        <button
          @click="resetFilters"
          class="px-5 py-2.5 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors font-medium"
        >
          重置
        </button>
        <button
          @click="loadLogs"
          class="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors font-medium"
        >
          搜索
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">📊 总日志数</div>
        <div class="text-2xl font-bold text-white">{{ response?.total || 0 }}</div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">🔍 筛选结果</div>
        <div class="text-2xl font-bold text-white">{{ response?.filtered_total || 0 }}</div>
      </div>
      <div class="bg-[#1e293b] p-4 rounded-lg border border-gray-700">
        <div class="text-gray-400 text-sm mb-1">📄 当前显示</div>
        <div class="text-2xl font-bold text-white">{{ displayedLogs.length }}</div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-12">
      <div class="text-gray-400">加载中...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-400">
      {{ error }}
    </div>

    <!-- Logs List -->
    <div v-else-if="displayedLogs.length > 0" class="space-y-4">
      <div
        v-for="(log, index) in displayedLogs"
        :key="index"
        class="bg-[#1e293b] rounded-lg border border-gray-700 overflow-hidden transition-all hover:border-gray-600"
      >
        <!-- Collapsed View -->
        <div
          v-if="!expandedLogs.has(index)"
          @click="toggleExpand(index)"
          class="p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center space-x-3 mb-2">
                <span
                  class="px-2 py-1 text-xs font-semibold rounded"
                  :class="getLevelClass(log.level)"
                >
                  {{ getLevelText(log.level) }}
                </span>
                <span class="text-sm text-gray-400">{{ formatTimestamp(log.timestamp) }}</span>
                <span v-if="log.logger" class="text-sm text-gray-500">@{{ log.logger }}</span>
              </div>
              <div class="text-white text-sm line-clamp-2">
                {{ log.message }}
              </div>
              <div v-if="log.module || log.function" class="flex items-center space-x-2 mt-2 text-xs text-gray-500">
                <span v-if="log.module">{{ log.module }}</span>
                <span v-if="log.function">{{ log.function }}</span>
                <span v-if="log.line">:{{ log.line }}</span>
              </div>
            </div>
            <svg
              class="w-5 h-5 text-gray-400 ml-4 flex-shrink-0"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
            </svg>
          </div>
        </div>

        <!-- Expanded View -->
        <div
          v-else
          class="p-4"
        >
          <div class="flex items-start justify-between mb-4">
            <div class="flex-1">
              <div class="flex items-center space-x-3 mb-3">
                <span
                  class="px-2 py-1 text-xs font-semibold rounded"
                  :class="getLevelClass(log.level)"
                >
                  {{ getLevelText(log.level) }}
                </span>
                <span class="text-sm text-gray-400">{{ formatTimestamp(log.timestamp) }}</span>
                <span v-if="log.logger" class="text-sm text-gray-500">@{{ log.logger }}</span>
              </div>
              <div class="text-white text-sm whitespace-pre-wrap mb-3">
                {{ log.message }}
              </div>
            </div>
            <button
              @click.stop="toggleExpand(index)"
              class="ml-4 text-gray-400 hover:text-white transition-colors"
            >
              <svg
                class="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7"></path>
              </svg>
            </button>
          </div>

          <!-- Detailed Information -->
          <div class="bg-[#0f172a] rounded-lg p-4 border border-gray-700">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <div class="text-gray-400 mb-1">时间戳</div>
                <div class="text-white font-mono">{{ log.timestamp }}</div>
              </div>
              <div v-if="log.level">
                <div class="text-gray-400 mb-1">级别</div>
                <div class="text-white">{{ log.level }}</div>
              </div>
              <div v-if="log.logger">
                <div class="text-gray-400 mb-1">Logger</div>
                <div class="text-white font-mono">{{ log.logger }}</div>
              </div>
              <div v-if="log.module">
                <div class="text-gray-400 mb-1">模块</div>
                <div class="text-white font-mono">{{ log.module }}</div>
              </div>
              <div v-if="log.function">
                <div class="text-gray-400 mb-1">函数</div>
                <div class="text-white font-mono">{{ log.function }}</div>
              </div>
              <div v-if="log.line">
                <div class="text-gray-400 mb-1">行号</div>
                <div class="text-white font-mono">{{ log.line }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-center space-x-2 pt-4">
        <button
          @click="currentPage = Math.max(1, currentPage - 1)"
          :disabled="currentPage === 1"
          class="px-4 py-2 bg-[#1e293b] hover:bg-gray-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700"
        >
          上一页
        </button>
        <span class="text-gray-400 text-sm">
          第 {{ currentPage }} / {{ totalPages }} 页
        </span>
        <button
          @click="currentPage = Math.min(totalPages, currentPage + 1)"
          :disabled="currentPage === totalPages"
          class="px-4 py-2 bg-[#1e293b] hover:bg-gray-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="bg-[#1e293b] rounded-lg border border-gray-700 p-12 text-center">
      <div class="text-gray-400 text-lg">未找到符合条件的日志</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import DateRangePicker from '../components/DateRangePicker.vue'
import { getOperationLogs, getLogsStats, type LogsResponse, type LogsStatsResponse } from '../api'

// State
const loading = ref(false)
const error = ref<string | null>(null)
const response = ref<LogsResponse | null>(null)
const stats = ref<LogsStatsResponse['data'] | null>(null)
const expandedLogs = ref(new Set<number>())
const currentPage = ref(1)
const pageSize = ref(50)

const filters = ref({
  days: 7 as number | null,
  startDate: '' as string,
  endDate: '' as string,
  keyword: '' as string,
  level: '' as string,
  logger: '' as string
})

// Computed
const displayedLogs = computed(() => {
  if (!response.value) return []
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return response.value.data.slice(start, end)
})

const totalPages = computed(() => {
  if (!response.value) return 0
  return Math.ceil(response.value.filtered_total / pageSize.value)
})

// Methods

const resetFilters = () => {
  filters.value = {
    days: 7,
    startDate: '',
    endDate: '',
    keyword: '',
    level: '',
    logger: ''
  }
  currentPage.value = 1
  loadLogs()
}

let searchTimeout: ReturnType<typeof setTimeout> | null = null
const debounceSearch = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
  searchTimeout = setTimeout(() => {
    currentPage.value = 1
    loadLogs()
  }, 500)
}

const loadLogs = async () => {
  loading.value = true
  error.value = null
  
  try {
    const result = await getOperationLogs(
      filters.value.startDate || undefined,
      filters.value.endDate || undefined,
      filters.value.days || undefined,
      filters.value.keyword || undefined,
      filters.value.level || undefined,
      filters.value.logger || undefined,
      5000 // limit
    )
    response.value = result
    currentPage.value = 1
    expandedLogs.value.clear()
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '加载日志失败'
    console.error('Load logs error:', err)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const result = await getLogsStats()
    stats.value = result.data
  } catch (err) {
    console.error('Load stats error:', err)
  }
}

const toggleExpand = (index: number) => {
  if (expandedLogs.value.has(index)) {
    expandedLogs.value.delete(index)
  } else {
    expandedLogs.value.add(index)
  }
}

const formatTimestamp = (timestamp: string) => {
  try {
    const date = new Date(timestamp)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timestamp
  }
}

const getLevelText = (level: string) => {
  const levelUpper = level.toUpperCase()
  if (levelUpper.includes('ERROR')) return 'ERROR'
  if (levelUpper.includes('WARNING')) return 'WARNING'
  if (levelUpper.includes('INFO')) return 'INFO'
  if (levelUpper.includes('DEBUG')) return 'DEBUG'
  return level
}

const getLevelClass = (level: string) => {
  const levelUpper = level.toUpperCase()
  if (levelUpper.includes('ERROR')) return 'bg-red-600/20 text-red-400 border border-red-600/30'
  if (levelUpper.includes('WARNING')) return 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/30'
  if (levelUpper.includes('INFO')) return 'bg-blue-600/20 text-blue-400 border border-blue-600/30'
  if (levelUpper.includes('DEBUG')) return 'bg-gray-600/20 text-gray-400 border border-gray-600/30'
  return 'bg-gray-600/20 text-gray-400 border border-gray-600/30'
}

// Lifecycle
onMounted(() => {
  loadStats()
  loadLogs()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 日期选择器样式优化 */
.date-input {
  color-scheme: dark;
  position: relative;
}

/* 隐藏原生日历图标，使用自定义图标 */
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

