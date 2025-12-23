<template>
  <div class="flex flex-col h-full">
    <!-- 基础模态框 -->
    <!-- <ModalDialog
      v-model="showModal"
      :title="modalTitle"
      :data="modalData"
    /> -->
    
    <!-- 扩展模态框 -->
    <ModalDialogEx
      v-model="showModalEx"
      :cache-info="modalCacheInfo"
      :cache-data="modalCacheData"
    />
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-white">缓存管理</h1>
      <div class="flex items-center gap-3">
        <span class="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-blue-600/20 text-blue-400 border border-blue-600/30">
          <span class="mr-1.5">📊</span>
          总数: {{ totalCount }}
        </span>
        <button
          @click="loadCacheList"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors font-medium"
          :disabled="loading"
        >
          {{ loading ? '加载中...' : '刷新' }}
        </button>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading && cacheList.length === 0" class="flex items-center justify-center py-12">
      <div class="text-gray-400">加载中...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-900/20 border border-red-700 rounded-lg p-4 text-red-400 mb-6">
      {{ error }}
    </div>

    <!-- Cache List -->
    <div v-else-if="cacheList.length > 0" class="flex-1 overflow-y-auto pb-20">
      <div class="grid grid-cols-2 gap-4">
        <div
          v-for="item in cacheList"
          :key="item.task_id"
          class="bg-[#1e293b] rounded-lg border border-gray-700 overflow-hidden transition-all hover:border-gray-600 flex flex-col"
          :class="expandedItems.has(item.task_id) ? 'h-[600px]' : ''"
        >
        <!-- Collapsed View -->
        <div
          v-if="!expandedItems.has(item.task_id)"
          @click="toggleExpand(item.task_id)"
          class="p-4 cursor-pointer hover:bg-gray-800/50 transition-colors"
        >
          <div class="flex items-start justify-between">
            <div class="flex-1">
              <div class="flex items-center space-x-3 mb-2">
                <span class="text-sm font-semibold text-white">Task ID:</span>
                <span class="text-sm text-gray-300 font-mono">{{ item.task_id }}</span>
                <span
                  class="px-2 py-1 text-xs font-semibold rounded"
                  :class="getStatusClass(item.status)"
                >
                  {{ item.status }}
                </span>
              </div>
              <div class="grid grid-cols-2 gap-4 mt-3 text-sm">
                <div>
                  <span class="text-gray-400">股票代码:</span>
                  <span class="text-white ml-2">{{ item.stock_symbol || 'N/A' }}</span>
                </div>
                <div>
                  <span class="text-gray-400">公司名称:</span>
                  <span class="text-white ml-2">{{ item.company_name || 'N/A' }}</span>
                </div>
                <div>
                  <span class="text-gray-400">分析日期:</span>
                  <span class="text-white ml-2">{{ item.analysis_date || 'N/A' }}</span>
                </div>
                <div>
                  <span class="text-gray-400">创建时间:</span>
                  <span class="text-white ml-2">{{ formatDate(item.created_at) }}</span>
                </div>
                <div>
                  <span class="text-gray-400">更新时间:</span>
                  <span class="text-white ml-2">{{ formatDate(item.updated_at) }}</span>
                </div>
              </div>
            </div>
            <div class="ml-4">
              <svg
                class="w-5 h-5 text-gray-400 transition-transform"
                :class="{ 'rotate-180': expandedItems.has(item.task_id) }"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>
        </div>

        <!-- Expanded View -->
        <div v-else class="p-4 flex flex-col flex-1 min-h-0">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-semibold text-white">缓存详情</h3>
            <button
              @click="toggleExpand(item.task_id)"
              class="text-gray-400 hover:text-white transition-colors"
            >
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
              </svg>
            </button>
          </div>

          <!-- Tabs -->
          <div class="mb-4 border-b border-gray-700">
            <div class="flex items-center justify-between">
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
              <button
                v-if="cacheDetails[item.task_id]"
                @click="openModalEx(item, cacheDetails[item.task_id])"
                class="px-3 py-1.5 text-xs bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors flex items-center gap-1.5"
                title="放大查看缓存详情"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                </svg>
                放大查看
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
          <div v-else-if="cacheDetails[item.task_id]" class="flex-1 flex flex-col min-h-0">
            <!-- Current Step Tab -->
            <div v-show="activeTabs[item.task_id] === 'current_step'" class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-hidden min-h-0">
                <JsonViewer :data="cacheDetails[item.task_id]?.current_step" :max-height="'100%'" />
              </div>
            </div>
            <!-- History Tab -->
            <div v-show="activeTabs[item.task_id] === 'history'" class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-hidden min-h-0">
                <JsonViewer :data="cacheDetails[item.task_id]?.history" :max-height="'100%'" />
              </div>
            </div>
            <!-- Props Tab -->
            <div v-show="activeTabs[item.task_id] === 'props'" class="flex-1 flex flex-col min-h-0">
              <div class="flex-1 overflow-hidden min-h-0">
                <JsonViewer :data="cacheDetails[item.task_id]?.props" :max-height="'100%'" />
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
    <div v-else class="flex items-center justify-center py-12">
      <div class="text-gray-400">暂无缓存记录</div>
    </div>

    <!-- Pagination -->
    <div v-if="totalPages > 1" class="flex items-center justify-center gap-4 mt-6 pt-6 border-t border-gray-700">
      <button
        @click="currentPage = Math.max(1, currentPage - 1); loadCacheList()"
        :disabled="currentPage === 1"
        class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        上一页
      </button>
      <span class="text-gray-400 text-sm">
        第 {{ currentPage }} / {{ totalPages }} 页
      </span>
      <button
        @click="currentPage = Math.min(totalPages, currentPage + 1); loadCacheList()"
        :disabled="currentPage === totalPages"
        class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getCacheCount, getCacheList, getCacheDetail, type CacheListItem, type CacheDetailData } from '../api'
import JsonViewer from '../components/JsonViewer.vue'
import ModalDialogEx from '../components/ModalDialogEx.vue'

const loading = ref(false)
const error = ref('')
const cacheList = ref<CacheListItem[]>([])
const totalCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = ref(0)

const expandedItems = ref<Set<string>>(new Set())
const activeTabs = reactive<Record<string, string>>({})
const cacheDetails = reactive<Record<string, CacheDetailData>>({})
const loadingDetails = reactive<Record<string, boolean>>({})
const detailErrors = reactive<Record<string, string>>({})

// 扩展模态框相关
const showModalEx = ref(false)
const modalCacheInfo = ref<CacheListItem>({
  task_id: '',
  status: '',
  created_at: undefined,
  updated_at: undefined,
  analysis_date: undefined,
  stock_symbol: undefined,
  company_name: undefined
})
const modalCacheData = ref<CacheDetailData>({})

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

const formatDate = (dateStr?: string) => {
  if (!dateStr) return 'N/A'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return dateStr
  }
}

const openModalEx = (item: CacheListItem, detailData: CacheDetailData) => {
  modalCacheInfo.value = { ...item }
  modalCacheData.value = { 
    current_step: detailData?.current_step ?? null,
    history: detailData?.history ?? null,
    props: detailData?.props ?? null
  }
  showModalEx.value = true
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
    if (!cacheDetails[taskId]) {
      await loadCacheDetail(taskId)
    }
  }
}

const loadCacheDetail = async (taskId: string) => {
  loadingDetails[taskId] = true
  delete detailErrors[taskId]
  
  try {
    const response = await getCacheDetail(taskId)
    if (response.success) {
      // 确保数据结构正确
      cacheDetails[taskId] = {
        current_step: response.data.current_step ?? null,
        history: response.data.history ?? null,
        props: response.data.props ?? null
      }
      console.log('缓存详情数据:', cacheDetails[taskId])
    } else {
      detailErrors[taskId] = response.message || '加载失败'
    }
  } catch (e: any) {
    detailErrors[taskId] = e.message || '加载失败'
    console.error('加载缓存详情失败:', e)
  } finally {
    loadingDetails[taskId] = false
  }
}

const loadCacheList = async () => {
  loading.value = true
  error.value = ''
  
  try {
    // 加载总数
    const countResponse = await getCacheCount()
    if (countResponse.success) {
      totalCount.value = countResponse.total
    }
    
    // 加载列表
    const listResponse = await getCacheList(currentPage.value, pageSize.value)
    if (listResponse.success) {
      cacheList.value = listResponse.data
      totalPages.value = listResponse.pages
    } else {
      error.value = listResponse.message || '加载失败'
    }
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadCacheList()
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

