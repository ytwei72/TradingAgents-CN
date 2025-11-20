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
      正在分析股票，请稍候...
    </div>

    <div v-if="error" class="error">
      <h3>错误:</h3>
      <p>{{ error }}</p>
    </div>

    <div v-if="result" class="result">
      <h3>分析结果</h3>
      <div v-if="result.decision" class="decision">
        <h4>交易决策:</h4>
        <pre>{{ result.decision }}</pre>
      </div>
      <div class="report">
        <h4>完整报告:</h4>
        <div v-html="result.full_report"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const form = ref({
  symbol: '',
  trade_date: ''
})

const loading = ref(false)
const error = ref('')
const result = ref(null)

const analyzeStock = async () => {
  loading.value = true
  error.value = ''
  result.value = null

  try {
    const response = await axios.post('/api/analysis', {
      symbol: form.value.symbol,
      trade_date: form.value.trade_date || undefined
    })
    result.value = response.data
  } catch (err) {
    if (err.response) {
      error.value = err.response.data.detail || '分析失败'
    } else {
      error.value = '连接后端失败，请确保API服务器运行在 localhost:8000'
    }
  } finally {
    loading.value = false
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
.result {
  margin-top: 20px;
  text-align: left;
}
pre {
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  overflow: auto;
}
</style>
