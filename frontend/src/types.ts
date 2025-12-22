// Type definitions matching backend models

export type Incident = {
  id: string;
  source: string;
  alertname: string;
  domain: 'k8s' | 'network';
  severity: 'low' | 'medium' | 'high' | 'unknown';
  status: 'new' | 'investigating' | 'auto_remediated' | 'awaiting_human' | 'resolved';
  labels: Record<string, string>;
  annotations: Record<string, string>;
  created_at: string;
  updated_at: string;
  auto_remediated: boolean;
  assigned_agent: string | null;
  findings?: Record<string, any> | null;
  recommendation?: string | null;
  ticket_id?: string | null;
};

export type Action = {
  id: string;
  incident_id: string;
  agent: 'monitor' | 'k8s' | 'network' | 'review' | 'ticket';
  type: string;
  message: string;
  data?: Record<string, any> | null;
  created_at: string;
};

export type StatusResponse = {
  overall_status: 'healthy' | 'degraded';
  last_normal_report: {
    text: string;
    timestamp: string;
  } | null;
  stats: {
    active_incidents: number;
    k8s_incidents: number;
    network_incidents: number;
    auto_remediations_24h: number;
  };
};

export type IncidentsResponse = {
  incidents: Incident[];
  count: number;
};

export type IncidentDetailResponse = {
  incident: Incident;
  actions: Action[];
};

export type AgentStats = {
  agent: string;
  lastActiveAt: string | null;
  incidentsHandled: number;
  actionsPerformed: number;
  autoRemediations: number;
};

export type AgentActivityResponse = {
  agent: string;
  actions: Action[];
  count: number;
};

export type RecentActivityResponse = {
  actions: Action[];
  count: number;
};

