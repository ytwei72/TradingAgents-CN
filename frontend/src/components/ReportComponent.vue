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
          {{ report.title }} ({{ report.stage }})
        </button>
      </div>
      
      <!-- 活动报告内容 -->
      <div class="report-content">
        <div class="report-header">
          <h3>{{ currentReport.title }}</h3>
          <p class="created-at">创建时间: {{ formatDate(currentReport.created_at) }}</p>
        </div>
        <div 
          class="markdown-content"
          v-html="renderedContent"
        ></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

const props = defineProps({
  analysisId: {
    type: String,
    required: true
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
  try {
    loading.value = true
    const response = await axios.get(`/api/analysis/${props.analysisId}/reports`)
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

onMounted(() => {
  fetchReports()
})
</script>

<style scoped>
.report-component {
  max-width: 800px;
  margin: 20px auto;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.loading, .error, .no-reports {
  text-align: center;
  padding: 20px;
  margin: 20px 0;
  border-radius: 4px;
}

.loading {
  background-color: #d1ecf1;
  color: #0c5460;
}

.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.no-reports {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.tabs {
  display: flex;
  border-bottom: 2px solid #dee2e6;
  margin-bottom: 20px;
  overflow-x: auto;
}

.tab-button {
  background: none;
  border: none;
  padding: 10px 20px;
  cursor: pointer;
  color: #6c757d;
  border-bottom: 2px solid transparent;
  white-space: nowrap;
}

.tab-button:hover {
  color: #0056b3;
}

.tab-button.active {
  color: #0056b3;
  border-bottom-color: #0056b3;
  font-weight: bold;
}

.report-header {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #dee2e6;
}

.report-header h3 {
  margin: 0 0 5px 0;
  color: #212529;
}

.created-at {
  margin: 0;
  color: #6c757d;
  font-size: 0.9em;
}

.markdown-content {
  line-height: 1.6;
  color: #212529;
}

.markdown-content h1, .markdown-content h2, .markdown-content h3 {
  margin-top: 0;
  color: #0056b3;
}

.markdown-content pre {
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 4px;
  overflow-x: auto;
  border: 1px solid #dee2e6;
}

.markdown-content code {
  background-color: #f8f9fa;
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 0.9em;
}

.markdown-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
}

.markdown-content th, .markdown-content td {
  border: 1px solid #dee2e6;
  padding: 8px;
  text-align: left;
}

.markdown-content th {
  background-color: #f8f9fa;
  font-weight: bold;
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
