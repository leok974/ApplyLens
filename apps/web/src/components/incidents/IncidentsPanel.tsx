/**
 * Incidents Panel - Phase 5.4 PR4
 * 
 * Real-time incident dashboard with SSE updates.
 */
import React, { useState } from 'react';
import { useIncidentsSSE } from '../../hooks/useIncidentsSSE';
import { IncidentCard } from './IncidentCard';

interface IncidentsPanelProps {
  className?: string;
}

export const IncidentsPanel: React.FC<IncidentsPanelProps> = ({ className }) => {
  const { incidents, loading, error, connected } = useIncidentsSSE();
  const [filter, setFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  const filteredIncidents = incidents.filter((incident) => {
    // Status filter
    if (filter !== 'all' && incident.status !== filter) {
      return false;
    }
    
    // Severity filter
    if (severityFilter !== 'all' && incident.severity !== severityFilter) {
      return false;
    }
    
    return true;
  });

  const openCount = incidents.filter((i) => i.status === 'open').length;
  const sev1Count = incidents.filter((i) => i.severity === 'sev1').length;
  const sev2Count = incidents.filter((i) => i.severity === 'sev2').length;

  return (
    <Card className={className}>
      <Card.Header className="d-flex justify-content-between align-items-center">
        <div className="d-flex align-items-center gap-2">
          <h5 className="mb-0">Incidents</h5>
          {connected ? (
            <Badge bg="success" className="d-flex align-items-center gap-1">
              <span className="status-dot" />
              Live
            </Badge>
          ) : (
            <Badge bg="secondary">Disconnected</Badge>
          )}
        </div>
        
        <div className="d-flex gap-2">
          <Badge bg="danger">{sev1Count} SEV1</Badge>
          <Badge bg="warning">{sev2Count} SEV2</Badge>
          <Badge bg="info">{openCount} Open</Badge>
        </div>
      </Card.Header>

      <Card.Body>
        {/* Filters */}
        <div className="mb-3 d-flex gap-2 flex-wrap">
          <div className="btn-group btn-group-sm">
            <button
              className={`btn ${filter === 'all' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button
              className={`btn ${filter === 'open' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setFilter('open')}
            >
              Open
            </button>
            <button
              className={`btn ${filter === 'acknowledged' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setFilter('acknowledged')}
            >
              Acknowledged
            </button>
            <button
              className={`btn ${filter === 'resolved' ? 'btn-primary' : 'btn-outline-primary'}`}
              onClick={() => setFilter('resolved')}
            >
              Resolved
            </button>
          </div>

          <div className="btn-group btn-group-sm">
            <button
              className={`btn ${severityFilter === 'all' ? 'btn-secondary' : 'btn-outline-secondary'}`}
              onClick={() => setSeverityFilter('all')}
            >
              All Severity
            </button>
            <button
              className={`btn ${severityFilter === 'sev1' ? 'btn-danger' : 'btn-outline-danger'}`}
              onClick={() => setSeverityFilter('sev1')}
            >
              SEV1
            </button>
            <button
              className={`btn ${severityFilter === 'sev2' ? 'btn-warning' : 'btn-outline-warning'}`}
              onClick={() => setSeverityFilter('sev2')}
            >
              SEV2
            </button>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="text-center py-4">
            <Spinner animation="border" role="status">
              <span className="visually-hidden">Loading...</span>
            </Spinner>
          </div>
        )}

        {/* Error state */}
        {error && (
          <Alert variant="danger">
            <Alert.Heading>Error loading incidents</Alert.Heading>
            <p>{error}</p>
          </Alert>
        )}

        {/* Incidents list */}
        {!loading && !error && (
          <div className="incidents-list">
            {filteredIncidents.length === 0 ? (
              <div className="text-center text-muted py-4">
                {filter === 'all' ? (
                  <>
                    <div className="mb-2">🎉</div>
                    <div>No incidents - all systems operational!</div>
                  </>
                ) : (
                  <div>No incidents matching filters</div>
                )}
              </div>
            ) : (
              <div className="d-flex flex-column gap-3">
                {filteredIncidents.map((incident) => (
                  <IncidentCard key={incident.id} incident={incident} />
                ))}
              </div>
            )}
          </div>
        )}
      </Card.Body>

      <style jsx>{`
        .status-dot {
          width: 6px;
          height: 6px;
          background: currentColor;
          border-radius: 50%;
          display: inline-block;
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .incidents-list {
          max-height: 600px;
          overflow-y: auto;
        }

        .btn-group-sm .btn {
          font-size: 0.875rem;
        }
      `}</style>
    </Card>
  );
};
