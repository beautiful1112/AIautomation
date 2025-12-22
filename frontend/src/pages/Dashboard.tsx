import { useState } from 'react';
import { CheckCircle2, XCircle, AlertCircle, Activity, Play, RefreshCw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useStatus, useRecentActivity } from '../hooks/useApi';
import { formatRelativeTime } from '../lib/utils';
import { Link } from 'react-router-dom';
import { useIncidents } from '../hooks/useApi';
import { api } from '../api/client';
import { useQuery, useQueryClient } from '@tanstack/react-query';

export function Dashboard() {
  const queryClient = useQueryClient();
  const { data: status, isLoading: statusLoading } = useStatus();
  const { data: activity, isLoading: activityLoading } = useRecentActivity(20);
  const { data: incidentsData, isLoading: incidentsLoading } = useIncidents();
  const [isRunning, setIsRunning] = useState(false);

  const { data: monitoringStatus } = useQuery({
    queryKey: ['monitoring-status'],
    queryFn: () => api.getMonitoringStatus(),
    refetchInterval: 5000,
  });

  const handleManualRun = async () => {
    setIsRunning(true);
    try {
      await api.runGraph();
      // Refresh all data after manual run
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['status'] }),
        queryClient.invalidateQueries({ queryKey: ['incidents'] }),
        queryClient.invalidateQueries({ queryKey: ['recent-activity'] }),
        queryClient.invalidateQueries({ queryKey: ['monitoring-status'] }),
      ]);
    } catch (error) {
      console.error('Failed to run graph:', error);
    } finally {
      setIsRunning(false);
    }
  };

  const activeIncidents = incidentsData?.incidents.filter(
    (inc) => inc.status !== 'resolved' && inc.status !== 'auto_remediated'
  ) || [];

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

  if (statusLoading) {
    return <div className="text-center py-8">Loading dashboard...</div>;
  }

  return (
    <div className="space-y-6">
      {/* Global Health Banner */}
      <Card className={status?.overall_status === 'healthy' ? 'border-green-500' : 'border-red-500'}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              {status?.overall_status === 'healthy' ? (
                <CheckCircle2 className="h-6 w-6 text-green-500" />
              ) : (
                <XCircle className="h-6 w-6 text-red-500" />
              )}
              <CardTitle>
                System Status: {status?.overall_status === 'healthy' ? 'Healthy' : 'Degraded'}
              </CardTitle>
            </div>
            <div className="flex items-center space-x-2">
              <Badge variant={status?.overall_status === 'healthy' ? 'success' : 'destructive'}>
                {status?.overall_status === 'healthy' ? 'Healthy' : 'Degraded'}
              </Badge>
              <Button
                onClick={handleManualRun}
                disabled={isRunning}
                size="sm"
                variant="outline"
                className="flex items-center space-x-2"
              >
                {isRunning ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>Running...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4" />
                    <span>Run Now</span>
                  </>
                )}
              </Button>
            </div>
          </div>
          {status?.last_normal_report && (
            <CardDescription className="mt-2">
              {status.last_normal_report.text} — {formatRelativeTime(status.last_normal_report.timestamp)}
            </CardDescription>
          )}
          {/* Monitoring Status */}
          {monitoringStatus && (
            <div className="mt-4 p-3 bg-muted rounded-lg">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center space-x-2">
                  <Activity className={`h-4 w-4 ${monitoringStatus.active ? 'text-green-500' : 'text-gray-400'}`} />
                  <span className="text-muted-foreground">
                    Auto monitoring: {monitoringStatus.active ? 'running' : 'stopped'}
                  </span>
                </div>
                {monitoringStatus.last_run_time && (
                  <span className="text-muted-foreground">
                    Last run: {formatRelativeTime(monitoringStatus.last_run_time)}
                  </span>
                )}
              </div>
              {monitoringStatus.last_run_status && (
                <div className="mt-2 text-xs">
                  <span className="text-muted-foreground">Status: </span>
                  <Badge
                    variant={monitoringStatus.last_run_status.status === 'success' ? 'success' : 'destructive'}
                    className="text-xs"
                  >
                    {monitoringStatus.last_run_status.status === 'success'
                      ? `Success (${(monitoringStatus.last_run_status as any).incidents_count || 0} incidents, ${(monitoringStatus.last_run_status as any).actions_count || 0} actions)`
                      : `Error: ${monitoringStatus.last_run_status.error || 'Unknown error'}`}
                  </Badge>
                </div>
              )}
            </div>
          )}
        </CardHeader>
      </Card>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Incidents</CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.stats.active_incidents || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">K8s Incidents</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.stats.k8s_incidents || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Network Incidents</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.stats.network_incidents || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auto-Remediations (24h)</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.stats.auto_remediations_24h || 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Active Incidents Preview */}
      <Card>
        <CardHeader>
          <CardTitle>Active Incidents</CardTitle>
          <CardDescription>Recent incidents requiring attention</CardDescription>
        </CardHeader>
        <CardContent>
          {incidentsLoading ? (
            <div className="text-center py-4">Loading incidents...</div>
          ) : activeIncidents.length === 0 ? (
            <div className="text-center py-4 text-muted-foreground">No active incidents</div>
          ) : (
            <div className="space-y-2">
              {activeIncidents.slice(0, 10).map((incident) => (
                <Link
                  key={incident.id}
                  to={`/incidents/${incident.id}`}
                  className="block p-4 border rounded-lg hover:bg-accent transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{incident.alertname}</span>
                        <Badge variant={getSeverityBadgeVariant(incident.severity)}>{incident.severity}</Badge>
                        <Badge variant="outline">{incident.domain}</Badge>
                        <Badge variant="secondary">{incident.status}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {incident.annotations?.summary || incident.annotations?.description || 'No description'}
                      </p>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {formatRelativeTime(incident.updated_at)}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Agent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Agent Activity</CardTitle>
          <CardDescription>Latest actions taken by agents</CardDescription>
        </CardHeader>
        <CardContent>
          {activityLoading ? (
            <div className="text-center py-4">Loading activity...</div>
          ) : !activity?.actions.length ? (
            <div className="text-center py-4 text-muted-foreground">No recent activity</div>
          ) : (
            <div className="space-y-2">
              {activity.actions.map((action) => (
                <div key={action.id} className="flex items-start space-x-3 p-3 border rounded-lg">
                  <Badge variant="outline" className="mt-0.5">
                    {action.agent}
                  </Badge>
                  <div className="flex-1">
                    <p className="text-sm">{action.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatRelativeTime(action.created_at)}
                    </p>
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

