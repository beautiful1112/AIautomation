import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Select } from '../components/ui/Select';
import { useRecentActivity } from '../hooks/useApi';
import { formatRelativeTime, formatDate } from '../lib/utils';

export function AgentLogs() {
  const [agentFilter, setAgentFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const { data: activity, isLoading } = useRecentActivity(200);

  const getAgentBadgeVariant = (agent: string) => {
    switch (agent) {
      case 'monitor':
        return 'default';
      case 'k8s':
        return 'success';
      case 'network':
        return 'warning';
      case 'review':
        return 'secondary';
      case 'ticket':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  const getTypeBadgeVariant = (type: string) => {
    switch (type) {
      case 'step':
        return 'outline';
      case 'alert_received':
        return 'default';
      case 'investigation':
        return 'success';
      case 'remediation':
        return 'warning';
      case 'escalation':
        return 'destructive';
      case 'normal_report':
        return 'success';
      default:
        return 'secondary';
    }
  };

  const filteredActions = activity?.actions.filter((action) => {
    if (agentFilter && action.agent !== agentFilter) return false;
    if (typeFilter && action.type !== typeFilter) return false;
    return true;
  }) || [];

  // Extract unique agents and types from all actions
  const agents = Array.from(new Set(activity?.actions.map((a) => a.agent) || [])).sort();
  const types = Array.from(new Set(activity?.actions.map((a) => a.type) || [])).sort();

  if (isLoading) {
    return <div className="text-center py-8">Loading agent logs...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Agent Execution Logs</CardTitle>
          <CardDescription>Detailed step-by-step view of all agent actions and reasoning</CardDescription>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          {activity && activity.actions.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2 mb-6">
              <div>
                <label className="text-sm font-medium mb-2 block">Filter by Agent</label>
                <Select value={agentFilter} onChange={(e) => setAgentFilter(e.target.value)}>
                  <option value="">All Agents</option>
                  {agents.map((agent) => (
                    <option key={agent} value={agent}>
                      {agent}
                    </option>
                  ))}
                </Select>
                {agents.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {agents.length} agent{agents.length !== 1 ? 's' : ''} available
                  </p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Filter by Action Type</label>
                <Select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
                  <option value="">All Types</option>
                  {types.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </Select>
                {types.length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    {types.length} type{types.length !== 1 ? 's' : ''} available
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Logs */}
          {filteredActions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">No logs found</div>
          ) : (
            <div className="space-y-3">
              {filteredActions.map((action) => (
                <div
                  key={action.id}
                  className="border rounded-lg p-4 hover:bg-accent transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      <Badge variant={getAgentBadgeVariant(action.agent)}>{action.agent}</Badge>
                      <Badge variant={getTypeBadgeVariant(action.type)}>{action.type}</Badge>
                      {action.incident_id && action.incident_id !== 'none' && (
                        <span className="text-xs text-muted-foreground font-mono">
                          Incident: {action.incident_id}
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {formatDate(action.created_at)}
                    </div>
                  </div>
                  <p className="text-sm mb-2">{action.message}</p>
                  {action.data && Object.keys(action.data).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                        View detailed data
                      </summary>
                      <pre className="text-xs bg-muted p-3 rounded mt-2 overflow-auto max-h-64">
                        {JSON.stringify(action.data, null, 2)}
                      </pre>
                    </details>
                  )}
                  <div className="text-xs text-muted-foreground mt-2">
                    {formatRelativeTime(action.created_at)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

