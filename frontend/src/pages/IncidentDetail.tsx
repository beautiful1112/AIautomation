import { useParams } from 'react-router-dom';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { useIncident } from '../hooks/useApi';
import { formatDate, formatRelativeTime } from '../lib/utils';

export function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const { data, isLoading } = useIncident(id || '');

  if (isLoading) {
    return <div className="text-center py-8">Loading incident...</div>;
  }

  if (!data) {
    return <div className="text-center py-8">Incident not found</div>;
  }

  const { incident, actions } = data;

  const getSeverityBadgeVariant = (severity: string) => {
    switch (severity) {
      case 'high':
        return 'destructive';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'secondary';
    }
  };

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">{incident.alertname}</CardTitle>
              <CardDescription className="mt-2">Incident ID: {incident.id}</CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant={getSeverityBadgeVariant(incident.severity)}>{incident.severity}</Badge>
              <Badge variant="outline">{incident.domain}</Badge>
              <Badge variant="secondary">{incident.status}</Badge>
            </div>
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Left Column: Incident Info */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Alert Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <h4 className="text-sm font-medium mb-2">Labels</h4>
                <div className="space-y-1">
                  {Object.entries(incident.labels).map(([key, value]) => (
                    <div key={key} className="flex text-sm">
                      <span className="font-mono text-muted-foreground w-32">{key}:</span>
                      <span className="flex-1">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Annotations</h4>
                <div className="space-y-1">
                  {Object.entries(incident.annotations).map(([key, value]) => (
                    <div key={key} className="flex text-sm">
                      <span className="font-mono text-muted-foreground w-32">{key}:</span>
                      <span className="flex-1">{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className="text-sm font-medium mb-2">Timestamps</h4>
                <div className="space-y-1 text-sm">
                  <div>
                    <span className="text-muted-foreground">Created:</span> {formatDate(incident.created_at)}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Updated:</span> {formatDate(incident.updated_at)}
                  </div>
                </div>
              </div>
              {incident.assigned_agent && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Assigned Agent</h4>
                  <Badge variant="outline">{incident.assigned_agent}</Badge>
                </div>
              )}
              {incident.ticket_id && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Ticket ID</h4>
                  <Badge variant="outline">{incident.ticket_id}</Badge>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Findings */}
          {incident.findings && (
            <Card>
              <CardHeader>
                <CardTitle>Findings</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-xs bg-muted p-4 rounded-lg overflow-auto">
                  {JSON.stringify(incident.findings, null, 2)}
                </pre>
              </CardContent>
            </Card>
          )}

          {/* Recommendation */}
          {incident.recommendation && (
            <Card>
              <CardHeader>
                <CardTitle>Recommendation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm whitespace-pre-wrap">{incident.recommendation}</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right Column: Timeline */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Timeline</CardTitle>
              <CardDescription>Agent actions and events</CardDescription>
            </CardHeader>
            <CardContent>
              {actions.length === 0 ? (
                <div className="text-center py-4 text-muted-foreground">No actions recorded</div>
              ) : (
                <div className="space-y-4">
                  {actions.map((action, index) => (
                    <div key={action.id} className="flex space-x-4">
                      <div className="flex flex-col items-center">
                        <div className="w-2 h-2 rounded-full bg-primary" />
                        {index < actions.length - 1 && <div className="w-0.5 h-full bg-border mt-2" />}
                      </div>
                      <div className="flex-1 pb-4">
                        <div className="flex items-center space-x-2 mb-1">
                          <Badge variant={getAgentBadgeVariant(action.agent)}>{action.agent}</Badge>
                          <span className="text-xs text-muted-foreground">{action.type}</span>
                        </div>
                        <p className="text-sm">{action.message}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatRelativeTime(action.created_at)}
                        </p>
                        {action.data && Object.keys(action.data).length > 0 && (
                          <details className="mt-2">
                            <summary className="text-xs text-muted-foreground cursor-pointer">View data</summary>
                            <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto">
                              {JSON.stringify(action.data, null, 2)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Auto-Remediation Panel */}
          {incident.auto_remediated && (
            <Card className="border-green-500">
              <CardHeader>
                <CardTitle className="text-green-700">Auto-Remediation</CardTitle>
                <CardDescription>This incident was automatically remediated</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm">
                  The Review Agent determined this was a low-severity issue and performed automatic remediation.
                </p>
                {actions.find((a) => a.type === 'remediation') && (
                  <div className="mt-2 p-2 bg-green-50 rounded text-sm">
                    {actions.find((a) => a.type === 'remediation')?.message}
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

