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
          class="w-full px-3 py-2 pl-9 pr-9 bg-gray-800 border border-gray-600 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <svg
          class="absolute left-3 top-2.5 w-4 h-4 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
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
import { computed, watch, ref } from 'vue'

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
  if (!query.trim()) return html
  
  // 转义搜索词中的特殊字符
  const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  
  // 创建正则表达式，用于匹配搜索词（不要求完整词匹配，大小写不敏感）
  const regex = new RegExp(`(${escapedQuery})`, 'gi')
  
  // 第一步：处理span标签内的文本
  let result = html.replace(/(<span[^>]*>)(.*?)(<\/span>)/g, (match, openTag, content, closeTag) => {
    // 如果内容中已经有mark标签，跳过（避免重复处理）
    if (content.includes('<mark')) {
      return match
    }
    
    // 在span内容中查找并高亮搜索词
    const highlightedContent = content.replace(regex, (m: string) => {
      return `<mark class="json-search-highlight">${m}</mark>`
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
    return `<mark class="json-search-highlight">${match}</mark>`
  })
  
  // 恢复HTML标签
  placeholders.forEach((tag, index) => {
    protectedHtml = protectedHtml.replace(
      `${TEMP_PLACEHOLDER}${index}${TEMP_PLACEHOLDER}`,
      tag
    )
  })
  
  return protectedHtml
}

// 监听搜索词变化，重新计算高亮
watch(() => searchQuery.value, () => {
  computeSyntaxHighlight()
})

// 监听JSON内容变化，重新计算语法高亮
watch(() => formattedJson.value, () => {
  computeSyntaxHighlight()
  // 不清除搜索，保持搜索状态
}, { immediate: true })

const clearSearch = () => {
  searchQuery.value = ''
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

