<template>
  <div class="flex h-full gap-6">
    <!-- 扩展模态框 -->
    <CacheDetailsModalDlgEx
      v-model="showModalEx"
      :cache-info="modalCacheInfo"
      :cache-data="modalCacheData"
    />
    
    <!-- Left Sidebar: Search Filters -->
    <aside class="w-72 flex-shrink-0">
      <h1 class="text-2xl font-bold text-white mb-6">任务监测</h1>
      <div class="bg-[#1e293b] rounded-lg border border-gray-700 p-6 sticky top-0">
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-lg font-bold text-white">筛选条件</h2>
          <button
            @click="resetFilters"
            class="text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            重置
          </button>
        </div>
        
        <div class="space-y-6">
          <!-- Task ID -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">🔍 Task ID</label>
            <input
              v-model="filters.task_id"
              type="text"
              placeholder="输入Task ID（支持部分匹配）"
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors placeholder-gray-500"
              @keyup.enter="applyFilters"
            />
          </div>

          <!-- 分析日期 -->
          <DateRangePicker
            label="📅 分析日期"
            :quick-days="[]"
            single-mode="start"
            v-model:modelStartDate="filters.analysis_date"
            v-model:modelEndDate="analysisDateEnd"
            v-model:modelDays="analysisDateDays"
            @change="onAnalysisDateChange"
          />

          <!-- 运行状态 -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">📊 运行状态</label>
            <select
              v-model="filters.status"
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors cursor-pointer"
            >
              <option value="" class="bg-[#0f172a] text-white">全部</option>
              <option value="completed" class="bg-[#0f172a] text-white">已完成</option>
              <option value="running" class="bg-[#0f172a] text-white">运行中</option>
              <option value="pending" class="bg-[#0f172a] text-white">等待中</option>
              <option value="failed" class="bg-[#0f172a] text-white">失败</option>
              <option value="paused" class="bg-[#0f172a] text-white">已暂停</option>
              <option value="stopped" class="bg-[#0f172a] text-white">已停止</option>
            </select>
          </div>

          <!-- 股票代码 -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">📈 股票代码</label>
            <input
              v-model="filters.stock_symbol"
              type="text"
              placeholder="输入股票代码（支持部分匹配）"
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors placeholder-gray-500"
              @keyup.enter="applyFilters"
            />
          </div>

          <!-- 公司名称 -->
          <div class="space-y-3">
            <label class="text-sm font-medium text-gray-300 block">🏢 公司名称</label>
            <input
              v-model="filters.company_name"
              type="text"
              placeholder="输入公司名称（支持部分匹配）"
              class="w-full bg-[#0f172a] text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-3 py-2.5 border border-gray-600 hover:border-blue-500 transition-colors placeholder-gray-500"
              @keyup.enter="applyFilters"
            />
          </div>

          <!-- Action Buttons -->
          <div class="flex flex-col space-y-3 pt-4 border-t border-gray-700">
            <button
              @click="applyFilters"
              class="w-full px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors font-medium"
              :disabled="loading"
            >
              {{ loading ? '加载中...' : '搜索' }}
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
            总数: {{ totalCount }}
          </span>
          <button
            @click="loadTaskList"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors font-medium"
            :disabled="loading"
          >
            {{ loading ? '加载中...' : '刷新' }}
          </button>
        </div>
      </div>

      <!-- Content Area with Scroll -->
      <div class="flex-1 flex flex-col min-h-0 relative">
        <div class="flex-1 overflow-y-auto">
          <!-- Loading State -->
          <div v-if="loading && taskList.length === 0" class="flex items-center justify-center py-12">
            <div class="text-gray-400">加载中...</div>
          </div>

          <!-- Error State -->
          <div v-else-if="error" class="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-400 mb-6">
            {{ error }}
          </div>

          <!-- Task List -->
          <div v-else-if="taskList.length > 0" class="pb-20">
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="item in taskList"
          :key="item.task_id"
          class="bg-[#1e293b] rounded-lg border border-gray-700 overflow-hidden transition-all hover:border-gray-600 flex flex-col"
          :class="expandedItems.has(item.task_id) ? 'h-[600px]' : ''"
        >
        <!-- Collapsed View -->
        <div
          v-if="!expandedItems.has(item.task_id)"
          class="p-4"
        >
          <!-- 第一行：一列 - 公司名称（股票代码）+ 状态/分析日期 -->
          <div class="mb-3">
            <div class="flex items-center justify-between">
              <div class="text-base font-semibold text-white">
                {{ item.company_name || 'N/A' }}<span v-if="item.stock_symbol" class="text-gray-400 font-normal">（{{ item.stock_symbol }}）</span>
              </div>
              <div class="flex items-center gap-2">
                <span
                  class="px-2 py-1 text-xs font-semibold rounded"
                  :class="getStatusClass(item.status)"
                >
                  {{ getStatusText(item.status) }}
                </span>
                <span class="text-sm text-gray-400">
                  分析日期: <span class="text-white">{{ item.analysis_date || 'N/A' }}</span>
                </span>
              </div>
            </div>
          </div>
          
          <!-- 第二行：两列 - 创建时间、更新时间（占据整个宽度） -->
          <div class="grid grid-cols-2 gap-4 mb-3 text-sm">
            <div>
              <span class="text-gray-400">创建:</span>
              <span class="text-white ml-2">{{ formatDate(item.created_at) }}</span>
            </div>
            <div>
              <span class="text-gray-400">更新:</span>
              <span class="text-white ml-2">{{ formatDate(item.updated_at) }}</span>
            </div>
          </div>
          
          <!-- 第三行：一列 - Task ID + 按钮 -->
          <div class="flex items-center justify-between pt-2 border-t border-gray-700">
            <div>
              <span class="text-xs text-gray-400">Task ID: </span>
              <span class="text-xs text-gray-300 font-mono">{{ item.task_id }}</span>
            </div>
            <div class="flex items-center gap-2">
              <button
                @click.stop="openModalExDirectly(item)"
                class="text-gray-400 hover:text-blue-400 transition-colors p-1"
                title="放大查看任务详情"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
              <button
                @click.stop="toggleExpand(item.task_id)"
                class="text-gray-400 hover:text-white transition-colors p-1"
                title="展开/收缩"
              >
                <svg
                  class="w-5 h-5 transition-transform"
                  :class="{ 'rotate-180': expandedItems.has(item.task_id) }"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Expanded View -->
        <div v-else class="p-4 flex flex-col flex-1 min-h-0">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-white">
              任务详情：{{ item.company_name || 'N/A' }}（{{ item.stock_symbol || 'N/A' }}）
            </h3>
            <div class="flex items-center gap-2">
              <button
                v-if="taskDetails[item.task_id]"
                @click="openModalEx(item, taskDetails[item.task_id])"
                class="text-gray-400 hover:text-blue-400 transition-colors p-1"
                title="放大查看任务详情"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
              <button
                @click="toggleExpand(item.task_id)"
                class="text-gray-400 hover:text-white transition-colors p-1"
                title="展开/收缩"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Tabs -->
          <div class="mb-4 border-b border-gray-700">
            <div class="flex space-x-4">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                @click="activeTabs[item.task_id] = tab.key"
                class="px-4 py-2 text-sm font-medium transition-colors"
                :class="activeTabs[item.task_id] === tab.key
                  ? 'text-blue-400 border-b-2 border-blue-400'
                  : 'text-gray-400 hover:text-gray-300'"
              >
                {{ tab.label }}
              </button>
            </div>
          </div>

          <!-- Tab Content -->
          <div v-if="loadingDetails[item.task_id]" class="text-gray-400 py-4 flex-1 flex items-center justify-center">
            加载中...
          </div>
          <div v-else-if="detailErrors[item.task_id]" class="text-red-400 py-4 flex-1 flex items-center justify-center">
            {{ detailErrors[item.task_id] }}
          </div>
          <div v-else-if="taskDetails[item.task_id]" class="flex-1 flex flex-col min-h-0">
            <!-- Current Step Tab -->
            <div v-show="activeTabs[item.task_id] === 'current_step'" class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-hidden min-h-0">
                <JsonViewer :data="taskDetails[item.task_id]?.current_step" :max-height="'100%'" :show-search="false" />
              </div>
            </div>
            <!-- History Tab -->
            <div v-show="activeTabs[item.task_id] === 'history'" class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-hidden min-h-0">
                <JsonViewer :data="taskDetails[item.task_id]?.history" :max-height="'100%'" :show-search="false" />
              </div>
            </div>
            <!-- Props Tab -->
            <div v-show="activeTabs[item.task_id] === 'props'" class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-hidden min-h-0">
                <JsonViewer :data="taskDetails[item.task_id]?.props" :max-height="'100%'" :show-search="false" />
              </div>
            </div>
          </div>
          <div v-else class="text-gray-400 py-4 flex-1 flex items-center justify-center">
            暂无数据
          </div>
        </div>
        </div>
      </div>
    </div>

          <!-- Empty State -->
          <div v-else class="bg-[#1e293b] rounded-lg border border-gray-700 p-12 text-center">
            <div class="text-gray-400 text-lg">暂无任务记录</div>
          </div>
        </div>

        <!-- Floating Pagination -->
        <div v-if="totalPages > 1" class="sticky bottom-0 bg-[#0f172a] border-t border-gray-700 px-6 py-4 flex items-center justify-center gap-4">
          <button
            @click="currentPage = Math.max(1, currentPage - 1); loadTaskList()"
            :disabled="currentPage === 1"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            上一页
          </button>
          <span class="text-gray-400 text-sm">
            第 {{ currentPage }} / {{ totalPages }} 页
          </span>
          <button
            @click="currentPage = Math.min(totalPages, currentPage + 1); loadTaskList()"
            :disabled="currentPage === totalPages"
            class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            下一页
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getTaskList, getTaskDetail, type TaskListItem, type TaskDetailData } from '../api'
import JsonViewer from '../components/JsonViewer.vue'
import CacheDetailsModalDlgEx from '../components/CacheDetailsModalDlgEx.vue'
import DateRangePicker from '../components/DateRangePicker.vue'

const loading = ref(false)
const error = ref('')
const taskList = ref<TaskListItem[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = ref(0)

// 筛选条件
const filters = ref({
  task_id: '',
  analysis_date: '',
  status: '',
  stock_symbol: '',
  company_name: ''
})

// DateRangePicker 需要的额外状态（用于单日期模式）
const analysisDateEnd = ref('')
const analysisDateDays = ref<number | null>(null)

// 分析日期变化处理
const onAnalysisDateChange = () => {
  applyFilters()
}

const expandedItems = ref<Set<string>>(new Set())
const activeTabs = reactive<Record<string, string>>({})
const taskDetails = reactive<Record<string, TaskDetailData>>({})
const loadingDetails = reactive<Record<string, boolean>>({})
const detailErrors = reactive<Record<string, string>>({})

// 扩展模态框相关
const showModalEx = ref(false)
const modalCacheInfo = ref<TaskListItem>({
  task_id: '',
  status: '',
  created_at: undefined,
  updated_at: undefined,
  analysis_date: undefined,
  stock_symbol: undefined,
  company_name: undefined
})
const modalCacheData = ref<TaskDetailData>({})

const tabs = [
  { key: 'current_step', label: 'Current Step' },
  { key: 'history', label: 'History' },
  { key: 'props', label: 'Props' }
]

const getStatusClass = (status: string) => {
  const statusMap: Record<string, string> = {
    'completed': 'bg-green-600/20 text-green-400 border border-green-600/30',
    'running': 'bg-blue-600/20 text-blue-400 border border-blue-600/30',
    'pending': 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/30',
    'failed': 'bg-red-600/20 text-red-400 border border-red-600/30',
    'paused': 'bg-gray-600/20 text-gray-400 border border-gray-600/30',
    'stopped': 'bg-red-600/20 text-red-400 border border-red-600/30'
  }
  return statusMap[status] || 'bg-gray-600/20 text-gray-400 border border-gray-600/30'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'completed': '已完成',
    'running': '运行中',
    'pending': '等待中',
    'failed': '失败',
    'paused': '已暂停',
    'stopped': '已停止'
  }
  return statusMap[status] || status
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

const openModalEx = (item: TaskListItem, detailData: TaskDetailData) => {
  modalCacheInfo.value = { ...item }
  modalCacheData.value = { 
    current_step: detailData?.current_step ?? null,
    history: detailData?.history ?? null,
    props: detailData?.props ?? null
  }
  showModalEx.value = true
}

const openModalExDirectly = async (item: TaskListItem) => {
  // 如果数据还没加载，先加载
  if (!taskDetails[item.task_id]) {
    await loadTaskDetail(item.task_id)
  }
  // 打开扩展模态框
  if (taskDetails[item.task_id]) {
    openModalEx(item, taskDetails[item.task_id])
  }
}

const toggleExpand = async (taskId: string) => {
  if (expandedItems.value.has(taskId)) {
    expandedItems.value.delete(taskId)
  } else {
    expandedItems.value.add(taskId)
    // 初始化tab
    if (!activeTabs[taskId]) {
      activeTabs[taskId] = 'current_step'
    }
    // 加载详细信息
    if (!taskDetails[taskId]) {
      await loadTaskDetail(taskId)
    }
  }
}

const loadTaskDetail = async (taskId: string) => {
  loadingDetails[taskId] = true
  delete detailErrors[taskId]
  
  try {
    const response = await getTaskDetail(taskId)
    if (response.success) {
      // 确保数据结构正确
      taskDetails[taskId] = {
        current_step: response.data.current_step ?? null,
        history: response.data.history ?? null,
        props: response.data.props ?? null
      }
      console.log('任务详情数据:', taskDetails[taskId])
    } else {
      detailErrors[taskId] = response.message || '加载失败'
    }
  } catch (e: any) {
    detailErrors[taskId] = e.message || '加载失败'
    console.error('加载任务详情失败:', e)
  } finally {
    loadingDetails[taskId] = false
  }
}

const loadTaskList = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // 构建筛选参数对象（只包含非空值）
    const filterParams: any = {}
    if (filters.value.task_id) filterParams.task_id = filters.value.task_id
    if (filters.value.analysis_date) filterParams.analysis_date = filters.value.analysis_date
    if (filters.value.status) filterParams.status = filters.value.status
    if (filters.value.stock_symbol) filterParams.stock_symbol = filters.value.stock_symbol
    if (filters.value.company_name) filterParams.company_name = filters.value.company_name
    
    // 加载列表（带筛选）
    const listResponse = await getTaskList(
      currentPage.value,
      pageSize.value,
      Object.keys(filterParams).length > 0 ? filterParams : undefined
    )
    if (listResponse.success) {
      taskList.value = listResponse.data
      totalPages.value = listResponse.pages
      totalCount.value = listResponse.total  // 使用筛选后的总数
    } else {
      error.value = listResponse.message || '加载失败'
    }
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  // 重置到第一页
  currentPage.value = 1
  // 加载数据
  loadTaskList()
}

const resetFilters = () => {
  filters.value = {
    task_id: '',
    analysis_date: '',
    status: '',
    stock_symbol: '',
    company_name: ''
  }
  analysisDateEnd.value = ''
  analysisDateDays.value = null
  currentPage.value = 1
  loadTaskList()
}

onMounted(() => {
  loadTaskList()
})
</script>

<style scoped>
/* 自定义滚动条样式 */
.overflow-y-auto::-webkit-scrollbar {
  width: 8px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #1e293b;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 4px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}

</style>

