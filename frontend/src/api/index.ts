import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api', // Adjust if backend runs on different port
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface AnalysisRequest {
  stock_symbol: string;
  market_type: string;
  analysis_date?: string;
  analysts: string[];
  research_depth: number;
  include_sentiment?: boolean;
  include_risk_assessment?: boolean;
  custom_prompt?: string;
  extra_config?: Record<string, any>;
}

export interface AnalysisResponse {
  analysis_id: string;
  status: string;
  message: string;
}

export interface AnalysisStatus {
  analysis_id: string;
  status: string;
  current_message?: string;
  progress_log?: any[];
  progress?: any;
  error?: string;
}

export const startAnalysis = async (data: AnalysisRequest) => {
  const response = await api.post<AnalysisResponse>('/analysis/start', data);
  return response.data;
};

export const getAnalysisStatus = async (analysisId: string) => {
  const response = await api.get<AnalysisStatus>(`/analysis/${analysisId}/status`);
  return response.data;
};

export const getAnalysisResult = async (analysisId: string) => {
  const response = await api.get<any>(`/analysis/${analysisId}/result`);
  return response.data;
};

export const pauseAnalysis = async (analysisId: string) => {
  const response = await api.post<AnalysisResponse>(`/analysis/${analysisId}/pause`);
  return response.data;
};

export const resumeAnalysis = async (analysisId: string) => {
  const response = await api.post<AnalysisResponse>(`/analysis/${analysisId}/resume`);
  return response.data;
};

export const stopAnalysis = async (analysisId: string) => {
  const response = await api.post<AnalysisResponse>(`/analysis/${analysisId}/stop`);
  return response.data;
};

// Batch Analysis API
export interface BatchSameParamsRequest {
  stock_symbols: string[];
  market_type: string;
  analysis_date?: string;
  analysts: string[];
  research_depth: number;
  include_sentiment?: boolean;
  include_risk_assessment?: boolean;
  custom_prompt?: string;
  extra_config?: Record<string, any>;
}

export interface BatchTaskResult {
  stock_symbol: string;
  analysis_id: string;
  status: string;
  message: string;
}

export interface BatchAnalysisResponse {
  total: number;
  success_count: number;
  failed_count: number;
  tasks: BatchTaskResult[];
}

export const startBatchAnalysisSameParams = async (data: BatchSameParamsRequest): Promise<BatchAnalysisResponse> => {
  const response = await api.post<BatchAnalysisResponse>('/analysis/start/batch-same-params', data);
  return response.data;
};

export const getPlannedSteps = async (analysisId: string) => {
  const response = await api.get<any>(`/analysis/${analysisId}/planned_steps`);
  return response.data;
};

export const getAnalysisHistory = async (analysisId: string) => {
  const response = await api.get<any[]>(`/analysis/${analysisId}/history`);
  return response.data;
};

export interface ReportListItem {
  analysis_id: string;
  analysis_date: string;
  analysts: string[];
  formatted_decision: Record<string, any>;
  research_depth: number;
  status: string;
  stock_symbol: string;
  summary: string;
  updated_at: string;
}

export interface ReportsResponse {
  success: boolean;
  data: {
    reports: ReportListItem[];
    total: number;
    page: number;
    page_size: number;
    pages: number;
  };
  message: string;
}

export const getReportsList = async (page: number = 1, page_size: number = 10): Promise<ReportsResponse> => {
  const params = new URLSearchParams({ page: page.toString(), page_size: page_size.toString() });
  const response = await api.get<ReportsResponse>(`/reports/list?${params.toString()}`);
  return response.data;
};

// 批量回测 - 研究报告决策列表（按日期区间）
export interface FormattedDecisionItem {
  analysis_id: string;
  stock_symbol: string;
  analysis_date: string;
  formatted_decision: {
    action?: 'buy' | 'hold' | 'sell' | string;
    confidence?: number;
    target_price?: number;
    risk_score?: number;
    [key: string]: any;
  };
  summary?: string;
  [key: string]: any;
}

export interface FormattedDecisionsResponse {
  success: boolean;
  data: FormattedDecisionItem[];
  total: number;
  message: string;
}

export const getFormattedDecisions = async (
  startDate: string,
  endDate: string
): Promise<FormattedDecisionsResponse> => {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate
  });
  const response = await api.get<FormattedDecisionsResponse>(
    `/reports/formatted-decisions?${params.toString()}`
  );
  return response.data;
};

// System Config Types
export interface ModelConfig {
  provider: string;
  model_name: string;
  api_key: string;
  base_url: string | null;
  max_tokens: number;
  temperature: number;
  enabled: boolean;
}

export interface PricingConfig {
  provider: string;
  model_name: string;
  input_price_per_1k: number;
  output_price_per_1k: number;
  currency: string;
}

export interface SystemSettings {
  default_provider: string;
  default_model: string;
  enable_cost_tracking: boolean;
  cost_alert_threshold: number;
  currency_preference: string;
  auto_save_usage: boolean;
  max_usage_records: number;
  data_dir: string;
  cache_dir: string;
  results_dir: string;
  auto_create_dirs: boolean;
  openai_enabled: boolean;
  finnhub_api_key: string;
  log_level: string;
}

export interface SystemConfigData {
  models?: ModelConfig[];
  pricing?: PricingConfig[];
  settings?: SystemSettings;
}

export interface SystemConfigResponse {
  success: boolean;
  data: SystemConfigData;
  message: string;
}

export const getSystemConfig = async (configTypes: string[] = ['settings']): Promise<SystemConfigResponse> => {
  const query = configTypes.length ? `?config_types=${configTypes.join(',')}` : '';
  const response = await api.get<SystemConfigResponse>(`/config/system${query}`);
  return response.data;
};

export const updateSystemConfig = async (payload: Partial<SystemConfigData>): Promise<SystemConfigResponse> => {
  // 后端要求按照 config_types 分类提交，可以包含 models、pricing、settings 中的任意几个
  const response = await api.put<SystemConfigResponse>('/config/system', payload);
  return response.data;
};

// Operation Logs API
export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  module?: string;
  function?: string;
  line?: number;
}

export interface LogsResponse {
  success: boolean;
  data: LogEntry[];
  total: number;
  filtered_total: number;
  message: string;
}

export interface LogsStatsResponse {
  success: boolean;
  data: {
    total_files: number;
    files: Array<{
      filename: string;
      size: number;
      modified_time: string;
      exists: boolean;
      error?: string;
    }>;
  };
}

export const getOperationLogs = async (
  startDate?: string,
  endDate?: string,
  days?: number,
  keyword?: string,
  level?: string,
  logger?: string,
  limit: number = 50,
  skip: number = 0
): Promise<LogsResponse> => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (days) params.append('days', days.toString());
  if (keyword) params.append('keyword', keyword);
  if (level) params.append('level', level);
  if (logger) params.append('logger', logger);
  params.append('limit', limit.toString());
  params.append('skip', skip.toString());

  const response = await api.get<LogsResponse>(`/logs/operation/query?${params.toString()}`);
  return response.data;
};

export const getLogsStats = async (): Promise<LogsStatsResponse> => {
  const response = await api.get<LogsStatsResponse>('/logs/operation/stats');
  return response.data;
};

// Stock Data API
export interface StockBasicInfo {
  code: string;
  name: string;
  market?: string;
  category?: string;
  [key: string]: any;
}

export interface StockBasicInfoResponse {
  success: boolean;
  data: StockBasicInfo | null;
  message: string;
}

export interface StockHistoricalData {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
  [key: string]: any;
}

export interface StockHistoricalDataResponse {
  success: boolean;
  data: StockHistoricalData[] | null;
  total: number;
  message: string;
}

export interface AnalysisReport {
  analysis_id: string;
  stock_symbol: string;
  analysis_date: string;
  formatted_decision?: {
    action?: string;
    target_price?: number;
    confidence?: number;
    risk_score?: number;
    reasoning?: string;
  };
  timestamp?: number;
  [key: string]: any;
}

export interface AnalysisReportsResponse {
  success: boolean;
  data: AnalysisReport[];
  total: number;
  message: string;
}

// 批量回测结果结构
export interface SingleReportProfit {
  analysis_id: string;
  stock_symbol: string;
  company_name: string;
  analysis_date: string;
  action: string;
  profits: number[];  // 收益序列（%），每个元素对应第1天到第N天的收益
  index_name?: string;  // 大盘指数名称（如：上证指数、深证成指）
  formatted_decision?: {
    action?: string;
    confidence?: number;
    risk_score?: number;
    target_price?: number;
  };
  trade_dates?: string[];  // 交易日期列表
  trade_prices?: number[];  // 成交价列表（开盘价）
  close_prices?: number[];  // 收盘价列表
  index_returns?: number[];  // 大盘指数涨幅序列（%）
  index_closes?: number[];   // 大盘指数收盘点位序列
  strategy_trade_price?: number;  // 按照回测策略在分析日的成交价（建仓价）
}

export interface BatchBacktestResult {
  success: boolean;
  data: {
    profits: SingleReportProfit[];  // 每个研报的收益序列
    stats: {
      weighted_avg: number[];  // 加权平均收益序列（%）
    };
  };
  message: string;
}

export const getStockBasicInfo = async (stockCode: string): Promise<StockBasicInfoResponse> => {
  const response = await api.get<StockBasicInfoResponse>(`/stock-data/basic-info/${stockCode}`);
  return response.data;
};

export const getStockHistoricalData = async (
  stockCode: string,
  startDate: string,
  endDate: string,
  expectedPoints: number = 60,
  analysisDate?: string
): Promise<StockHistoricalDataResponse> => {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
    expected_points: expectedPoints.toString()
  });
  if (analysisDate) {
    params.append('analysis_date', analysisDate);
  }
  const response = await api.get<StockHistoricalDataResponse>(
    `/stock-data/historical-data/${stockCode}?${params.toString()}`
  );
  return response.data;
};

export const getAnalysisReportsByStock = async (
  stockCode: string,
  limit: number = 100,
  startDate?: string,
  endDate?: string
): Promise<AnalysisReportsResponse> => {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (startDate) {
    params.append('start_date', startDate);
  }
  if (endDate) {
    params.append('end_date', endDate);
  }

  // 当未指定股票代码时，使用特殊值 all，表示后端不过滤股票代码
  const codeForRequest = stockCode && stockCode.trim() !== '' ? stockCode.trim() : 'all';

  const response = await api.get<AnalysisReportsResponse>(
    `/stock-data/analysis-reports/${codeForRequest}?${params.toString()}`
  );
  return response.data;
};

export const startBatchBacktest = async (payload: {
  analysis_ids: string[];
}): Promise<BatchBacktestResult> => {
  // 后端当前在 app/routers/backtest.py 中定义的路径为：/backtest/batch/start-backtest
  // 回测配置参数从数据库的backtest_config中获取，不再通过请求参数传递
  const response = await api.post<BatchBacktestResult>('/backtest/batch/start-backtest', payload);
  return response.data;
};

// Cache Management API
export interface CacheCountResponse {
  success: boolean;
  total: number;
  message: string;
}

export interface CacheListItem {
  task_id: string;
  status: string;
  created_at?: string;
  updated_at?: string;
  analysis_date?: string;
  stock_symbol?: string;
  company_name?: string;
}

export interface CacheListResponse {
  success: boolean;
  data: CacheListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
  message: string;
}

export interface CacheDetailData {
  current_step?: any;
  history?: any;
  props?: any;
}

export interface CacheDetailResponse {
  success: boolean;
  data: CacheDetailData;
  message: string;
}

export const getCacheCount = async (): Promise<CacheCountResponse> => {
  const response = await api.get<CacheCountResponse>('/cache/count');
  return response.data;
};

export const getCacheList = async (
  page: number = 1,
  page_size: number = 10,
  filters?: {
    task_id?: string;
    analysis_date?: string;
    status?: string;
    stock_symbol?: string;
    company_name?: string;
  }
): Promise<CacheListResponse> => {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: page_size.toString()
  });
  
  // 添加筛选参数
  if (filters) {
    if (filters.task_id) {
      params.append('task_id', filters.task_id);
    }
    if (filters.analysis_date) {
      params.append('analysis_date', filters.analysis_date);
    }
    if (filters.status) {
      params.append('status', filters.status);
    }
    if (filters.stock_symbol) {
      params.append('stock_symbol', filters.stock_symbol);
    }
    if (filters.company_name) {
      params.append('company_name', filters.company_name);
    }
  }
  
  const response = await api.get<CacheListResponse>(`/cache/list?${params.toString()}`);
  return response.data;
};

export const getCacheDetail = async (analysisId: string): Promise<CacheDetailResponse> => {
  const response = await api.get<CacheDetailResponse>(`/cache/${analysisId}`);
  return response.data;
};

// Favorite Stocks API
export interface FavoriteStock {
  stock_code: string;
  user_id?: string;
  stock_name?: string;
  market_type?: string;
  category?: string;
  tags?: string[];
  themes?: string[];
  sectors?: string[];
  notes?: string;
  created_at?: string;
  updated_at?: string;
}

export interface FavoriteStockResponse {
  success: boolean;
  data: FavoriteStock | null;
  message: string;
}

export interface FavoriteStockListResponse {
  success: boolean;
  data: FavoriteStock[] | null;
  total: number;
  message: string;
}

export interface FavoriteStockStatisticsResponse {
  success: boolean;
  data: {
    total_count: number;
    category_stats: Record<string, number>;
    tag_stats: Record<string, number>;
  } | null;
  message: string;
}

export interface FavoriteStockCreateRequest {
  stock_code: string;
  user_id?: string;
  stock_name?: string;
  market_type?: string;
  category?: string;
  tags?: string[];
  themes?: string[];
  sectors?: string[];
  notes?: string;
}

export interface FavoriteStockUpdateRequest {
  stock_name?: string;
  market_type?: string;
  category?: string;
  tags?: string[];
  themes?: string[];
  sectors?: string[];
  notes?: string;
}

export const getFavoriteStocks = async (params?: {
  user_id?: string;
  stock_code?: string;
  category?: string;
  tag?: string;
  limit?: number;
  skip?: number;
  sort_by?: string;
  sort_order?: string;
}): Promise<FavoriteStockListResponse> => {
  const queryParams = new URLSearchParams();
  if (params) {
    if (params.user_id) queryParams.append('user_id', params.user_id);
    if (params.stock_code) queryParams.append('stock_code', params.stock_code);
    if (params.category) queryParams.append('category', params.category);
    if (params.tag) queryParams.append('tag', params.tag);
    if (params.limit) queryParams.append('limit', params.limit.toString());
    if (params.skip) queryParams.append('skip', params.skip.toString());
    if (params.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params.sort_order) queryParams.append('sort_order', params.sort_order);
  }
  const queryString = queryParams.toString();
  const url = `/favorite-stocks${queryString ? `?${queryString}` : ''}`;
  const response = await api.get<FavoriteStockListResponse>(url);
  return response.data;
};

export const getFavoriteStock = async (
  stockCode: string,
  userId?: string,
  category?: string
): Promise<FavoriteStockResponse> => {
  const queryParams = new URLSearchParams();
  if (userId) queryParams.append('user_id', userId);
  if (category) queryParams.append('category', category);
  const queryString = queryParams.toString();
  const url = `/favorite-stocks/${stockCode}${queryString ? `?${queryString}` : ''}`;
  const response = await api.get<FavoriteStockResponse>(url);
  return response.data;
};

export const createFavoriteStock = async (
  data: FavoriteStockCreateRequest
): Promise<FavoriteStockResponse> => {
  const response = await api.post<FavoriteStockResponse>('/favorite-stocks', data);
  return response.data;
};

export const updateFavoriteStock = async (
  stockCode: string,
  data: FavoriteStockUpdateRequest,
  userId?: string,
  category?: string
): Promise<FavoriteStockResponse> => {
  const queryParams = new URLSearchParams();
  if (userId) queryParams.append('user_id', userId);
  if (category) queryParams.append('category', category);
  const queryString = queryParams.toString();
  const url = `/favorite-stocks/${stockCode}${queryString ? `?${queryString}` : ''}`;
  const response = await api.put<FavoriteStockResponse>(url, data);
  return response.data;
};

export const deleteFavoriteStock = async (
  stockCode: string,
  userId?: string,
  category?: string
): Promise<FavoriteStockResponse> => {
  const queryParams = new URLSearchParams();
  if (userId) queryParams.append('user_id', userId);
  if (category) queryParams.append('category', category);
  const queryString = queryParams.toString();
  const url = `/favorite-stocks/${stockCode}${queryString ? `?${queryString}` : ''}`;
  const response = await api.delete<FavoriteStockResponse>(url);
  return response.data;
};

export const getFavoriteStocksStatistics = async (
  userId?: string
): Promise<FavoriteStockStatisticsResponse> => {
  const queryParams = new URLSearchParams();
  if (userId) queryParams.append('user_id', userId);
  const queryString = queryParams.toString();
  const url = `/favorite-stocks/statistics/summary${queryString ? `?${queryString}` : ''}`;
  const response = await api.get<FavoriteStockStatisticsResponse>(url);
  return response.data;
};

// Batch import favorite stocks
export interface FavoriteStockBatchCreateRequest {
  stock_codes: string[];
  user_id?: string;
  category?: string;
  tags?: string[];
  themes?: string[];
  sectors?: string[];
  notes?: string;
}

export interface FavoriteStockBatchCreateResponse {
  success: boolean;
  data: {
    total: number;
    success_count: number;
    failed_count: number;
    success_list: string[];
    failed_list: Array<{
      stock_code: string;
      error: string;
    }>;
  } | null;
  message: string;
}

export const batchCreateFavoriteStocks = async (
  data: FavoriteStockBatchCreateRequest
): Promise<FavoriteStockBatchCreateResponse> => {
  const response = await api.post<FavoriteStockBatchCreateResponse>('/favorite-stocks/batch', data);
  return response.data;
};

// Sector list APIs
export interface SectorInfo {
  name: string;
  stocks?: Array<{ code: string; name: string }>;
  updated_at?: string;
}

export interface SectorListResponse {
  success: boolean;
  data: SectorInfo[] | null;
  total: number;
  message: string;
}

export const getConceptList = async (
  limit?: number,
  skip?: number
): Promise<SectorListResponse> => {
  const queryParams = new URLSearchParams();
  if (limit) queryParams.append('limit', limit.toString());
  if (skip) queryParams.append('skip', skip.toString());
  const queryString = queryParams.toString();
  const url = `/stock-data/sectors/concept/list${queryString ? `?${queryString}` : ''}`;
  const response = await api.get<SectorListResponse>(url);
  return response.data;
};

export const getIndustryList = async (
  limit?: number,
  skip?: number
): Promise<SectorListResponse> => {
  const queryParams = new URLSearchParams();
  if (limit) queryParams.append('limit', limit.toString());
  if (skip) queryParams.append('skip', skip.toString());
  const queryString = queryParams.toString();
  const url = `/stock-data/sectors/industry/list${queryString ? `?${queryString}` : ''}`;
  const response = await api.get<SectorListResponse>(url);
  return response.data;
};

// Get stocks by sector
export interface SectorStocksResponse {
  success: boolean;
  data: Record<string, Array<{ code: string; name: string }>> | null;
  message: string;
}

export const getStocksByConcept = async (
  conceptNames: string[]
): Promise<SectorStocksResponse> => {
  const response = await api.post<SectorStocksResponse>('/stock-data/sectors/concept/stocks', {
    concept_names: conceptNames
  });
  return response.data;
};

export const getStocksByIndustry = async (
  industryNames: string[]
): Promise<SectorStocksResponse> => {
  const response = await api.post<SectorStocksResponse>('/stock-data/sectors/industry/stocks', {
    industry_names: industryNames
  });
  return response.data;
};

export default api;
