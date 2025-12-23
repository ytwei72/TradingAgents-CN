<template>
  <Transition name="modal">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
      @click.self="handleClose"
    >
      <div class="w-full h-full flex flex-col bg-[#0f172a]">
        <!-- 主要内容区域：左右两列 -->
        <div class="flex-1 flex min-h-0 overflow-hidden">
          <!-- 左列：JSON查看器 -->
          <div class="flex-1 flex flex-col min-h-0 border-r border-gray-700">
            <JsonViewer
              :data="currentData"
              :title="getSubKeyLabel(selectedSubKey)"
              :max-height="'100%'"
              :show-search="true"
            />
          </div>
          
          <!-- 右列：缓存记录概要和子键选择器 -->
          <div class="w-96 flex flex-col border-l border-gray-700 bg-[#1e293b]">
            <!-- 标题区域 -->
            <div class="p-4 border-b border-gray-700 flex items-center justify-between">
              <div>
                <h4 class="text-base font-semibold text-white mb-1">
                  {{ cacheInfo.company_name || 'N/A' }}
                </h4>
                <p class="text-sm text-gray-400">
                  {{ cacheInfo.stock_symbol || 'N/A' }}
                </p>
              </div>
              <button
                @click="handleClose"
                class="text-gray-400 hover:text-white transition-colors p-2 hover:bg-gray-700 rounded-lg"
                title="关闭 (ESC)"
              >
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <!-- 缓存记录概要 -->
            <div class="p-4 border-b border-gray-700 space-y-3">
              <div>
                <span class="text-xs text-gray-400 block mb-1">分析任务ID</span>
                <span class="text-sm text-white font-mono break-all">{{ cacheInfo.task_id || 'N/A' }}</span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block mb-1">分析日期</span>
                <span class="text-sm text-white">{{ cacheInfo.analysis_date || 'N/A' }}</span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block mb-1">创建时间</span>
                <span class="text-sm text-white">{{ formatDate(cacheInfo.created_at) }}</span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block mb-1">更新时间</span>
                <span class="text-sm text-white">{{ formatDate(cacheInfo.updated_at) }}</span>
              </div>
              <div>
                <span class="text-xs text-gray-400 block mb-1">状态</span>
                <span
                  class="inline-block px-2 py-1 text-xs font-semibold rounded"
                  :class="getStatusClass(cacheInfo.status)"
                >
                  {{ cacheInfo.status || 'N/A' }}
                </span>
              </div>
            </div>
            
            <!-- 子键选择器 -->
            <div class="flex-1 overflow-y-auto p-4">
              <div class="space-y-2">
                <h5 class="text-sm font-medium text-gray-300 mb-3">选择子键</h5>
                <button
                  v-for="subKey in subKeys"
                  :key="subKey.key"
                  @click="selectedSubKey = subKey.key"
                  class="w-full text-left px-3 py-2 text-sm rounded-lg transition-colors"
                  :class="selectedSubKey === subKey.key
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-700/50 text-gray-300 hover:bg-gray-700'"
                >
                  <div class="font-medium">{{ subKey.label }}</div>
                  <div class="text-xs mt-0.5 opacity-75">
                    {{ subKey.description }}
                  </div>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import JsonViewer from './JsonViewer.vue'

interface CacheInfo {
  task_id?: string
  status?: string
  created_at?: string
  updated_at?: string
  analysis_date?: string
  stock_symbol?: string
  company_name?: string
}

interface CacheData {
  current_step?: any
  history?: any
  props?: any
}

interface Props {
  modelValue: boolean
  cacheInfo?: CacheInfo
  cacheData?: CacheData
}

const props = withDefaults(defineProps<Props>(), {
  cacheInfo: () => ({}),
  cacheData: () => ({})
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const selectedSubKey = ref<string>('current_step')

const subKeys = [
  { key: 'current_step', label: 'Current Step', description: '当前步骤信息' },
  { key: 'history', label: 'History', description: '历史步骤列表' },
  { key: 'props', label: 'Props', description: '任务属性信息' }
]

const currentData = computed(() => {
  return props.cacheData?.[selectedSubKey.value as keyof CacheData] ?? null
})

const getSubKeyLabel = (key: string) => {
  const subKey = subKeys.find(s => s.key === key)
  return subKey?.label || key
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

const getStatusClass = (status?: string) => {
  const statusMap: Record<string, string> = {
    'completed': 'bg-green-600/20 text-green-400 border border-green-600/30',
    'running': 'bg-blue-600/20 text-blue-400 border border-blue-600/30',
    'pending': 'bg-yellow-600/20 text-yellow-400 border border-yellow-600/30',
    'failed': 'bg-red-600/20 text-red-400 border border-red-600/30',
    'paused': 'bg-gray-600/20 text-gray-400 border border-gray-600/30',
    'stopped': 'bg-red-600/20 text-red-400 border border-red-600/30'
  }
  return statusMap[status || ''] || 'bg-gray-600/20 text-gray-400 border border-gray-600/30'
}

const handleClose = () => {
  emit('update:modelValue', false)
}

// ESC键关闭模态框
const handleEscape = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && props.modelValue) {
    handleClose()
  }
}

// 监听显示状态，控制背景滚动
watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    document.body.style.overflow = 'hidden'
    // 重置选中的子键
    selectedSubKey.value = 'current_step'
  } else {
    document.body.style.overflow = ''
  }
})

onMounted(() => {
  window.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleEscape)
  document.body.style.overflow = ''
})
</script>

<style scoped>
/* 模态框动画 */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-active > div,
.modal-leave-active > div {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from > div,
.modal-leave-to > div {
  transform: scale(0.95);
  opacity: 0;
}

/* 自定义滚动条样式 */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: #1e293b;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>

