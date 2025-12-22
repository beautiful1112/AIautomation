import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Input } from '../components/ui/Input';
import { Select } from '../components/ui/Select';
import { useIncidents } from '../hooks/useApi';
import { formatDate } from '../lib/utils';

export function Incidents() {
  const [severity, setSeverity] = useState<string>('');
  const [domain, setDomain] = useState<string>('');
  const [status, setStatus] = useState<string>('');
  const [search, setSearch] = useState<string>('');

  const { data, isLoading } = useIncidents({
    severity: severity || undefined,
    domain: domain || undefined,
    status: status || undefined,
    search: search || undefined,
  });

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

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Incidents</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="grid gap-4 md:grid-cols-4 mb-6">
            <Input
              placeholder="Search incidents..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <Select value={domain} onChange={(e) => setDomain(e.target.value)}>
              <option value="">All Domains</option>
              <option value="k8s">Kubernetes</option>
              <option value="network">Network</option>
            </Select>
            <Select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              <option value="">All Severities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="unknown">Unknown</option>
            </Select>
            <Select value={status} onChange={(e) => setStatus(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="new">New</option>
              <option value="investigating">Investigating</option>
              <option value="auto_remediated">Auto-Remediated</option>
              <option value="awaiting_human">Awaiting Human</option>
              <option value="resolved">Resolved</option>
            </Select>
          </div>

          {/* Incidents Table */}
          {isLoading ? (
            <div className="text-center py-8">Loading incidents...</div>
          ) : !data?.incidents.length ? (
            <div className="text-center py-8 text-muted-foreground">No incidents found</div>
          ) : (
            <div className="border rounded-lg overflow-hidden">
              <table className="w-full">
                <thead className="bg-muted">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-medium">ID</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Domain</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Severity</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Summary</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Created</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {data.incidents.map((incident) => (
                    <tr key={incident.id} className="hover:bg-accent">
                      <td className="px-4 py-3">
                        <Link
                          to={`/incidents/${incident.id}`}
                          className="text-primary hover:underline font-mono text-sm"
                        >
                          {incident.id}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline">{incident.domain}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={getSeverityBadgeVariant(incident.severity)}>
                          {incident.severity}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="secondary">{incident.status}</Badge>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {incident.annotations?.summary || incident.annotations?.description || '-'}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {formatDate(incident.created_at)}
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {formatDate(incident.updated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

