<template>
  <div class="flex h-screen bg-[#0f172a] text-gray-100 font-sans overflow-hidden">
    <!-- Sidebar -->
    <aside class="w-56 bg-[#1e293b] border-r border-gray-700 flex flex-col">
      <div class="p-6 flex items-center space-x-3 border-b border-gray-700">
        <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">AR</div>
        <div>
          <div class="font-bold">Apex Research</div>
          <div class="text-xs text-gray-400">多智能体投资研究系统</div>
        </div>
      </div>
      
      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        <router-link 
          to="/" 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg transition"
          :class="route.path === '/' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
          </svg>
          <span>股票分析</span>
        </router-link>

        <router-link 
          to="/config" 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg transition"
          :class="route.path === '/config' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
          </svg>
          <span>配置管理</span>
        </router-link>

        <router-link 
          to="/cache-management" 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg transition"
          :class="route.path === '/cache-management' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"></path>
          </svg>
          <span>缓存管理</span>
        </router-link>

        <!-- System Logs Group -->
        <div>
          <button
            type="button"
            class="w-full flex items-center justify-between px-4 py-3 rounded-lg transition text-left border-l-4"
            :class="isSystemLogsActive ? 'border-blue-500 text-gray-100 font-semibold bg-transparent' : 'border-transparent text-gray-400 hover:bg-gray-800 hover:text-white'"
            @click="showSystemLogs = !showSystemLogs"
          >
            <div class="flex items-center space-x-3">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4h16v4H4zM4 10h16v10H4z"></path>
              </svg>
              <span>系统日志</span>
            </div>
            <svg
              class="w-4 h-4 transform transition-transform"
              :class="showSystemLogs ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <div v-if="showSystemLogs" class="mt-1 space-y-1 ml-6">
            <router-link 
              to="/model-usage-stats" 
              class="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition"
              :class="route.path === '/model-usage-stats' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span>用量统计</span>
            </router-link>

            <router-link 
              to="/operation-logs" 
              class="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition"
              :class="route.path === '/operation-logs' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              <span>运行日志-老</span>
            </router-link>

            <router-link 
              to="/task-run-logs" 
              class="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition"
              :class="route.path === '/task-run-logs' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
              </svg>
              <span>运行日志</span>
            </router-link>
          </div>
        </div>

        <router-link 
          to="/analysis-results" 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg transition"
          :class="route.path === '/analysis-results' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <span>分析结果</span>
        </router-link>

        <router-link 
          to="/analysis-process" 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg transition"
          :class="route.path === '/analysis-process' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
          </svg>
          <span>分析流程</span>
        </router-link>

        <router-link 
          to="/favorite-stocks" 
          class="flex items-center space-x-3 px-4 py-3 rounded-lg transition"
          :class="route.path === '/favorite-stocks' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z"></path>
          </svg>
          <span>自选股</span>
        </router-link>

        <!-- Backtest Group -->
        <div>
          <button
            type="button"
            class="w-full flex items-center justify-between px-4 py-3 rounded-lg transition text-left border-l-4"
            :class="isBacktestActive ? 'border-blue-500 text-gray-100 font-semibold bg-transparent' : 'border-transparent text-gray-400 hover:bg-gray-800 hover:text-white'"
            @click="showBacktest = !showBacktest"
          >
            <div class="flex items-center space-x-3">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"></path>
              </svg>
              <span>回测系统</span>
            </div>
            <svg
              class="w-4 h-4 transform transition-transform"
              :class="showBacktest ? 'rotate-90' : ''"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </button>

          <div v-if="showBacktest" class="mt-1 space-y-1 ml-6">
            <router-link 
              to="/backtest" 
              class="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition"
              :class="route.path === '/backtest' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
              </svg>
              <span>单项回测</span>
            </router-link>

            <router-link 
              to="/batch-backtest" 
              class="flex items-center space-x-3 px-3 py-2 rounded-lg text-sm transition"
              :class="route.path === '/batch-backtest' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/50' : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7"></path>
              </svg>
              <span>批量回测</span>
            </router-link>
          </div>
        </div>

      </nav>

      <!-- Sidebar Footer -->
      <div class="p-4 border-t border-gray-700">
        <div class="text-xs text-gray-500 text-center">
          v0.2.0 · Apex Research Agent
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 overflow-y-auto p-8">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const systemLogsPaths = ['/model-usage-stats', '/operation-logs', '/task-run-logs']
const showSystemLogs = ref(systemLogsPaths.includes(route.path))
const isSystemLogsActive = computed(() => systemLogsPaths.includes(route.path))

const backtestPaths = ['/backtest', '/batch-backtest']
const showBacktest = ref(backtestPaths.includes(route.path))
const isBacktestActive = computed(() => backtestPaths.includes(route.path))
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* Custom scrollbar */
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
