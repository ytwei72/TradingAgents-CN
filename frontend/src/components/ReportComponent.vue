<template>
  <div class="report-component">
    <div v-if="loading" class="loading">加载报告中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="reports.length === 0" class="no-reports">无报告可用</div>
    <div v-else class="reports-container">
      <!-- 报告导航 Tabs -->
      <div class="tabs">
        <button
          v-for="(report, index) in reports"
          :key="report.report_id"
          @click="activeTab = index"
          :class="{ active: activeTab === index }"
          class="tab-button"
        >
          {{ report.stage_display_name }}
        </button>
      </div>
      
      <!-- 活动报告内容 -->
      <div class="report-content">
        <div class="report-header">
          <!-- <h3>{{ currentReport.title }}</h3> -->
          <p class="created-at">创建时间: {{ formatDate(currentReport.created_at) }}</p>
        </div>
        <div 
          class="markdown-content prose prose-invert prose-lg max-w-none"
          v-html="renderedContent"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import '../styles/markdown-render-paper.css'

const props = defineProps({
  analysisId: {
    type: String,
    default: ''
  }
})

const reports = ref([])
const loading = ref(true)
const error = ref('')
const activeTab = ref(0)

const currentReport = computed(() => reports.value[activeTab.value] || {})
const renderedContent = computed(() => {
  if (!currentReport.value.content) return ''
  const html = marked.parse(currentReport.value.content)
  return DOMPurify.sanitize(html)
})

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleString('zh-CN')
}

const fetchReports = async () => {
  // 如果 analysisId 为空，不发起请求
  if (!props.analysisId) {
    loading.value = false
    return
  }
  
  try {
    loading.value = true
    const response = await axios.get(`/api/reports/${props.analysisId}/reports`)
    reports.value = response.data.data.reports || []
    if (reports.value.length > 0) {
      // 默认选择最终报告（假设 stage 为 'final_decision'）
      const finalIndex = reports.value.findIndex(r => r.stage === 'final_decision')
      activeTab.value = finalIndex !== -1 ? finalIndex : 0
    }
  } catch (err) {
    error.value = err.response?.data?.detail || '获取报告失败'
    console.error('Fetch reports error:', err)
  } finally {
    loading.value = false
  }
}

// 监听 analysisId 变化
watch(() => props.analysisId, (newId) => {
  if (newId) {
    fetchReports()
  } else {
    reports.value = []
    error.value = ''
  }
})

onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.report-component {
  max-width: 100%;
  margin: 0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.loading, .error, .no-reports {
  text-align: center;
  padding: 20px;
  margin: 20px 0;
  border-radius: 8px;
}

.loading {
  background-color: #1e293b;
  color: #60a5fa;
  border: 1px solid #3b82f6;
}

.error {
  background-color: #7f1d1d;
  color: #fca5a5;
  border: 1px solid #dc2626;
}

.no-reports {
  background-color: #78350f;
  color: #fcd34d;
  border: 1px solid #f59e0b;
}

.tabs {
  display: flex;
  border-bottom: 2px solid #475569;
  margin-bottom: 20px;
  overflow-x: auto;
}

.tab-button {
  background: none;
  border: none;
  padding: 10px 20px;
  cursor: pointer;
  color: #94a3b8;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #60a5fa;
  background-color: #1e293b;
}

.tab-button.active {
  color: #60a5fa;
  border-bottom-color: #3b82f6;
  font-weight: bold;
}

.report-header {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #475569;
}

.report-header h3 {
  margin: 0 0 5px 0;
  color: #f1f5f9;
}

.created-at {
  margin: 0;
  color: #94a3b8;
  font-size: 0.9em;
}

@media (max-width: 768px) {
  .tabs {
    flex-direction: column;
  }
  
  .tab-button {
    border-bottom: 1px solid #dee2e6;
    border-left: none;
  }
  
  .report-component {
    margin: 10px;
  }
}
</style>
