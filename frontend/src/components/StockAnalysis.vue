<template>
  <div class="stock-analysis">
    <h2>股票分析</h2>
    <form @submit.prevent="analyzeStock">
      <div class="form-group">
        <label for="symbol">股票代码:</label>
        <input
          id="symbol"
          v-model="form.symbol"
          type="text"
          placeholder="e.g., AAPL or 000001"
          required
        >
      </div>
      <div class="form-group">
        <label for="tradeDate">交易日期 (可选):</label>
        <input
          id="tradeDate"
          v-model="form.trade_date"
          type="date"
        >
      </div>
      <button type="submit" :disabled="loading">
        {{ loading ? '分析中...' : '开始分析' }}
      </button>
    </form>

    <div v-if="loading" class="loading">
      正在启动分析任务...
    </div>

    <div v-if="analysisId" class="status-section">
      <p>分析任务 ID: {{ analysisId }}</p>
      <p v-if="polling">轮询状态中... 当前状态: {{ currentStatus }}</p>
      <button @click="stopAnalysis" v-if="currentStatus === 'running'" :disabled="!analysisId">
        停止分析
      </button>
    </div>

    <div v-if="error" class="error">
      <h3>错误:</h3>
      <p>{{ error }}</p>
    </div>

    <div v-if="result" class="result">
      <h3>分析结果</h3>
      <div v-if="result.decision" class="decision">
        <h4>交易决策:</h4>
        <pre>{{ JSON.stringify(result.decision, null, 2) }}</pre>
      </div>
      
      <div class="generate-section" v-if="analysisId">
        <button @click="generateReport" :disabled="generating">
          {{ generating ? '生成中...' : '生成 Markdown 报告' }}
        </button>
        <div v-if="generateStatus" :class="['generate-status', { success: generateStatus.includes('成功') }]">
          {{ generateStatus }}
        </div>
      </div>
      
      <ReportComponent v-if="analysisId" :analysis-id="analysisId" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import ReportComponent from './ReportComponent.vue'

const form = ref({
  symbol: '',
  trade_date: ''
})

const loading = ref(false)
const error = ref('')
const result = ref(null)
const analysisId = ref('')
const polling = ref(false)
const currentStatus = ref('')
const pollInterval = ref(null)
const generating = ref(false)
const generateStatus = ref('')

const analyzeStock = async () => {
  loading.value = true
  error.value = ''
  result.value = null
  analysisId.value = ''
  generating.value = false
  generateStatus.value = ''
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    polling.value = false
  }

  try {
    const requestData = {
      stock_symbol: form.value.symbol,
      market_type: '美股', // 默认，可扩展
      analysis_date: form.value.trade_date || undefined,
      analysts: ['market_analyst', 'news_analyst', 'fundamentals_analyst'],
      research_depth: 3,
      include_sentiment: true,
      include_risk_assessment: true
    }

    const response = await axios.post('/api/analysis/start', requestData)
    analysisId.value = response.data.analysis_id
    currentStatus.value = response.data.status
    startPolling()
  } catch (err) {
    if (err.response) {
      error.value = err.response.data.detail || '启动分析失败'
    } else {
      error.value = '连接后端失败，请确保API服务器运行在 localhost:8000'
    }
  } finally {
    loading.value = false
  }
}

const startPolling = () => {
  polling.value = true
  pollInterval.value = setInterval(async () => {
    if (!analysisId.value) return

    try {
      const statusResponse = await axios.get(`/api/analysis/${analysisId.value}/status`)
      currentStatus.value = statusResponse.data.status

      if (currentStatus.value === 'completed') {
        clearInterval(pollInterval.value)
        polling.value = false
        await fetchResult()
      } else if (currentStatus.value === 'failed' || currentStatus.value === 'stopped') {
        clearInterval(pollInterval.value)
        polling.value = false
        error.value = `分析${currentStatus.value === 'failed' ? '失败' : '已停止'}`
      }
    } catch (err) {
      console.error('Polling error:', err)
    }
  }, 2000)
}

const fetchResult = async () => {
  try {
    const resultResponse = await axios.get(`/api/analysis/${analysisId.value}/result`)
    result.value = resultResponse.data
  } catch (err) {
    error.value = '获取结果失败'
    console.error('Fetch result error:', err)
  }
}

const stopAnalysis = async () => {
  try {
    await axios.post(`/api/analysis/${analysisId.value}/stop`)
    currentStatus.value = 'stopped'
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      polling.value = false
    }
  } catch (err) {
    console.error('Stop analysis error:', err)
  }
}

const generateReport = async () => {
  if (!analysisId.value) return

  generating.value = true
  generateStatus.value = '生成中...'

  try {
    const generateResponse = await axios.post('/reports/generate', {
      analysis_id: analysisId.value,
      format: 'markdown'
    })

    if (generateResponse.data.status === 'completed') {
      generateStatus.value = `报告生成成功! 下载链接: ${generateResponse.data.download_url}`
    } else {
      generateStatus.value = '报告生成完成，但状态未知'
    }
  } catch (err) {
    generateStatus.value = '生成报告失败: ' + (err.response?.data?.detail || err.message)
    console.error('Generate report error:', err)
  } finally {
    generating.value = false
  }
}
</script>

<style scoped>
.stock-analysis {
  text-align: left;
  max-width: 800px;
  margin: 0 auto;
}
.form-group {
  margin-bottom: 15px;
}
label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}
input {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-sizing: border-box;
}
button {
  background-color: #007bff;
  color: white;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}
.loading, .error {
  margin: 20px 0;
  padding: 10px;
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
.status-section {
  margin: 20px 0;
  padding: 10px;
  background-color: #e9ecef;
  border-radius: 4px;
}
.result {
  margin-top: 20px;
  text-align: left;
}
.decision, .generate-section {
  margin-bottom: 20px;
}
pre {
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
  white-space: pre-wrap;
}
.generate-status {
  margin-top: 10px;
  padding: 8px;
  border-radius: 4px;
}
.generate-status.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}
</style>
