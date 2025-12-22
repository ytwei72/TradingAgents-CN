<template>
  <div class="json-viewer-container">
    <div class="json-viewer-content" :class="{ 'compact': compact }" :style="{ maxHeight: maxHeight }">
      <pre class="json-text" v-html="highlightedJson"></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  data: any
  compact?: boolean
  showLineNumbers?: boolean
  maxHeight?: string
}

const props = withDefaults(defineProps<Props>(), {
  compact: false,
  showLineNumbers: true,
  maxHeight: '600px'
})

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

const highlightedJson = computed(() => {
  const json = formattedJson.value
  if (json === 'null') {
    return '<span class="json-null">null</span>'
  }
  
  // 简单的JSON语法高亮
  return json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
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
})
</script>

<style scoped>
.json-viewer-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
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

