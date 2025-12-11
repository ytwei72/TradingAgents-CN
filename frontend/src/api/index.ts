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

export default api;
