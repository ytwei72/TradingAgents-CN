<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getReportsList, type ReportListItem } from '../api/index.ts'

const reports = ref<ReportListItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 10
const pages = ref(0)
const loading = ref(false)

const fetchReports = async (page: number = 1) => {
  loading.value = true
  try {
    const response = await getReportsList(page, pageSize)
    if (response.success) {
      reports.value = response.data.reports
      total.value = response.data.total
      pages.value = response.data.pages
      currentPage.value = page
    }
  } catch (error) {
    console.error('Failed to fetch reports:', error)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

const formatDecision = (decision: any) => {
  if (!decision) return 'N/A'
  return `${decision.recommendation || 'N/A'} (${decision.confidence || 0}%)`
}

const handlePageChange = (page: number) => {
  if (page >= 1 && page <= pages.value) {
    fetchReports(page)
  }
}

onMounted(() => {
  fetchReports()
})
</script>

<template>
  <div class="space-y-6">
    <header class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-white">分析结果</h1>
      <div class="text-sm text-gray-400">
        总计 {{ total }} 个报告
      </div>
    </header>

    <div v-if="loading" class="flex justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
    </div>

    <div v-else-if="reports.length === 0" class="text-center py-12 text-gray-400">
      <p>暂无分析报告</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <div v-for="report in reports" :key="report.analysis_id" class="bg-[#1e293b] rounded-lg p-6 border border-gray-700 shadow-lg hover:shadow-blue-900/20 transition-shadow">
        <div class="flex justify-between items-start mb-4">
          <div class="flex items-center space-x-2">
            <h3 class="font-bold text-white truncate">{{ report.stock_symbol }}</h3>
            <span class="px-2 py-1 rounded text-xs font-bold uppercase" :class="{
              'bg-green-900 text-green-300': report.status === 'completed',
              'bg-blue-900 text-blue-300': report.status === 'running',
              'bg-red-900 text-red-300': report.status === 'failed'
            }">
              {{ report.status }}
            </span>
          </div>
          <div class="text-right">
            <div class="text-sm font-semibold text-blue-400">{{ report.research_depth }}/5</div>
            <div class="text-xs text-gray-400">{{ formatDate(report.analysis_date) }}</div>
          </div>
        </div>

        <p class="text-gray-300 text-sm mb-4 line-clamp-3">{{ report.summary }}</p>

        <div class="space-y-2 text-xs text-gray-400 mb-4">
          <div>分析师: {{ report.analysts.join(', ') }}</div>
          <div>决策: {{ formatDecision(report.formatted_decision) }}</div>
          <div class="text-gray-500">更新时间: {{ formatDate(report.updated_at) }}</div>
        </div>

        <div class="flex justify-end">
          <button class="text-blue-400 hover:text-blue-300 text-sm">查看详情</button>
        </div>
      </div>
    </div>

    <div v-if="pages > 1" class="flex justify-center items-center space-x-2 mt-8">
      <button 
        @click="handlePageChange(currentPage - 1)" 
        :disabled="currentPage === 1"
        class="px-3 py-1 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        :class="currentPage === 1 ? 'bg-gray-700 text-gray-400' : 'bg-blue-600 hover:bg-blue-700 text-white'"
      >
        上一页
      </button>

      <button 
        v-for="page in Math.min(5, pages)" 
        :key="page"
        @click="handlePageChange(page)"
        class="px-3 py-1 rounded text-sm"
        :class="page === currentPage ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
      >
        {{ page }}
      </button>

      <span v-if="pages > 5" class="px-3 py-1 text-gray-400">...</span>

      <button 
        v-if="pages > 5"
        @click="handlePageChange(pages)"
        class="px-3 py-1 rounded text-sm bg-gray-700 text-gray-300 hover:bg-gray-600"
      >
        {{ pages }}
      </button>

      <button 
        @click="handlePageChange(currentPage + 1)" 
        :disabled="currentPage === pages"
        class="px-3 py-1 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        :class="currentPage === pages ? 'bg-gray-700 text-gray-400' : 'bg-blue-600 hover:bg-blue-700 text-white'"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
