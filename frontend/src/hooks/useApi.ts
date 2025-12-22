import { useQuery } from '@tanstack/react-query';
import { api } from '../api/client';
import type { AgentStats, IncidentDetailResponse, IncidentsResponse, StatusResponse } from '../types';

// Status
export function useStatus() {
  return useQuery<StatusResponse>({
    queryKey: ['status'],
    queryFn: () => api.getStatus(),
    refetchInterval: 10000, // Refetch every 10 seconds
  });
}

// Incidents
export function useIncidents(params?: {
  severity?: string;
  domain?: string;
  status?: string;
  search?: string;
}) {
  return useQuery<IncidentsResponse>({
    queryKey: ['incidents', params],
    queryFn: () => api.getIncidents(params),
    refetchInterval: 10000,
  });
}

export function useIncident(id: string) {
  return useQuery<IncidentDetailResponse>({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id),
    enabled: !!id,
    refetchInterval: 10000,
  });
}

// Agents
export function useAgents() {
  return useQuery<AgentStats[]>({
    queryKey: ['agents'],
    queryFn: () => api.getAgents(),
    refetchInterval: 10000,
  });
}

export function useAgentActivity(agent: string, limit = 50) {
  return useQuery({
    queryKey: ['agent-activity', agent, limit],
    queryFn: () => api.getAgentActivity(agent, limit),
    enabled: !!agent,
    refetchInterval: 10000,
  });
}

// Recent Activity
export function useRecentActivity(limit = 50) {
  return useQuery({
    queryKey: ['recent-activity', limit],
    queryFn: () => api.getRecentActivity(limit),
    refetchInterval: 5000, // More frequent for activity feed
  });
}

