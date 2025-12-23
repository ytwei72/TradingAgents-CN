<template>
  <div class="json-viewer-container">
    <!-- 标题和搜索框 -->
    <div v-if="title || showSearch" class="json-viewer-header p-4 border-b border-gray-700 flex-shrink-0">
      <div v-if="title" class="flex items-center justify-between mb-3">
        <h4 class="text-sm font-medium text-gray-300">
          {{ title }}
        </h4>
      </div>
      <!-- 搜索框 -->
      <div v-if="showSearch" class="relative">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索JSON内容..."
          class="w-full px-3 py-2 pl-9 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          @input="handleSearch"
          @keydown="handleKeyDown"
        />
        <svg
          class="absolute left-3 top-2.5 w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <div v-if="searchQuery" class="absolute right-3 top-2.5 flex items-center gap-2">
          <span v-if="isSearching" class="text-xs text-gray-400">搜索中...</span>
          <span v-else class="text-xs text-gray-400">
            {{ matchCount > 0 ? `${currentMatchIndex + 1}/${matchCount}` : '0/0' }}
          </span>
          <button
            v-if="matchCount > 0"
            @click="previousMatch"
            class="text-gray-400 hover:text-white transition-colors p-1"
            title="上一个 (↑)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <button
            v-if="matchCount > 0"
            @click="nextMatch"
            class="text-gray-400 hover:text-white transition-colors p-1"
            title="下一个 (↓)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <button
            @click="clearSearch"
            class="text-gray-400 hover:text-white transition-colors p-1"
            title="清除搜索"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </div>
    <!-- JSON内容 -->
    <div class="json-viewer-content-wrapper flex-1 overflow-hidden min-h-0">
      <div class="json-viewer-content" :class="{ 'compact': compact }" :style="{ maxHeight: maxHeight }" ref="containerRef">
        <pre class="json-text" v-html="highlightedJson" ref="preRef"></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick } from 'vue'

// 防抖函数
function debounce<T extends (...args: any[]) => any>(func: T, wait: number): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null
  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null
      func(...args)
    }
    if (timeout) {
      clearTimeout(timeout)
    }
    timeout = setTimeout(later, wait)
  }
}

interface Props {
  data: any
  title?: string
  compact?: boolean
  showLineNumbers?: boolean
  maxHeight?: string
  showSearch?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
  showLineNumbers: true,
  maxHeight: '600px',
  showSearch: true,
  title: ''
})

const emit = defineEmits<{
  'match-updated': [count: number]
}>()

const containerRef = ref<HTMLElement | null>(null)
const preRef = ref<HTMLElement | null>(null)
const matchPositions = ref<Array<{ start: number; end: number }>>([])
const searchQuery = ref<string>('')
const debouncedSearchQuery = ref<string>('')
const currentMatchIndex = ref<number>(-1)
const matchCount = ref<number>(0)
const isSearching = ref<boolean>(false)

// 缓存语法高亮结果，避免重复计算
const syntaxHighlightedJson = ref<string>('')
const plainJsonText = ref<string>('')

// 格式化JSON（只在data变化时计算）
const formattedJson = computed(() => {
  if (props.data === null || props.data === undefined) {
    return 'null'
  }
  
  try {
    if (typeof props.data === 'string') {
      // 尝试解析字符串为JSON
      try {
        const parsed = JSON.parse(props.data)
        return JSON.stringify(parsed, null, props.compact ? 0 : 2)
      } catch {
        return props.data
      }
    }
    return JSON.stringify(props.data, null, props.compact ? 0 : 2)
  } catch (e) {
    return String(props.data)
  }
})

// 计算语法高亮（只在JSON内容变化时重新计算）
const computeSyntaxHighlight = () => {
  const json = formattedJson.value
  plainJsonText.value = json
  
  if (json === 'null') {
    syntaxHighlightedJson.value = '<span class="json-null">null</span>'
    return
  }
  
  // 先进行HTML转义
  let escapedJson = json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  
  // 进行JSON语法高亮
  syntaxHighlightedJson.value = escapedJson.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
    let cls = 'json-number'
    if (/^"/.test(match)) {
      if (/:$/.test(match)) {
        cls = 'json-key'
      } else {
        cls = 'json-string'
      }
    } else if (/true|false/.test(match)) {
      cls = 'json-boolean'
    } else if (/null/.test(match)) {
      cls = 'json-null'
    }
    return `<span class="${cls}">${match}</span>`
  })
}

// 监听JSON内容变化，重新计算语法高亮
watch(() => formattedJson.value, () => {
  computeSyntaxHighlight()
  // 清除搜索
  searchQuery.value = ''
  debouncedSearchQuery.value = ''
  currentMatchIndex.value = -1
  matchCount.value = 0
}, { immediate: true })

// 应用搜索高亮到语法高亮的结果上（简化优化版本）
const applySearchHighlight = (syntaxHighlighted: string, searchTerm: string): string => {
  if (!searchTerm || !searchTerm.trim()) {
    return syntaxHighlighted
  }
  
  const term = searchTerm.trim()
  const escapedTerm = escapeHtml(term)
  
  // 使用简单的全局替换，但需要避免重复包裹
  const regex = new RegExp(`(${escapeRegex(escapedTerm)})`, 'gi')
  const positions: Array<{ index: number; length: number }> = []
  
  // 先找到所有匹配位置（避免在已高亮的区域内）
  let match
  const tempResult = syntaxHighlighted
  while ((match = regex.exec(tempResult)) !== null) {
    // 检查是否已经在search-match span内
    const beforeMatch = tempResult.substring(0, match.index)
    const searchMatchOpen = (beforeMatch.match(/<span class="search-match/g) || []).length
    const searchMatchClose = (beforeMatch.match(/<\/span>/g) || []).length
    
    if (searchMatchOpen <= searchMatchClose) {
      // 不在搜索高亮内，记录位置
      positions.push({ index: match.index, length: match[0].length })
    }
  }
  
  matchPositions.value = positions.map(p => ({ start: p.index, end: p.index + p.length }))
  
  if (positions.length === 0) {
    return syntaxHighlighted
  }
  
  // 从后往前替换，避免位置偏移
  let result = syntaxHighlighted
  for (let i = positions.length - 1; i >= 0; i--) {
    const pos = positions[i]
    const isCurrentMatch = i === currentMatchIndex.value
    const searchClass = isCurrentMatch ? 'search-match search-match-current' : 'search-match'
    
    const before = result.substring(0, pos.index)
    const matched = result.substring(pos.index, pos.index + pos.length)
    const after = result.substring(pos.index + pos.length)
    
    result = before + `<span class="${searchClass}">${matched}</span>` + after
  }
  
  return result
}

// 最终的高亮JSON（使用防抖后的搜索查询）
const highlightedJson = computed(() => {
  const base = syntaxHighlightedJson.value
  
  if (!debouncedSearchQuery.value || !debouncedSearchQuery.value.trim()) {
    return base
  }
  
  return applySearchHighlight(base, debouncedSearchQuery.value)
})

const escapeRegex = (str: string) => {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

const escapeHtml = (str: string) => {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

// 防抖的搜索处理函数
const debouncedSearch = debounce((query: string) => {
  debouncedSearchQuery.value = query
  
  // 使用 nextTick 确保在下一个事件循环中更新，避免阻塞
  nextTick(() => {
    isSearching.value = false
    
    if (query && query.trim()) {
      // 更新匹配数量（在 highlightedJson computed 中会计算实际数量）
      // 这里先设置一个临时值，避免闪烁
      const term = query.trim()
      const regex = new RegExp(escapeRegex(term), 'gi')
      const matches = plainJsonText.value.match(regex)
      const count = matches ? matches.length : 0
      
      matchCount.value = count
      if (count > 0 && currentMatchIndex.value === -1) {
        currentMatchIndex.value = 0
      } else if (count === 0) {
        currentMatchIndex.value = -1
      }
      
      emit('match-updated', count)
    } else {
      matchCount.value = 0
      currentMatchIndex.value = -1
      emit('match-updated', 0)
    }
  })
}, 200) // 200ms 防抖延迟，稍微增加以减少计算频率

const handleSearch = () => {
  isSearching.value = true
  currentMatchIndex.value = -1
  debouncedSearch(searchQuery.value)
}

const clearSearch = () => {
  searchQuery.value = ''
  debouncedSearchQuery.value = ''
  currentMatchIndex.value = -1
  matchCount.value = 0
  isSearching.value = false
}

const previousMatch = () => {
  if (matchCount.value > 0) {
    currentMatchIndex.value = currentMatchIndex.value <= 0 
      ? matchCount.value - 1 
      : currentMatchIndex.value - 1
    scrollToMatch()
  }
}

const nextMatch = () => {
  if (matchCount.value > 0) {
    currentMatchIndex.value = (currentMatchIndex.value + 1) % matchCount.value
    scrollToMatch()
  }
}

const scrollToMatch = async () => {
  if (currentMatchIndex.value >= 0 && currentMatchIndex.value < matchCount.value && preRef.value) {
    await nextTick()
    const matches = preRef.value.querySelectorAll('.search-match')
    if (matches[currentMatchIndex.value]) {
      matches[currentMatchIndex.value].scrollIntoView({
        behavior: 'smooth',
        block: 'center'
      })
    }
  }
}

const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && searchQuery.value) {
    clearSearch()
  } else if (e.key === 'Enter' && searchQuery.value && matchCount.value > 0) {
    e.preventDefault()
    nextMatch()
  } else if (e.key === 'ArrowUp' && searchQuery.value && matchCount.value > 0) {
    e.preventDefault()
    previousMatch()
  } else if (e.key === 'ArrowDown' && searchQuery.value && matchCount.value > 0) {
    e.preventDefault()
    nextMatch()
  }
}

// 监听currentMatchIndex变化，更新高亮
watch(() => currentMatchIndex.value, () => {
  // 触发重新计算以更新当前匹配项的高亮
  if (debouncedSearchQuery.value) {
    // 强制更新
    const temp = debouncedSearchQuery.value
    debouncedSearchQuery.value = ''
    nextTick(() => {
      debouncedSearchQuery.value = temp
      scrollToMatch()
    })
  }
})

// 监听防抖后的搜索查询变化，更新匹配计数
watch(() => debouncedSearchQuery.value, (newVal) => {
  if (newVal && newVal.trim()) {
    const term = newVal.trim()
    const regex = new RegExp(escapeRegex(term), 'gi')
    const matches = plainJsonText.value.match(regex)
    const count = matches ? matches.length : 0
    
    matchCount.value = count
    if (count > 0 && currentMatchIndex.value === -1) {
      currentMatchIndex.value = 0
    } else if (count === 0) {
      currentMatchIndex.value = -1
    }
  } else {
    matchCount.value = 0
    currentMatchIndex.value = -1
  }
})
</script>

<style scoped>
.json-viewer-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.json-viewer-header {
  background: transparent;
}

.json-viewer-content-wrapper {
  padding: 16px;
}

.json-viewer-content {
  background: #0f172a;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 16px;
  overflow: auto;
  max-height: v-bind(maxHeight);
  height: 100%;
  position: relative;
  flex: 1;
  min-height: 0;
}

.json-viewer-content.compact {
  padding: 12px;
}

.json-text {
  margin: 0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.7;
  color: #e2e8f0;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-x: auto;
}

/* JSON语法高亮 */
.json-text :deep(.json-key) {
  color: #7dd3fc;
  font-weight: 500;
}

.json-text :deep(.json-string) {
  color: #86efac;
}

.json-text :deep(.json-number) {
  color: #fbbf24;
  font-weight: 500;
}

.json-text :deep(.json-boolean) {
  color: #a78bfa;
  font-weight: 500;
}

.json-text :deep(.json-null) {
  color: #94a3b8;
  font-style: italic;
}

/* 搜索高亮样式 */
.json-text :deep(.search-match) {
  background-color: rgba(251, 191, 36, 0.3);
  border-radius: 2px;
  padding: 1px 2px;
  transition: background-color 0.2s;
}

.json-text :deep(.search-match-current) {
  background-color: rgba(251, 191, 36, 0.6);
  box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.4);
  animation: search-pulse 1.5s ease-in-out;
}

@keyframes search-pulse {
  0%, 100% {
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(251, 191, 36, 0.6);
  }
}

/* 滚动条样式 */
.json-viewer-content::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.json-viewer-content::-webkit-scrollbar-track {
  background: #1e293b;
  border-radius: 4px;
}

.json-viewer-content::-webkit-scrollbar-thumb {
  background: #475569;
  border-radius: 4px;
}

.json-viewer-content::-webkit-scrollbar-thumb:hover {
  background: #64748b;
}
</style>

