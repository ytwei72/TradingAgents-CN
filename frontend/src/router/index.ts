import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import StockAnalyzeView from '../views/StockAnalyzeView.vue'
import AnalysisResultsView from '../views/AnalysisResults.vue'
import SystemConfigView from '../views/SystemConfig.vue'
import ModelUsageStatsView from '../views/ModelUsageStats.vue'
import AnalysisProcessView from '../views/AnalysisProcess.vue'
import OperationLogsView from '../views/TaskRunLogsOld.vue'
import TaskRunLogsView from '../views/TaskRunLogs.vue'
import BacktestView from '../views/Backtest.vue'
import BatchBacktestView from '../views/BatchBacktest.vue'
import CacheManagementView from '../views/CacheManagement.vue'
import FavoriteStocksView from '../views/FavoriteStocks.vue'

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
  },
  {
    path: '/operation-logs',
    name: 'OperationLogs',
    component: OperationLogsView
  },
  {
    path: '/task-run-logs',
    name: 'TaskRunLogs',
    component: TaskRunLogsView
  },
  {
    path: '/backtest',
    name: 'Backtest',
    component: BacktestView
  },
  {
    path: '/batch-backtest',
    name: 'BatchBacktest',
    component: BatchBacktestView
  },
  {
    path: '/cache-management',
    name: 'CacheManagement',
    component: CacheManagementView
  },
  {
    path: '/favorite-stocks',
    name: 'FavoriteStocks',
    component: FavoriteStocksView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
