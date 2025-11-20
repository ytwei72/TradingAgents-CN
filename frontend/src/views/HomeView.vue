<script setup lang="ts">
import { ref, reactive, computed } from 'vue';
import { startAnalysis, getAnalysisStatus, getAnalysisResult, type AnalysisRequest } from '../api';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt();

const form = reactive<AnalysisRequest>({
  stock_symbol: '',
  market_type: '美股',
  analysts: ['market', 'fundamentals'],
  research_depth: 3,
  include_sentiment: true,
  include_risk_assessment: true,
  custom_prompt: ''
});

const loading = ref(false);
const analysisId = ref<string | null>(null);
const status = ref<string>('');
const progressLog = ref<any[]>([]);
const result = ref<any>(null);
const error = ref<string | null>(null);

const marketOptions = ['美股', 'A股', '港股'];
const analystOptions = [
  { value: 'market', label: 'Market Analyst' },
  { value: 'fundamentals', label: 'Fundamentals Analyst' },
  { value: 'news', label: 'News Analyst' },
  { value: 'social', label: 'Social Media Analyst' }
];

const start = async () => {
  if (!form.stock_symbol) return;
  
  loading.value = true;
  error.value = null;
  result.value = null;
  progressLog.value = [];
  
  try {
    const res = await startAnalysis(form);
    analysisId.value = res.analysis_id;
    status.value = res.status;
    pollStatus();
  } catch (e: any) {
    error.value = e.message || 'Failed to start analysis';
    loading.value = false;
  }
};

const pollStatus = async () => {
  if (!analysisId.value) return;
  
  const interval = setInterval(async () => {
    try {
      const res = await getAnalysisStatus(analysisId.value!);
      status.value = res.status;
      progressLog.value = res.progress_log || [];
      
      if (res.status === 'completed') {
        clearInterval(interval);
        const resData = await getAnalysisResult(analysisId.value!);
        result.value = resData;
        loading.value = false;
      } else if (res.status === 'failed') {
        clearInterval(interval);
        error.value = res.error || 'Analysis failed';
        loading.value = false;
      }
    } catch (e) {
      console.error(e);
    }
  }, 2000);
};

const renderedReport = computed(() => {
  if (!result.value) return '';
  // Depending on result structure, render the report
  // Assuming result has a 'decision' object with 'reasoning' or similar
  // Or if it returns the full state, we look for reports
  
  let report = '';
  if (result.value.decision) {
      report += `## Decision: ${result.value.decision.action}\n\n`;
      report += `**Confidence:** ${result.value.decision.confidence}\n\n`;
      report += `**Reasoning:**\n${result.value.decision.reasoning}\n\n`;
  }
  
  if (result.value.state) {
      const state = result.value.state;
      if (state.market_report) report += `${state.market_report}\n\n`;
      if (state.fundamentals_report) report += `${state.fundamentals_report}\n\n`;
      if (state.news_report) report += `${state.news_report}\n\n`;
      if (state.sentiment_report) report += `${state.sentiment_report}\n\n`;
      if (state.risk_assessment) report += `${state.risk_assessment}\n\n`;
      if (state.investment_plan) report += `${state.investment_plan}\n\n`;
  }
  
  return md.render(report);
});

</script>

<template>
  <div class="container mx-auto p-4 max-w-4xl">
    <header class="mb-8 text-center">
      <h1 class="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-600">
        TradingAgents AI Analyst
      </h1>
      <p class="text-gray-400 mt-2">Professional Multi-Agent Stock Analysis</p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Configuration Panel -->
      <div class="md:col-span-1 space-y-6 bg-gray-800 p-6 rounded-xl shadow-lg h-fit">
        <h2 class="text-xl font-semibold mb-4">Configuration</h2>
        
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-400 mb-1">Market</label>
            <select v-model="form.market_type" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:border-blue-500">
              <option v-for="m in marketOptions" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-1">Stock Symbol</label>
            <input v-model="form.stock_symbol" type="text" placeholder="e.g. AAPL" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 focus:outline-none focus:border-blue-500 uppercase" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-1">Research Depth ({{ form.research_depth }})</label>
            <input v-model="form.research_depth" type="range" min="1" max="5" class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer" />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-400 mb-2">Analysts</label>
            <div class="space-y-2">
              <div v-for="analyst in analystOptions" :key="analyst.value" class="flex items-center">
                <input type="checkbox" :value="analyst.value" v-model="form.analysts" class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500">
                <label class="ml-2 text-sm text-gray-300">{{ analyst.label }}</label>
              </div>
            </div>
          </div>
          
          <button @click="start" :disabled="loading || !form.stock_symbol" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex justify-center items-center">
            <span v-if="loading" class="animate-spin mr-2">⟳</span>
            {{ loading ? 'Analyzing...' : 'Start Analysis' }}
          </button>
        </div>
      </div>

      <!-- Results & Progress Panel -->
      <div class="md:col-span-2 bg-gray-800 p-6 rounded-xl shadow-lg min-h-[500px]">
        <div v-if="!analysisId && !result" class="h-full flex flex-col items-center justify-center text-gray-500">
          <span class="text-6xl mb-4">📊</span>
          <p>Enter a stock symbol and start analysis to see results.</p>
        </div>

        <div v-else>
          <!-- Progress -->
          <div v-if="loading || (status && status !== 'completed')" class="mb-6">
            <h3 class="text-lg font-semibold mb-2 flex items-center">
              <span class="animate-pulse mr-2">●</span> Analysis in Progress
            </h3>
            <div class="bg-gray-900 rounded-lg p-4 font-mono text-sm h-48 overflow-y-auto border border-gray-700">
              <div v-for="(log, index) in progressLog" :key="index" class="mb-1 text-green-400">
                <span class="text-gray-500">[{{ log.timestamp.split('T')[1].split('.')[0] }}]</span> {{ log.message }}
              </div>
              <div v-if="progressLog.length === 0" class="text-gray-500 italic">Waiting for logs...</div>
            </div>
          </div>

          <!-- Error -->
          <div v-if="error" class="bg-red-900/50 border border-red-600 text-red-200 p-4 rounded-lg mb-6">
            <strong>Error:</strong> {{ error }}
          </div>

          <!-- Results -->
          <div v-if="result" class="prose prose-invert max-w-none">
            <div class="flex items-center justify-between mb-6 border-b border-gray-700 pb-4">
              <h2 class="text-2xl font-bold m-0">{{ result.stock_symbol }} Analysis Report</h2>
              <span class="px-3 py-1 rounded-full text-sm font-bold" 
                :class="{
                  'bg-green-600 text-white': result.decision?.action?.includes('买入') || result.decision?.action?.includes('Buy'),
                  'bg-red-600 text-white': result.decision?.action?.includes('卖出') || result.decision?.action?.includes('Sell'),
                  'bg-yellow-600 text-white': result.decision?.action?.includes('持有') || result.decision?.action?.includes('Hold')
                }">
                {{ result.decision?.action || 'Unknown' }}
              </span>
            </div>
            
            <div v-html="renderedReport"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
/* Custom scrollbar for logs */
::-webkit-scrollbar {
  width: 8px;
}
::-webkit-scrollbar-track {
  background: #1f2937; 
}
::-webkit-scrollbar-thumb {
  background: #4b5563; 
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #6b7280; 
}
</style>
