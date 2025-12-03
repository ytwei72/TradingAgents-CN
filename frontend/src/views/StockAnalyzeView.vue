<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import { startAnalysis, getAnalysisStatus, getAnalysisResult, pauseAnalysis, resumeAnalysis, stopAnalysis, type AnalysisRequest } from '../api';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt();

// --- State & Form ---

const form = reactive({
  stock_symbol: '',
  analysis_date: new Date().toISOString().split('T')[0], // Default to today
  market_type: 'A股',
  research_depth: 3,
  analysts: ['market', 'fundamentals', 'news', 'risk'], // Default selection
  include_sentiment: true,
  include_risk_assessment: true,
  custom_prompt: ''
});

const marketOptions = ['A股', '港股', '美股'];
const analystOptions = [
  { value: 'market', label: '市场分析师' },
  { value: 'fundamentals', label: '基本面分析师' },
  { value: 'news', label: '新闻分析师' },
  { value: 'social', label: '社交媒体分析师' },
  { value: 'risk', label: '风险控制分析师' }, // Added based on typical roles
];

const loading = ref(false);
const analysisId = ref<string | null>(null);
const status = ref<string>('');
const progressLog = ref<any[]>([]);
const result = ref<any>(null);
const error = ref<string | null>(null);
const showAdvanced = ref(false);

// --- API Interactions ---

const start = async () => {
  if (!form.stock_symbol) return;
  
  loading.value = true;
  error.value = null;
  result.value = null;
  progressLog.value = [];
  
  // Map form to API request
  const apiRequest: AnalysisRequest = {
    stock_symbol: form.stock_symbol,
    market_type: form.market_type,
    analysts: form.analysts,
    research_depth: Number(form.research_depth),
    include_sentiment: form.include_sentiment,
    include_risk_assessment: form.include_risk_assessment,
    custom_prompt: form.custom_prompt
  };

  try {
    const res = await startAnalysis(apiRequest);
    analysisId.value = res.analysis_id;
    status.value = res.status;
    pollStatus();
  } catch (e: any) {
    error.value = e.message || '启动分析失败';
    loading.value = false;
  }
};

const pollStatus = async () => {
  if (!analysisId.value) return;
  
  const interval = setInterval(async () => {
    if (!analysisId.value) {
        clearInterval(interval);
        return;
    }

    try {
      const res = await getAnalysisStatus(analysisId.value!);
      status.value = res.status;
      progressLog.value = res.progress_log || [];
      
      if (res.status === 'completed') {
        clearInterval(interval);
        const resData = await getAnalysisResult(analysisId.value!);
        result.value = resData;
        loading.value = false;
      } else if (res.status === 'failed' || res.status === 'stopped' || res.status === 'cancelled') {
        clearInterval(interval);
        if (res.status === 'failed') {
            error.value = res.error || '分析失败';
        }
        loading.value = false;
      }
    } catch (e) {
      console.error(e);
    }
  }, 2000);
};

const pause = async () => {
    if (!analysisId.value) return;
    try {
        await pauseAnalysis(analysisId.value);
        status.value = 'paused';
    } catch (e: any) {
        error.value = e.message || '暂停失败';
    }
};

const resume = async () => {
    if (!analysisId.value) return;
    try {
        await resumeAnalysis(analysisId.value);
        status.value = 'running';
    } catch (e: any) {
        error.value = e.message || '恢复失败';
    }
};

const stop = async () => {
    if (!analysisId.value) return;
    try {
        await stopAnalysis(analysisId.value);
        status.value = 'stopped';
        loading.value = false;
    } catch (e: any) {
        error.value = e.message || '停止失败';
    }
};

// --- Computed ---

const renderedReport = computed(() => {
  if (!result.value) return '';
  
  let report = '';
  if (result.value.decision) {
      report += `## 投资决策: ${result.value.decision.action}\n\n`;
      report += `**置信度:** ${result.value.decision.confidence}\n\n`;
      report += `**决策理由:**\n${result.value.decision.reasoning}\n\n`;
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

// Helper to format logs into "steps" if possible, or just list them
const formattedLogs = computed(() => {
    return progressLog.value.map((log, index) => {
        // Try to extract "Stage X" or similar if present, otherwise default
        const timestamp = log.timestamp ? log.timestamp.split('T')[1].split('.')[0] : '';
        return {
            id: index,
            message: log.message,
            timestamp: timestamp,
            status: 'completed' // Assume completed for past logs
        };
    }).reverse(); // Show newest first or keep chronological? Image shows chronological top-down usually.
    // Actually, let's keep chronological (oldest first) as per typical process steps
});

</script>

<template>
  <div class="flex h-screen bg-[#0f172a] text-gray-100 font-sans overflow-hidden">
    
    <!-- Sidebar -->
    <aside class="w-64 bg-[#1e293b] border-r border-gray-700 flex flex-col">
      <div class="p-6 flex items-center space-x-3 border-b border-gray-700">
        <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">L</div>
        <div>
            <div class="font-bold">Li Ming</div>
            <div class="text-xs text-gray-400">businessman</div>
        </div>
      </div>
      
      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        <a href="#" class="flex items-center space-x-3 px-4 py-3 bg-blue-600 rounded-lg text-white shadow-lg shadow-blue-900/50">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path></svg>
            <span>股票分析</span>
        </a>
        <a href="#" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            <span>配置管理</span>
        </a>
        <a href="#" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path></svg>
            <span>缓存管理</span>
        </a>
         <a href="#" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>Token统计</span>
        </a>
         <a href="#" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
            <span>操作日志</span>
        </a>
        <a href="#" class="flex items-center space-x-3 px-4 py-3 text-gray-400 hover:bg-gray-800 hover:text-white rounded-lg transition">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
            <span>分析结果</span>
        </a>
      </nav>
      
      <div class="p-4 border-t border-gray-700">
         <div class="flex items-center space-x-3 text-gray-400">
             <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
             <span>系统状态</span>
         </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-8">
      <header class="flex justify-between items-center mb-8">
        <h1 class="text-2xl font-bold text-white">投资顾问协同分析平台</h1>
        <div class="flex items-center space-x-4">
            <button class="text-gray-400 hover:text-white"><svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"></path></svg></button>
            <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white text-sm">L</div>
        </div>
      </header>

      <div class="space-y-6 max-w-5xl mx-auto">
        
        <!-- Configuration Panel -->
        <section class="bg-[#1e293b] rounded-xl p-6 shadow-lg border border-gray-700">
          <div class="flex items-center mb-6">
            <svg class="w-6 h-6 text-gray-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
            <h2 class="text-xl font-semibold text-white">分析配置</h2>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label class="block text-sm text-gray-400 mb-2">股票代码 <span class="text-gray-600 text-xs ml-1">?</span></label>
              <input v-model="form.stock_symbol" type="text" placeholder="输入A股代码，如000001, 600519" class="w-full bg-[#0f172a] border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" />
            </div>
            <div>
              <label class="block text-sm text-gray-400 mb-2">分析日期 <span class="text-gray-600 text-xs ml-1">?</span></label>
              <input v-model="form.analysis_date" type="date" class="w-full bg-[#0f172a] border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
             <div>
              <label class="block text-sm text-gray-400 mb-2">选择版本 <span class="text-blue-500 text-xs ml-1">✓</span></label>
              <div class="relative">
                <select v-model="form.market_type" class="w-full bg-[#0f172a] border border-gray-600 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 appearance-none">
                  <option v-for="m in marketOptions" :key="m" :value="m">{{ m }}</option>
                </select>
                <div class="absolute inset-y-0 right-0 flex items-center px-4 pointer-events-none text-gray-400">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                </div>
              </div>
            </div>
            <div>
               <div class="flex justify-between mb-2">
                  <label class="block text-sm text-gray-400">研究深度 <span class="text-gray-600 text-xs ml-1">?</span></label>
                  <span class="text-blue-400 text-sm">{{ form.research_depth }}级 标准分析</span>
               </div>
               <input v-model="form.research_depth" type="range" min="1" max="5" class="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500" />
            </div>
          </div>

          <div class="mb-6">
             <label class="block text-sm font-bold text-white mb-4 flex items-center">
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
                选择分析师团队
             </label>
             <div class="grid grid-cols-2 gap-4">
                <label v-for="analyst in analystOptions" :key="analyst.value" class="flex items-center space-x-3 cursor-pointer p-3 rounded hover:bg-gray-800 transition">
                   <div class="relative flex items-center">
                      <input type="checkbox" :value="analyst.value" v-model="form.analysts" class="peer h-5 w-5 cursor-pointer appearance-none rounded-full border border-gray-500 checked:border-blue-500 checked:bg-blue-500 transition-all" />
                      <svg class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white opacity-0 peer-checked:opacity-100 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="3"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg>
                   </div>
                   <span class="text-gray-300">{{ analyst.label }}</span>
                   <span class="text-gray-600 text-xs">?</span>
                </label>
             </div>
          </div>

          <!-- Warning/Info Box -->
          <div v-if="form.market_type === 'A股'" class="bg-yellow-900/30 border-l-4 border-yellow-600 p-4 mb-6">
             <p class="text-yellow-500 text-sm">A股市场暂不支持社交媒体分析，因为国内数据源限制</p>
          </div>
          
          <div class="bg-green-900/20 border-l-4 border-green-600 p-4 mb-6">
             <p class="text-green-400 text-sm">已选择{{ form.analysts.length }}个分析师: {{ form.analysts.map(a => analystOptions.find(opt => opt.value === a)?.label).join(', ') }}</p>
          </div>

          <!-- Advanced Options Toggle -->
          <div class="border-t border-gray-700 pt-4">
             <button @click="showAdvanced = !showAdvanced" class="flex items-center justify-between w-full text-left text-white font-semibold">
                <span>高级选项</span>
                <svg class="w-5 h-5 transform transition-transform" :class="{'rotate-180': showAdvanced}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
             </button>
             
             <div v-if="showAdvanced" class="mt-4 space-y-3">
                <label class="flex items-center space-x-3 cursor-pointer">
                   <input type="checkbox" v-model="form.include_sentiment" class="form-checkbox h-4 w-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500">
                   <span class="text-gray-300">包含情绪分析</span>
                   <span class="text-gray-600 text-xs">?</span>
                </label>
                <label class="flex items-center space-x-3 cursor-pointer">
                   <input type="checkbox" v-model="form.include_risk_assessment" class="form-checkbox h-4 w-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500">
                   <span class="text-gray-300">包含风险评估</span>
                   <span class="text-gray-600 text-xs">?</span>
                </label>
             </div>
          </div>
          
          <div class="mt-8 flex justify-end">
             <button @click="start" :disabled="loading || !form.stock_symbol" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-8 rounded-lg shadow-lg shadow-blue-900/50 transition duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center">
                <span v-if="loading" class="animate-spin mr-2">⟳</span>
                {{ loading ? '分析中...' : '开始分析' }}
             </button>
          </div>
        </section>

        <!-- Analysis Process / Results -->
        <section v-if="analysisId || result" class="bg-[#1e293b] rounded-xl p-6 shadow-lg border border-gray-700">
           <div class="flex items-center justify-between mb-6 border-b border-gray-700 pb-4">
              <h2 class="text-xl font-semibold text-white flex items-center">
                 <span class="mr-2">📄</span>
                 {{ form.stock_symbol }} - 详细分析步骤日志
              </h2>
              <div class="flex items-center space-x-4">
                 <div class="text-sm text-gray-400">分析ID: <span class="font-mono text-gray-300">{{ analysisId }}</span></div>
                 <div class="flex items-center space-x-2">
                    <span class="text-sm text-gray-400">状态:</span>
                    <span class="px-2 py-0.5 rounded text-xs font-bold uppercase" 
                        :class="{
                            'bg-green-900 text-green-300': status === 'completed',
                            'bg-blue-900 text-blue-300': status === 'running',
                            'bg-red-900 text-red-300': status === 'failed' || status === 'stopped',
                            'bg-yellow-900 text-yellow-300': status === 'paused'
                        }">
                        {{ status }}
                    </span>
                 </div>
              </div>
           </div>

           <!-- Progress Steps Visualization -->
           <div class="space-y-3 mb-8">
              <div v-for="log in formattedLogs" :key="log.id" class="bg-[#f0fdf4] border border-green-200 rounded p-3 flex items-start">
                 <div class="mr-3 mt-1">
                    <svg class="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                 </div>
                 <div class="flex-1">
                    <div class="flex justify-between items-center mb-1">
                       <h3 class="font-bold text-gray-800 text-sm">{{ log.message }}</h3>
                       <span class="text-xs text-gray-500 flex items-center">
                          <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                          {{ log.timestamp }}
                       </span>
                    </div>
                    <p class="text-xs text-gray-600">已完成 - 状态: complete</p>
                 </div>
                 <div class="ml-2">
                    <span class="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded">已完成</span>
                 </div>
              </div>
              
              <!-- Loading State for next step -->
              <div v-if="status === 'running'" class="bg-blue-50 border border-blue-200 rounded p-3 flex items-start animate-pulse">
                 <div class="mr-3 mt-1">
                    <div class="w-5 h-5 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
                 </div>
                 <div class="flex-1">
                    <h3 class="font-bold text-gray-800 text-sm">正在执行下一步骤...</h3>
                    <p class="text-xs text-gray-600">系统正在处理中</p>
                 </div>
              </div>
           </div>

           <!-- Final Report -->
           <div v-if="result" class="mt-8 border-t border-gray-700 pt-6">
              <h3 class="text-lg font-bold text-white mb-4">分析报告结果</h3>
              <div class="prose prose-invert max-w-none bg-gray-900 p-6 rounded-lg border border-gray-700" v-html="renderedReport"></div>
           </div>
        </section>

      </div>
    </main>
  </div>
</template>

<style scoped>
/* Custom Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: #1e293b; 
}
::-webkit-scrollbar-thumb {
  background: #475569; 
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #64748b; 
}
</style>
