import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import StockAnalyzeView from '../views/StockAnalyzeView.vue'
import AnalysisResultsView from '../views/AnalysisResults.vue'
import SystemConfigView from '../views/SystemConfig.vue'
import ModelUsageStatsView from '../views/ModelUsageStats.vue'
import AnalysisProcessView from '../views/AnalysisProcess.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'StockAnalyze',
    component: StockAnalyzeView
  },
  {
    path: '/analysis-results',
    name: 'AnalysisResults',
    component: AnalysisResultsView
  },
  {
    path: '/config',
    name: 'SystemConfig',
    component: SystemConfigView
  },
  {
    path: '/model-usage-stats',
    name: 'ModelUsageStats',
    component: ModelUsageStatsView
  },
  {
    path: '/analysis-process',
    name: 'AnalysisProcess',
    component: AnalysisProcessView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
