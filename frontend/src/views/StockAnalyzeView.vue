<script setup lang="ts">
import { ref, reactive, computed, onUnmounted, watch } from 'vue';
import { startAnalysis, getAnalysisStatus, getAnalysisResult, pauseAnalysis, resumeAnalysis, stopAnalysis, getPlannedSteps, getAnalysisHistory, type AnalysisRequest } from '../api';
import MarkdownIt from 'markdown-it';
import ReportComponent from '../components/ReportComponent.vue';

const md = new MarkdownIt();

// --- State & Form ---

const form = reactive({
  stock_symbol: '',
  analysis_date: new Date().toISOString().split('T')[0], // Default to today
  market_type: 'A股',
  research_depth: 3,
  analysts: ['market', 'fundamentals', 'news'], // Default selection
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
const analysisId = ref<string | null>('c870901e-643b-4cd3-a81a-da67b73acb9d');
const status = ref<string>('');
const progressLog = ref<any[]>([]);
const taskProgress = ref<any>(null); // Store detailed progress info
const result = ref<any>(null);
const error = ref<string | null>(null);
const showAdvanced = ref(false);

const plannedSteps = ref<any[]>([]);
const historySteps = ref<any[]>([]);
const showHistory = ref(false); // For accordion toggle
const showReportResult = ref(false); // For report result accordion toggle, default collapsed
const showResearchReport = ref(false); // For research report accordion toggle, default collapsed

// Task Control State
const autoRefresh = ref(true);
const pollingTimer = ref<any>(null);
const ws = ref<WebSocket | null>(null);

// --- WebSocket Logic ---

const connectWebSocket = () => {
    if (ws.value) return; // Already connected

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = 'localhost:8000'; // Assuming backend is on 8000, adjust if needed
    const wsUrl = `${protocol}//${host}/ws/notifications`;

    ws.value = new WebSocket(wsUrl);

    ws.value.onopen = () => {
        console.log('WebSocket Connected');
        // Send heartbeat
        setInterval(() => {
            if (ws.value && ws.value.readyState === WebSocket.OPEN) {
                ws.value.send('ping');
            }
        }, 30000);
    };

    ws.value.onmessage = (event) => {
        if (event.data === 'pong') return;

        // If Auto Refresh is ON, ignore WS messages for state update
        if (autoRefresh.value) return;

        try {
            const data = JSON.parse(event.data);
            if (data.topic === 'task/progress' && data.payload) {
                const payload = data.payload;
                
                // Only update if it matches current analysisId
                if (payload.analysis_id !== analysisId.value) return;

                // Update status if provided (infer from message or payload if available)
                if (status.value !== 'running' && status.value !== 'paused') {
                     status.value = 'running';
                }

                // Add to progress log
                const newLog = {
                    message: payload.message,
                    step: payload.current_step,
                    timestamp: data.timestamp || new Date().toISOString()
                };
                
                progressLog.value.push(newLog);

                if (payload.status) {
                    status.value = payload.status;
                    if (payload.status === 'completed') {
                         handleCompletion();
                    } else if (payload.status === 'failed') {
                         handleFailure(payload.error || 'Unknown error');
                    }
                }
            }
        } catch (e) {
            console.error('Error parsing WS message:', e);
        }
    };

    ws.value.onclose = () => {
        console.log('WebSocket Disconnected');
        ws.value = null;
    };

    ws.value.onerror = (err) => {
        console.error('WebSocket Error:', err);
    };
};

const disconnectWebSocket = () => {
    if (ws.value) {
        ws.value.close();
        ws.value = null;
    }
};

// --- API Interactions ---

const start = async () => {
  if (!form.stock_symbol) return;
  
  loading.value = true;
  error.value = null;
  result.value = null;
  progressLog.value = [];
  taskProgress.value = null;
  
  // Map form to API request
  const apiRequest: AnalysisRequest = {
    stock_symbol: form.stock_symbol,
    analysis_date: form.analysis_date,
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
    
    // Connect WS immediately
    connectWebSocket();

    // Fetch planned steps
    try {
        const stepsData = await getPlannedSteps(analysisId.value!);
        plannedSteps.value = stepsData.steps || [];
        showHistory.value = true; // Auto-expand history/plan
    } catch (e) {
        console.error("Failed to fetch planned steps", e);
    }

    // Initial check: if autoRefresh is true, start polling.
    // If false, we rely on WS (which is connected).
    if (autoRefresh.value) {
        startPolling();
    }
  } catch (e: any) {
    error.value = e.message || '启动分析失败';
    loading.value = false;
  }
};

const startPolling = () => {
  if (pollingTimer.value) clearInterval(pollingTimer.value);
  
  pollingTimer.value = setInterval(async () => {
    if (!analysisId.value) {
        stopPolling();
        return;
    }
    
    // Double check autoRefresh, though watcher handles it too
    if (!autoRefresh.value) return; 

    try {
      const res = await getAnalysisStatus(analysisId.value!);
      status.value = res.status;
      progressLog.value = res.progress_log || [];
      taskProgress.value = res.progress; // Update detailed progress
      
      // Fetch history
      try {
          const history = await getAnalysisHistory(analysisId.value!);
          historySteps.value = history;
      } catch (e) {
          console.error("Failed to fetch history", e);
      }

      if (res.status === 'completed') {
        handleCompletion();
      } else if (res.status === 'failed' || res.status === 'stopped' || res.status === 'cancelled') {
        handleFailure(res.error);
      }
    } catch (e) {
      console.error(e);
    }
  }, 3000); // Changed to 3s as per requirement
};

const stopPolling = () => {
    if (pollingTimer.value) {
        clearInterval(pollingTimer.value);
        pollingTimer.value = null;
    }
};

const handleCompletion = async () => {
    stopPolling();
    // disconnectWebSocket(); // Optional: keep open for other notifications?
    status.value = 'completed';
    try {
        const resData = await getAnalysisResult(analysisId.value!);
        result.value = resData;
    } catch(e) {
        console.error(e);
    }
    loading.value = false;
};

const handleFailure = (errMsg?: string) => {
    stopPolling();
    status.value = 'failed'; // or stopped/cancelled
    if (errMsg) error.value = errMsg;
    loading.value = false;
};

// Watcher for Auto Refresh
watch(autoRefresh, (newVal) => {
    if (newVal) {
        // Turned ON: Start polling
        startPolling();
    } else {
        // Turned OFF: Stop polling
        stopPolling();
        // Ensure WS is connected (should be, but check)
        if (!ws.value && analysisId.value) {
            connectWebSocket();
        }
    }
});

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
    if (!confirm('确定要停止当前分析任务吗？此操作不可恢复。')) return;
    
    try {
        await stopAnalysis(analysisId.value);
        status.value = 'stopped';
        loading.value = false;
        stopPolling();
        disconnectWebSocket();
    } catch (e: any) {
        error.value = e.message || '停止失败';
    }
};

onUnmounted(() => {
    stopPolling();
    disconnectWebSocket();
});

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
const mergedSteps = computed(() => {
    if (plannedSteps.value.length === 0) {
        // Fallback to history if no plan available
        return historySteps.value.map(h => ({
            ...h,
            display_name: h.display_name || h.step_name,
            status: h.status || 'completed' // Default to completed if in history?
        }));
    }

    const historyMap = new Map(historySteps.value.map(s => [s.step_index, s]));
    
    return plannedSteps.value.map(plan => {
        const history = historyMap.get(plan.step_index);
        let status = 'pending';
        let startTime = plan.start_time;
        let elapsedTime = plan.elapsed_time;
        let errorMsg = '';
        // 优先使用历史记录中的描述（通常包含动态信息），如果没有则使用计划中的静态描述
        let description = plan.description || '';
        let message = '';
        
        if (history) {
            status = history.status;
            startTime = history.start_time;
            elapsedTime = history.elapsed_time;
            errorMsg = history.error;
            // 如果历史记录中有description，优先使用
            if (history.description) {
                description = history.description;
            }
            message = history.message;
        }
        
        return {
            ...plan,
            status: status,
            start_time: startTime,
            elapsed_time: elapsedTime,
            error: errorMsg,
            description: description,
            message: message
        };
    });
});

const completedCount = computed(() => mergedSteps.value.filter(s => s.status === 'completed').length);
const totalCount = computed(() => mergedSteps.value.length);

// Helper for formatting duration
const formatDuration = (seconds: number | undefined) => {
    if (seconds === undefined || seconds === null) return '-';
    if (seconds < 60) return `${seconds.toFixed(1)}秒`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = (seconds % 60).toFixed(1);
    return `${minutes}分${remainingSeconds}秒`;
};

// Helper for formatting time
const formatTime = (isoString: string | undefined) => {
    if (!isoString) return '-';
    try {
        return isoString.split('T')[1]?.split('.')[0] || isoString;
    } catch {
        return isoString;
    }
};

const getStepColorClass = (status: string) => {
    switch (status) {
        case 'running': return 'bg-blue-900/20 border-blue-500';
        case 'completed': return 'bg-green-900/20 border-green-500';
        case 'failed': 
        case 'error': return 'bg-red-900/20 border-red-500';
        case 'paused': return 'bg-yellow-900/20 border-yellow-500';
        case 'stopped': return 'bg-gray-700/50 border-gray-500';
        default: return 'bg-gray-800/50 border-gray-600'; // pending
    }
};

const getStepBadgeClass = (status: string) => {
    switch (status) {
        case 'running': return 'bg-blue-600 text-white';
        case 'completed': return 'bg-green-600 text-white';
        case 'failed': 
        case 'error': return 'bg-red-600 text-white';
        case 'paused': return 'bg-yellow-600 text-white';
        case 'stopped': return 'bg-gray-600 text-white';
        default: return 'bg-gray-700 text-gray-300';
    }
};

const getStepIcon = (status: string) => {
     switch (status) {
        case 'running': return '🔄'; 
        case 'completed': return '✅';
        case 'failed': 
        case 'error': return '❌';
        case 'paused': return '⏸';
        case 'stopped': return '⏹';
        default: return '⏳';
    }
};

const getStatusText = (status: string) => {
     switch (status) {
        case 'running': return '执行中'; 
        case 'completed': return '已完成';
        case 'failed': 
        case 'error': return '失败';
        case 'paused': return '已暂停';
        case 'stopped': return '已停止';
        default: return '等待执行';
    }
};

</script>

<template>
  <div class="space-y-8">
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
           <div class="flex flex-col md:flex-row md:items-center justify-between mb-6 border-b border-gray-700 pb-4 gap-4">
              <div class="flex items-center">
                 <h2 class="text-xl font-semibold text-white flex items-center mr-4">
                    <span class="mr-2">📄</span>
                    {{ form.stock_symbol }} - 详细分析步骤日志
                 </h2>
                 <div class="flex items-center space-x-2">
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
              
              <div class="flex items-center space-x-4 flex-wrap gap-y-2">
                 <!-- Auto Refresh Toggle -->
                 <label class="flex items-center space-x-2 cursor-pointer select-none">
                    <div class="relative">
                       <input type="checkbox" v-model="autoRefresh" class="sr-only peer">
                       <div class="w-9 h-5 bg-gray-600 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
                    </div>
                    <span class="text-sm text-gray-300">定时刷新</span>
                 </label>

                 <!-- Control Buttons -->
                 <div class="flex items-center space-x-2">
                    <button v-if="status === 'running'" @click="pause" class="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded transition flex items-center">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        暂停
                    </button>
                    <button v-if="status === 'paused'" @click="resume" class="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded transition flex items-center">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        继续
                    </button>
                    <button v-if="status === 'running' || status === 'paused'" @click="stop" class="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded transition flex items-center">
                        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"></path></svg>
                        停止
                    </button>
                 </div>
              </div>
           </div>

           <!-- Task History Accordion -->
           <div class="mb-8 border border-gray-700 rounded-lg overflow-hidden">
              <button @click="showHistory = !showHistory" class="w-full px-4 py-3 bg-gray-800 hover:bg-gray-750 flex justify-between items-center transition">
                  <div class="flex items-center space-x-3">
                      <span class="font-bold text-white">任务执行步骤</span>
                      <span class="text-xs px-2 py-0.5 rounded-full bg-gray-700 text-gray-300">{{ completedCount }}/{{ totalCount }}</span>
                  </div>
                  <svg class="w-5 h-5 text-gray-400 transform transition-transform" :class="{'rotate-180': showHistory}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
              </button>
              
              <div v-if="showHistory" class="p-4 bg-[#0f172a] space-y-4 max-h-[600px] overflow-y-auto">
                  <!-- Task Summary Info -->
                  <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div class="bg-gray-800/50 p-3 rounded border border-gray-700">
                         <div class="text-xs text-gray-400 mb-1">总计步骤</div>
                         <div class="font-bold text-xl text-white">{{ taskProgress?.total_steps || totalCount }}</div>
                      </div>
                      <div class="bg-gray-800/50 p-3 rounded border border-gray-700">
                         <div class="text-xs text-gray-400 mb-1">已完成</div>
                         <div class="font-bold text-xl text-blue-400">{{ taskProgress?.current_step || completedCount }}</div>
                      </div>
                       <div class="bg-gray-800/50 p-3 rounded border border-gray-700">
                         <div class="text-xs text-gray-400 mb-1">已运行时间</div>
                         <div class="font-bold text-xl text-green-400">{{ formatDuration(taskProgress?.elapsed_time) }}</div>
                      </div>
                       <div class="bg-gray-800/50 p-3 rounded border border-gray-700">
                         <div class="text-xs text-gray-400 mb-1">预计剩余</div>
                         <div class="font-bold text-xl text-yellow-400">{{ formatDuration(taskProgress?.remaining_time) }}</div>
                      </div>
                  </div>

                  <!-- Step List -->
                  <div v-for="step in mergedSteps" :key="step.step_index" 
                       class="step-card p-3 rounded border-l-4 transition-all duration-300"
                       :class="getStepColorClass(step.status)">
                       
                       <div class="flex justify-between items-start mb-2">
                           <div class="flex items-center space-x-2">
                               <div class="text-lg">{{ getStepIcon(step.status) }}</div>
                               <div>
                                   <div class="font-bold text-sm text-white flex items-center">
                                       {{ step.display_name || step.step_name }}
                                       <span class="ml-2 text-[10px] px-1.5 py-0.5 rounded-full" :class="getStepBadgeClass(step.status)">
                                           {{ getStatusText(step.status) }}
                                       </span>
                                   </div>
                                   <div v-if="step.phase === 'debate'" class="text-xs text-gray-400 mt-0.5">
                                       第{{ step.round }}轮 - {{ step.role }}
                                   </div>
                               </div>
                           </div>
                           
                           <div class="text-right">
                               <div class="text-xs text-gray-400">🕐 {{ formatTime(step.start_time) }}</div>
                               <div class="text-xs font-mono text-gray-500 mt-0.5">📊 用时: {{ formatDuration(step.elapsed_time) }}</div>
                           </div>
                       </div>
                       
                       <div class="text-xs text-gray-300 pl-7 whitespace-pre-wrap leading-relaxed">
                           {{ step.description || step.message || step.display_name + '...' }}
                           <div v-if="step.error" class="text-red-400 mt-1">
                               错误信息: {{ step.error }}
                           </div>
                       </div>
                  </div>
                  
                  <div v-if="mergedSteps.length === 0" class="text-center text-gray-500 py-4">
                      暂无步骤信息
                  </div>
              </div>
           </div>

           <!-- Live Logs (Optional, keep if needed for detailed messages) -->
           <div v-if="progressLog.length > 0" class="space-y-2 mb-8">
               <h3 class="text-sm font-bold text-gray-400 mb-2">实时日志</h3>
               <div class="bg-black/30 rounded p-4 max-h-40 overflow-y-auto font-mono text-xs text-gray-300 space-y-1">
                   <div v-for="(log, idx) in progressLog.slice().reverse()" :key="idx">
                       <span class="text-gray-500">[{{ log.timestamp ? log.timestamp.split('T')[1].split('.')[0] : '' }}]</span>
                       {{ log.message }}
                   </div>
               </div>
           </div>

           <!-- Final Report (Collapsible) -->
           <div v-if="result" class="mt-8 border-t border-gray-700 pt-6">
              <button 
                @click="showReportResult = !showReportResult" 
                class="w-full flex items-center justify-between text-left mb-4 hover:bg-gray-800/50 p-3 rounded-lg transition"
              >
                 <h3 class="text-lg font-bold text-white">分析报告结果</h3>
                 <svg 
                   class="w-5 h-5 text-gray-400 transform transition-transform" 
                   :class="{'rotate-180': showReportResult}" 
                   fill="none" 
                   stroke="currentColor" 
                   viewBox="0 0 24 24"
                 >
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                 </svg>
              </button>
              <div v-if="showReportResult" class="prose prose-invert max-w-none bg-gray-900 p-6 rounded-lg border border-gray-700" v-html="renderedReport"></div>
           </div>

           <!-- Research Report Component -->
           <div class="mt-8 border-t border-gray-700 pt-6">
              <button 
                @click="showResearchReport = !showResearchReport" 
                class="w-full flex items-center justify-between text-left mb-4 hover:bg-gray-800/50 p-3 rounded-lg transition"
              >
                 <h3 class="text-lg font-bold text-white">研究报告</h3>
                 <svg 
                   class="w-5 h-5 text-gray-400 transform transition-transform" 
                   :class="{'rotate-180': showResearchReport}" 
                   fill="none" 
                   stroke="currentColor" 
                   viewBox="0 0 24 24"
                 >
                   <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                 </svg>
              </button>
              <div v-if="showResearchReport" class="prose prose-invert max-w-none bg-gray-900 p-6 rounded-lg border border-gray-700">
                <ReportComponent :analysisId="analysisId || ''" />
              </div>
           </div>
        </section>

    </div>
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
