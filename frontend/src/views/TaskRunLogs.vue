<template>
  <div class="flex h-full gap-6">
    <!-- Left Sidebar: Search Filters -->
    <aside class="w-96 flex-shrink-0">
      <h1 class="text-2xl font-bold text-white mb-6">运行日志</h1>
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6 sticky top-0">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-lg font-bold text-white">搜索筛选</h2>
          <button
            @click="showAdvanced = !showAdvanced"
            class="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            {{ showAdvanced ? '收起' : '高级搜索' }}
          </button>
        </div>
        
        <div class="space-y-6">
          <!-- Date Range Filter -->
          <DateRangePicker
            label="📅 时间范围"
            :quick-days="[1, 3, 7, 30]"
            v-model:modelStartDate="filters.startDate"
            v-model:modelEndDate="filters.endDate"
            v-model:modelDays="filters.days"
            @change="onDateChange"
          />

          <!-- Keyword Search -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">🔍 关键字搜索</label>
            <input
              type="text"
              v-model="filters.keyword"
              @input="debounceSearch"
              placeholder="搜索日志内容..."
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors placeholder-gray-500"
            />
          </div>

          <!-- Advanced Search Options -->
          <div v-show="showAdvanced" class="space-y-6 border-t border-gray-700 pt-6">
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

          <!-- Action Buttons -->
          <div class="flex flex-col space-y-3 pt-4 border-t border-gray-700">
            <button
              @click="loadLogs"
              class="w-full px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors font-medium"
            >
              搜索
            </button>
            <button
              @click="resetFilters"
              class="w-full px-5 py-2.5 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors font-medium"
            >
              重置
            </button>
          </div>
        </div>
      </div>
    </aside>

    <!-- Right Content Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <div class="flex justify-end items-center mb-6">
        <div class="flex items-center gap-3">
          <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-600/20 text-blue-400 border border-blue-600/30">
            <span class="mr-1.5">📊</span>
            总数: {{ response?.total || 0 }}
          </span>
          <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-green-600/20 text-green-400 border border-green-600/30">
            <span class="mr-1.5">🔍</span>
            筛选: {{ response?.filtered_total || 0 }}
          </span>
          <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-purple-600/20 text-purple-400 border border-purple-600/30">
            <span class="mr-1.5">📄</span>
            本页: {{ displayedLogs.length }}
          </span>
          <div class="text-sm text-gray-400 ml-2" v-if="stats">
            共 {{ stats.total_files }} 个日志文件
          </div>
        </div>
      </div>

      <!-- Logs Content Area with Scroll -->
      <div class="flex-1 flex flex-col min-h-0 relative">
        <div class="flex-1 overflow-y-auto">
          <!-- Loading State -->
          <div v-if="loading" class="flex items-center justify-center py-12">
            <div class="text-gray-400">加载中...</div>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-400">
            {{ error }}
          </div>

          <!-- Logs List -->
          <div v-else-if="displayedLogs.length > 0" class="space-y-4 pb-20">
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
          </div>

          <!-- Empty State -->
          <div v-else class="bg-[#1e293b] rounded-lg border border-gray-700 p-12 text-center">
            <div class="text-gray-400 text-lg">未找到符合条件的日志</div>
          </div>
        </div>

        <!-- Floating Pagination -->
        <div 
          v-if="totalPages > 1" 
          class="absolute bottom-1 left-1/2 -translate-x-1/2 bg-[#334155]/95 backdrop-blur-sm border border-gray-600 rounded-lg p-3 flex items-center space-x-2 shadow-xl z-20 flex-nowrap"
        >
          <button
            @click="currentPage = 1"
            :disabled="currentPage === 1"
            class="px-4 py-1.5 whitespace-nowrap bg-[#475569] hover:bg-[#64748b] text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-500"
            title="首页"
          >
            首页
          </button>
          <button
            @click="currentPage = Math.max(1, currentPage - 1)"
            :disabled="currentPage === 1"
            class="px-4 py-1.5 whitespace-nowrap bg-[#475569] hover:bg-[#64748b] text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-500"
            title="上一页"
          >
            上一页
          </button>
          <div class="flex items-center space-x-2 px-2 whitespace-nowrap flex-shrink-0">
            <span class="text-gray-300 text-sm whitespace-nowrap">第</span>
            <input
              type="number"
              v-model.number="jumpPage"
              @keyup.enter="jumpToPage"
              @blur="jumpToPage"
              :min="1"
              :max="totalPages"
              class="w-16 px-2 py-1 bg-[#475569] text-white text-sm rounded border border-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-center flex-shrink-0"
            />
            <span class="text-gray-300 text-sm whitespace-nowrap">/ {{ totalPages }} 页</span>
          </div>
          <button
            @click="currentPage = Math.min(totalPages, currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="px-4 py-1.5 whitespace-nowrap bg-[#475569] hover:bg-[#64748b] text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-500"
            title="下一页"
          >
            下一页
          </button>
          <button
            @click="currentPage = totalPages"
            :disabled="currentPage === totalPages"
            class="px-4 py-1.5 whitespace-nowrap bg-[#475569] hover:bg-[#64748b] text-white text-sm rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed border border-gray-500"
            title="尾页"
          >
            尾页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
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
const showAdvanced = ref(false)
const jumpPage = ref(1)

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

// Watch currentPage to update jumpPage and scroll to top
watch(currentPage, (newPage) => {
  jumpPage.value = newPage
  const scrollContainer = document.querySelector('.overflow-y-auto')
  if (scrollContainer) {
    scrollContainer.scrollTop = 0
  }
})

// Methods
const formatDate = (date: Date): string => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const selectDays = (days: number) => {
  filters.value.days = days
  // 计算日期范围：结束日期为今天，开始日期为days天前
  const endDate = new Date()
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days + 1) // +1 表示包含今天
  
  filters.value.endDate = formatDate(endDate)
  filters.value.startDate = formatDate(startDate)
  loadLogs()
}

const onDateChange = (payload?: { startDate: string; endDate: string; days: number | null }) => {
  // 如果是从 DateRangePicker 传来的 change 事件，使用事件参数
  if (payload) {
    // 如果选择了"近X天"，保持 days 值，日期已经通过 v-model 更新
    if (payload.days !== null) {
      filters.value.days = payload.days
      filters.value.startDate = payload.startDate
      filters.value.endDate = payload.endDate
      currentPage.value = 1
      loadLogs()
      return
    }
    // 如果手动选择日期，清除"近X天"的选择
    filters.value.days = null
    filters.value.startDate = payload.startDate
    filters.value.endDate = payload.endDate
  } else {
    // 兼容旧代码：当手动选择日期时，清除"近X天"的选择
    if (filters.value.startDate || filters.value.endDate) {
      filters.value.days = null
    }
  }
  
  // 如果只选择了开始日期，自动设置结束日期为今天
  if (filters.value.startDate && !filters.value.endDate) {
    filters.value.endDate = formatDate(new Date())
  }
  // 如果只选择了结束日期，自动设置开始日期为结束日期
  if (filters.value.endDate && !filters.value.startDate) {
    filters.value.startDate = filters.value.endDate
  }
  // 如果两个日期都已设置，自动触发搜索
  if (filters.value.startDate && filters.value.endDate) {
    currentPage.value = 1
    loadLogs()
  }
}

const resetFilters = () => {
  filters.value = {
    days: 7,
    startDate: '',
    endDate: '',
    keyword: '',
    level: '',
    logger: ''
  }
  // 重置时自动设置近7天的日期范围
  selectDays(7)
  currentPage.value = 1
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

const jumpToPage = () => {
  const page = Math.max(1, Math.min(totalPages.value, Math.floor(jumpPage.value) || 1))
  currentPage.value = page
  jumpPage.value = page
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
  // 初始化时，如果选择了"近X天"，自动设置日期范围
  if (filters.value.days) {
    selectDays(filters.value.days)
  }
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

