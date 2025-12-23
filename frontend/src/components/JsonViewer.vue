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
          :class="{
            'pr-28': searchQuery && searchResults.length > 0,
            'pr-9': !searchQuery || searchResults.length === 0
          }"
          @keydown.enter.prevent="navigateSearch('next')"
          @keydown.shift.enter.prevent="navigateSearch('prev')"
        />
        <svg
          class="absolute left-3 top-2.5 w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <!-- 搜索结果导航 -->
        <div v-if="searchQuery && searchResults.length > 0" class="absolute right-12 top-1/2 -translate-y-1/2 flex items-center gap-1">
          <button
            @click="navigateSearch('prev')"
            class="text-gray-400 hover:text-white transition-colors p-1 disabled:opacity-30 disabled:cursor-not-allowed"
            :disabled="currentResultIndex === 0"
            title="上一个 (Shift+Enter)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <span class="text-xs text-gray-400 px-1 min-w-[3rem] text-center">
            {{ currentResultIndex + 1 }}/{{ searchResults.length }}
          </span>
          <button
            @click="navigateSearch('next')"
            class="text-gray-400 hover:text-white transition-colors p-1 disabled:opacity-30 disabled:cursor-not-allowed"
            :disabled="currentResultIndex === searchResults.length - 1"
            title="下一个 (Enter)"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>
        <button
          v-if="searchQuery"
          @click="clearSearch"
          class="absolute right-3 top-2.5 text-gray-400 hover:text-white transition-colors p-1"
          title="清除搜索"
        >
          <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
    <!-- JSON内容 -->
    <div class="json-viewer-content-wrapper flex-1 overflow-hidden min-h-0">
      <div class="json-viewer-content" :class="{ 'compact': compact }" :style="{ maxHeight: maxHeight }" ref="containerRef">
        <pre class="json-text" v-html="syntaxHighlightedJson" ref="preRef"></pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick } from 'vue'

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

const containerRef = ref<HTMLElement | null>(null)
const preRef = ref<HTMLElement | null>(null)
const searchQuery = ref<string>('')

// 搜索结果相关
const searchResults = ref<Array<{ id: string, element: HTMLElement | null }>>([])
const currentResultIndex = ref<number>(0)

// 缓存语法高亮结果，避免重复计算
const syntaxHighlightedJson = ref<string>('')

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
  let highlighted = escapedJson.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
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
  
  // 如果有搜索词，进行搜索高亮
  if (searchQuery.value.trim()) {
    highlighted = applySearchHighlight(highlighted, searchQuery.value.trim())
  }
  
  syntaxHighlightedJson.value = highlighted
}

// 应用搜索高亮（部分匹配）
const applySearchHighlight = (html: string, query: string): string => {
  if (!query.trim()) {
    searchResults.value = []
    currentResultIndex.value = 0
    return html
  }
  
  // 转义搜索词中的特殊字符
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  
  // 创建正则表达式，用于匹配搜索词（不要求完整词匹配，大小写不敏感）
  const regex = new RegExp(`(${escapedQuery})`, 'gi')
  
  // 重置搜索结果
  searchResults.value = []
  let resultIndex = 0
  
  // 第一步：处理span标签内的文本
  let result = html.replace(/(<span[^>]*>)(.*?)(<\/span>)/g, (match, openTag, content, closeTag) => {
    // 如果内容中已经有mark标签，跳过（避免重复处理）
    if (content.includes('<mark')) {
      return match
    }
    
    // 在span内容中查找并高亮搜索词
    const highlightedContent = content.replace(regex, (m: string) => {
      const resultId = `search-result-${resultIndex++}`
      searchResults.value.push({ id: resultId, element: null })
      return `<mark class="json-search-highlight" data-search-id="${resultId}">${m}</mark>`
    })
    
    return openTag + highlightedContent + closeTag
  })
  
  // 第二步：处理不在span标签内的文本（如逗号、冒号、空格等）
  // 使用临时标记保护所有HTML标签
  const TEMP_PLACEHOLDER = '___TEMP_PLACEHOLDER_'
  const placeholders: string[] = []
  let placeholderIndex = 0
  
  // 保护所有HTML标签
  let protectedHtml = result.replace(/<[^>]+>/g, (tag) => {
    const placeholder = `${TEMP_PLACEHOLDER}${placeholderIndex}${TEMP_PLACEHOLDER}`
    placeholders.push(tag)
    placeholderIndex++
    return placeholder
  })
  
  // 在纯文本中匹配搜索词
  protectedHtml = protectedHtml.replace(regex, (match) => {
    const resultId = `search-result-${resultIndex++}`
    searchResults.value.push({ id: resultId, element: null })
    return `<mark class="json-search-highlight" data-search-id="${resultId}">${match}</mark>`
  })
  
  // 恢复HTML标签
  placeholders.forEach((tag, index) => {
    protectedHtml = protectedHtml.replace(
      `${TEMP_PLACEHOLDER}${index}${TEMP_PLACEHOLDER}`,
      tag
    )
  })
  
  // 重置当前索引
  currentResultIndex.value = searchResults.value.length > 0 ? 0 : -1
  
  return protectedHtml
}

// 更新搜索结果元素引用并高亮当前结果
const updateSearchResults = () => {
  if (!preRef.value || searchResults.value.length === 0) return
  
  // 更新所有搜索结果的元素引用
  searchResults.value.forEach((result) => {
    const element = preRef.value?.querySelector(`[data-search-id="${result.id}"]`) as HTMLElement
    result.element = element || null
  })
  
  // 高亮当前结果所在的行
  highlightCurrentResult()
}

// 高亮当前搜索结果所在的行
const highlightCurrentResult = () => {
  if (!preRef.value || currentResultIndex.value < 0 || currentResultIndex.value >= searchResults.value.length) {
    // 清除所有行高亮
    preRef.value?.querySelectorAll('.json-line-highlight').forEach((el) => {
      el.classList.remove('json-line-highlight')
    })
    return
  }
  
  const currentResult = searchResults.value[currentResultIndex.value]
  if (!currentResult.element) {
    // 如果元素不存在，尝试重新查找
    const element = preRef.value?.querySelector(`[data-search-id="${currentResult.id}"]`) as HTMLElement
    if (element) {
      currentResult.element = element
    } else {
      return
    }
  }
  
  // 清除所有行高亮
  preRef.value?.querySelectorAll('.json-line-highlight').forEach((el) => {
    el.classList.remove('json-line-highlight')
  })
  
  // 给当前结果的元素添加高亮类
  const element = currentResult.element
  if (!element) return
  
  element.classList.add('json-line-highlight')
  
  // 找到包含当前结果所在行的元素
  // 向上查找包含换行符的父元素，找到包含整行的最小父元素
  let parent = element.parentElement
  let bestParent: HTMLElement | null = null
  
  while (parent && parent !== preRef.value) {
    const parentText = parent.textContent || ''
    // 如果父元素包含换行符，说明它可能包含整行
    if (parentText.includes('\n')) {
      const lines = parentText.split('\n')
      // 如果父元素只包含一行（除了前后可能有部分内容），使用它
      if (lines.length <= 2) {
        bestParent = parent
        // 继续向上查找，看是否有更合适的父元素
        let nextParent = parent.parentElement
        while (nextParent && nextParent !== preRef.value) {
          const nextParentText = nextParent.textContent || ''
          if (nextParentText.includes('\n')) {
            const nextLines = nextParentText.split('\n')
            // 如果下一个父元素也只包含一行或两行，且包含当前结果，使用它
            if (nextLines.length <= 2 && nextParentText.includes(element.textContent || '')) {
              bestParent = nextParent
              parent = nextParent
              nextParent = nextParent.parentElement
            } else {
              break
            }
          } else {
            break
          }
        }
        break
      }
    }
    parent = parent.parentElement
  }
  
  // 如果找到了合适的父元素，也给父元素添加高亮
  if (bestParent && bestParent !== element) {
    bestParent.classList.add('json-line-highlight')
  }
}

// 滚动到当前搜索结果
const scrollToCurrentResult = () => {
  if (!containerRef.value || currentResultIndex.value < 0 || currentResultIndex.value >= searchResults.value.length) {
    return
  }
  
  const currentResult = searchResults.value[currentResultIndex.value]
  if (!currentResult.element) return
  
  // 找到包含整行高亮的元素（可能是父元素）
  let elementToScroll = currentResult.element
  
  // 如果当前元素有 json-line-highlight 类的父元素，使用父元素
  let parent = currentResult.element.parentElement
  while (parent && parent !== preRef.value) {
    if (parent.classList.contains('json-line-highlight')) {
      elementToScroll = parent
      break
    }
    parent = parent.parentElement
  }
  
  // 使用更可靠的手动滚动方法
  // 等待一小段时间确保DOM已更新
  setTimeout(() => {
    if (!containerRef.value || !elementToScroll) return
    
    const container = containerRef.value
    const containerRect = container.getBoundingClientRect()
    const elementRect = elementToScroll.getBoundingClientRect()
    
    // 计算元素相对于容器的位置
    const elementTop = elementRect.top - containerRect.top + container.scrollTop
    const elementBottom = elementTop + elementRect.height
    const containerHeight = container.clientHeight
    const currentScrollTop = container.scrollTop
    
    // 计算目标滚动位置，使元素在容器中居中显示
    const targetScrollTop = elementTop - (containerHeight / 2) + (elementRect.height / 2)
    
    // 如果元素不在可视区域内，或者需要更好的定位，滚动到目标位置
    const isElementVisible = elementTop >= currentScrollTop && elementBottom <= currentScrollTop + containerHeight
    
    if (!isElementVisible || Math.abs(targetScrollTop - currentScrollTop) > 10) {
      container.scrollTo({
        top: Math.max(0, targetScrollTop),
        behavior: 'smooth'
      })
    }
  }, 50)
}

// 导航搜索结果
const navigateSearch = (direction: 'next' | 'prev') => {
  if (searchResults.value.length === 0) return
  
  if (direction === 'next') {
    currentResultIndex.value = (currentResultIndex.value + 1) % searchResults.value.length
  } else {
    currentResultIndex.value = currentResultIndex.value === 0 
      ? searchResults.value.length - 1 
      : currentResultIndex.value - 1
  }
  
  // 等待DOM更新后执行
  nextTick(() => {
    updateSearchResults()
    scrollToCurrentResult()
  })
}

// 监听搜索词变化，重新计算高亮
watch(() => searchQuery.value, () => {
  computeSyntaxHighlight()
  // 等待DOM更新后更新搜索结果引用
  setTimeout(() => {
    updateSearchResults()
    if (searchResults.value.length > 0) {
      scrollToCurrentResult()
    }
  }, 0)
})

// 监听JSON内容变化，重新计算语法高亮
watch(() => formattedJson.value, () => {
  computeSyntaxHighlight()
  // 等待DOM更新后更新搜索结果引用
  setTimeout(() => {
    updateSearchResults()
    if (searchResults.value.length > 0 && currentResultIndex.value >= 0) {
      scrollToCurrentResult()
    }
  }, 0)
}, { immediate: true })

const clearSearch = () => {
  searchQuery.value = ''
  searchResults.value = []
  currentResultIndex.value = 0
}
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
  /* 整行高亮的颜色变量 - 统一管理背景色和边框色 */
  --line-highlight-bg: rgba(117, 228, 80, 0.5);
  --line-highlight-border: #f59e0b;
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
.json-text :deep(.json-search-highlight) {
  background-color: #fbbf24;
  color: #1e293b;
  padding: 2px 0;
  border-radius: 2px;
  font-weight: 600;
}

/* 当前搜索结果所在行的整行高亮 - 使用黄色/橙色系以在蓝色背景上更明显 */
.json-text :deep(.json-line-highlight) {
  position: relative;
  background-color: var(--line-highlight-bg) !important;
  border-left: 3px solid var(--line-highlight-border) !important;
  padding: 2px 4px;
  margin: 0 -4px;
  display: inline-block;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

/* 对于包含换行符的父元素（整行），使用块级显示来高亮整行 */
.json-text :deep(.json-line-highlight:not(mark)) {
  display: block !important;
  width: calc(100% + 32px) !important;
  margin-left: -16px !important;
  margin-right: -16px !important;
  padding-left: 16px !important;
  padding-right: 16px !important;
  background-color: var(--line-highlight-bg) !important;
  border-left: 3px solid var(--line-highlight-border) !important;
  box-sizing: border-box;
  min-height: 1.7em;
}

/* 对于mark元素，确保高亮可见 */
.json-text :deep(mark.json-line-highlight) {
  background-color: var(--line-highlight-bg) !important;
  border-left: 3px solid var(--line-highlight-border) !important;
  position: relative;
  z-index: 1;
}

/* 使用伪元素为mark元素扩展背景到整行 */
.json-text :deep(mark.json-line-highlight)::before {
  content: '';
  position: absolute;
  left: -100vw;
  right: -100vw;
  top: 0;
  bottom: 0;
  background-color: var(--line-highlight-bg);
  border-left: 3px solid var(--line-highlight-border);
  z-index: -1;
  pointer-events: none;
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

