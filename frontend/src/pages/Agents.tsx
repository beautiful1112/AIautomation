import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useAgents, useAgentActivity } from '../hooks/useApi';
import { formatRelativeTime } from '../lib/utils';
import { useState } from 'react';

export function Agents() {
  const { data: agents, isLoading } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const { data: activity } = useAgentActivity(selectedAgent, 20);

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

  const getAgentDescription = (agent: string) => {
    switch (agent) {
      case 'monitor':
        return 'Monitoring Orchestrator - Polls Prometheus and routes alerts';
      case 'k8s':
        return 'Kubernetes Agent - Investigates K8s-related incidents';
      case 'network':
        return 'Network Agent - Investigates network device incidents';
      case 'review':
        return 'Review Agent - Evaluates severity and performs auto-remediation';
      case 'ticket':
        return 'Ticket Agent - Creates tickets and sends notifications';
      default:
        return '';
    }
  };

  if (isLoading) {
    return <div className="text-center py-8">Loading agents...</div>;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Agents</CardTitle>
          <CardDescription>Agent statistics and activity</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents?.map((agent) => (
              <Card
                key={agent.agent}
                className={`cursor-pointer transition-all ${
                  selectedAgent === agent.agent ? 'ring-2 ring-primary' : ''
                }`}
                onClick={() => setSelectedAgent(selectedAgent === agent.agent ? '' : agent.agent)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{agent.agent}</CardTitle>
                    <Badge variant={getAgentBadgeVariant(agent.agent)}>{agent.agent}</Badge>
                  </div>
                  <CardDescription className="mt-2">{getAgentDescription(agent.agent)}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Last Active:</span>
                    <span>{agent.lastActiveAt ? formatRelativeTime(agent.lastActiveAt) : 'Never'}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Incidents Handled:</span>
                    <span className="font-medium">{agent.incidentsHandled}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Actions Performed:</span>
                    <span className="font-medium">{agent.actionsPerformed}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Auto-Remediations:</span>
                    <span className="font-medium">{agent.autoRemediations}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Agent Activity */}
      {selectedAgent && (
        <Card>
          <CardHeader>
            <CardTitle>Activity: {selectedAgent}</CardTitle>
            <CardDescription>Recent actions by this agent</CardDescription>
          </CardHeader>
          <CardContent>
            {!activity?.actions.length ? (
              <div className="text-center py-4 text-muted-foreground">No activity recorded</div>
            ) : (
              <div className="space-y-2">
                {activity.actions.map((action) => (
                  <div key={action.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                    <Badge variant={getAgentBadgeVariant(action.agent)} className="mt-0.5">
                      {action.type}
                    </Badge>
                    <div className="flex-1">
                      <p className="text-sm">{action.message}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatRelativeTime(action.created_at)}
                      </p>
                      {action.incident_id && action.incident_id !== 'none' && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Incident: <span className="font-mono">{action.incident_id}</span>
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

