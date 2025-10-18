/**
 * Incidents Panel - Phase 5.4 PR4
 * 
 * Real-time incident dashboard with SSE updates.
 */
import React, { useState } from 'react';
import { useIncidentsSSE } from '../../hooks/useIncidentsSSE';
import { IncidentCard } from './IncidentCard';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import { Alert } from '../ui/alert';

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
      <div className="border-b border-gray-200 p-4">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <h5 className="text-lg font-semibold m-0">Incidents</h5>
            {connected ? (
              <Badge variant="default" className="flex items-center gap-1">
                <span className="status-dot" />
                Live
              </Badge>
            ) : (
              <Badge variant="secondary">Disconnected</Badge>
            )}
          </div>
          
          <div className="flex gap-2">
            <Badge variant="destructive">{sev1Count} SEV1</Badge>
            <Badge variant="outline">{sev2Count} SEV2</Badge>
            <Badge variant="default">{openCount} Open</Badge>
          </div>
        </div>
      </div>

      <div className="p-4">
        {/* Filters */}
        <div className="mb-3 flex gap-2 flex-wrap">
          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              className={`px-4 py-2 text-sm font-medium border ${filter === 'all' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'} rounded-l-lg`}
              onClick={() => setFilter('all')}
            >
              All
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border-t border-b ${filter === 'open' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
              onClick={() => setFilter('open')}
            >
              Open
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border-t border-b ${filter === 'acknowledged' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
              onClick={() => setFilter('acknowledged')}
            >
              Acknowledged
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border ${filter === 'resolved' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'} rounded-r-lg`}
              onClick={() => setFilter('resolved')}
            >
              Resolved
            </button>
          </div>

          <div className="inline-flex rounded-md shadow-sm" role="group">
            <button
              className={`px-4 py-2 text-sm font-medium border ${severityFilter === 'all' ? 'bg-gray-600 text-white border-gray-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'} rounded-l-lg`}
              onClick={() => setSeverityFilter('all')}
            >
              All Severity
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border-t border-b ${severityFilter === 'sev1' ? 'bg-red-600 text-white border-red-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'}`}
              onClick={() => setSeverityFilter('sev1')}
            >
              SEV1
            </button>
            <button
              className={`px-4 py-2 text-sm font-medium border ${severityFilter === 'sev2' ? 'bg-yellow-600 text-white border-yellow-600' : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'} rounded-r-lg`}
              onClick={() => setSeverityFilter('sev2')}
            >
              SEV2
            </button>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="text-center py-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900 mx-auto" />
            <span className="sr-only">Loading...</span>
          </div>
        )}

        {/* Error state */}
        {error && (
          <Alert variant="destructive">
            <div className="font-semibold">Error loading incidents</div>
            <p className="mt-1">{error}</p>
          </Alert>
        )}

        {/* Incidents list */}
        {!loading && !error && (
          <div className="incidents-list">
            {filteredIncidents.length === 0 ? (
              <div className="text-center text-gray-500 py-4">
                {filter === 'all' ? (
                  <>
                    <div className="mb-2 text-2xl">🎉</div>
                    <div>No incidents - all systems operational!</div>
                  </>
                ) : (
                  <div>No incidents matching filters</div>
                )}
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {filteredIncidents.map((incident) => (
                  <IncidentCard key={incident.id} incident={incident} />
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
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

        .card-header {
          padding: 1rem 1.5rem;
          border-bottom: 1px solid #e5e7eb;
        }

        .card-body {
          padding: 1.5rem;
        }

        .d-flex {
          display: flex;
        }

        .justify-content-between {
          justify-content: space-between;
        }

        .align-items-center {
          align-items: center;
        }

        .gap-2 {
          gap: 0.5rem;
        }

        .mb-0 {
          margin-bottom: 0;
        }

        .text-center {
          text-center: center;
        }

        .py-4 {
          padding-top: 1rem;
          padding-bottom: 1rem;
        }

        .mb-3 {
          margin-bottom: 0.75rem;
        }

        .flex-wrap {
          flex-wrap: wrap;
        }
      `}</style>
    </Card>
  );
};
