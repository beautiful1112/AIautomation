import axios from 'axios';
import type {
  AgentActivityResponse,
  AgentStats,
  IncidentDetailResponse,
  IncidentsResponse,
  RecentActivityResponse,
  StatusResponse,
} from '../types';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  // Status endpoint
  getStatus: async (): Promise<StatusResponse> => {
    const response = await client.get<StatusResponse>('/api/status');
    return response.data;
  },

  // Incidents endpoints
  getIncidents: async (params?: {
    severity?: string;
    domain?: string;
    status?: string;
    search?: string;
  }): Promise<IncidentsResponse> => {
    const response = await client.get<IncidentsResponse>('/api/incidents', { params });
    return response.data;
  },

  getIncident: async (id: string): Promise<IncidentDetailResponse> => {
    const response = await client.get<IncidentDetailResponse>(`/api/incidents/${id}`);
    return response.data;
  },

  // Agents endpoints
  getAgents: async (): Promise<AgentStats[]> => {
    const response = await client.get<AgentStats[]>('/api/agents');
    return response.data;
  },

  getAgentActivity: async (agent: string, limit = 50): Promise<AgentActivityResponse> => {
    const response = await client.get<AgentActivityResponse>(`/api/agents/${agent}/activity`, {
      params: { limit },
    });
    return response.data;
  },

  // Activity endpoint
  getRecentActivity: async (limit = 50): Promise<RecentActivityResponse> => {
    const response = await client.get<RecentActivityResponse>('/api/activity/recent', {
      params: { limit },
    });
    return response.data;
  },

  // Manual trigger
  runGraph: async (): Promise<{ message: string; status: string; incidents_count: number; actions_count: number; error?: string }> => {
    const response = await client.post('/api/run-graph');
    return response.data;
  },

  // Monitoring status
  getMonitoringStatus: async (): Promise<{
    active: boolean;
    last_run_time: string | null;
    last_run_status: { status: string; error?: string };
  }> => {
    const response = await client.get('/api/monitoring-status');
    return response.data;
  },
};

