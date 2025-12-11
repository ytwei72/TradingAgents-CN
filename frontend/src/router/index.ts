import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import StockAnalyzeView from '../views/StockAnalyzeView.vue'
import AnalysisResultsView from '../views/AnalysisResults.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'StockAnalyze',
    component: () => import('../views/StockAnalyzeView.vue')
  },
  {
    path: '/analysis-results',
    name: 'AnalysisResults',
    component: () => import('../views/AnalysisResults.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
