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

export default api;
