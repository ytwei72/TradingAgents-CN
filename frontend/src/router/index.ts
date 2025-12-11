import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import StockAnalyzeView from '../views/StockAnalyzeView.vue'
import AnalysisResultsView from '../views/AnalysisResults.vue'
import SystemConfigView from '../views/SystemConfig.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
