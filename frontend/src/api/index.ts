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

export interface SystemConfigResponse {
  success: boolean;
  data: Record<string, any>;
  message: string;
}

export const getSystemConfig = async (configTypes: string[] = ['settings']): Promise<SystemConfigResponse> => {
  const query = configTypes.length ? `?config_types=${configTypes.join(',')}` : '';
  const response = await api.get<SystemConfigResponse>(`/config/system${query}`);
  return response.data;
};

export const updateSystemConfig = async (payload: Record<string, any>): Promise<SystemConfigResponse> => {
  // 后端要求按照 config_types 分类提交，这里只更新 settings
  const response = await api.put<SystemConfigResponse>('/config/system', { settings: payload });
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
  limit: number = 1000
): Promise<LogsResponse> => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  if (days) params.append('days', days.toString());
  if (keyword) params.append('keyword', keyword);
  if (level) params.append('level', level);
  if (logger) params.append('logger', logger);
  params.append('limit', limit.toString());
  
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

export default api;
