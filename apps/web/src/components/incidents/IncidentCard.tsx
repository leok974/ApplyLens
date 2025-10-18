/**
 * Incident Card - Phase 5.4 PR4
 * 
 * Display individual incident with actions.
 */
import React, { useState } from 'react';
import type { Incident } from '../../types/incidents';
import { PlaybookActions } from './PlaybookActions';

interface IncidentCardProps {
  incident: Incident;
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident }) => {
  const [expanded, setExpanded] = useState(false);
  const [showActions, setShowActions] = useState(false);

  const severityColors = {
    sev1: '#dc3545',
    sev2: '#ffc107',
    sev3: '#0dcaf0',
    sev4: '#6c757d',
  };

  const statusColors = {
    open: '#dc3545',
    acknowledged: '#ffc107',
    mitigated: '#0dcaf0',
    resolved: '#198754',
    closed: '#6c757d',
  };

  const kindIcons = {
    invariant: '🔍',
    budget: '💰',
    planner: '🎯',
  };

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return null;
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  const timeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  return (
    <div className="incident-card">
      <div className="incident-header" onClick={() => setExpanded(!expanded)}>
        <div className="incident-title">
          <span className="kind-icon">{kindIcons[incident.kind]}</span>
          <span className="severity-badge" style={{ backgroundColor: severityColors[incident.severity] }}>
            {incident.severity.toUpperCase()}
          </span>
          <span className="summary">{incident.summary}</span>
        </div>
        
        <div className="incident-meta">
          <span className="status-badge" style={{ backgroundColor: statusColors[incident.status] }}>
            {incident.status}
          </span>
          <span className="time-ago">{timeAgo(incident.created_at)}</span>
          <button className="expand-btn">
            {expanded ? '▲' : '▼'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="incident-details">
          <div className="details-grid">
            <div className="detail-item">
              <strong>ID:</strong> {incident.id}
            </div>
            <div className="detail-item">
              <strong>Key:</strong> <code>{incident.key}</code>
            </div>
            <div className="detail-item">
              <strong>Created:</strong> {formatDate(incident.created_at)}
            </div>
            {incident.assigned_to && (
              <div className="detail-item">
                <strong>Assigned:</strong> {incident.assigned_to}
              </div>
            )}
            {incident.issue_url && (
              <div className="detail-item">
                <strong>Issue:</strong>{' '}
                <a href={incident.issue_url} target="_blank" rel="noopener noreferrer">
                  View in tracker →
                </a>
              </div>
            )}
          </div>

          {incident.playbooks && incident.playbooks.length > 0 && (
            <div className="playbooks-section">
              <strong>Recommended Playbooks:</strong>
              <div className="playbooks-list">
                {incident.playbooks.map((playbook) => (
                  <span key={playbook} className="playbook-tag">
                    {playbook}
                  </span>
                ))}
              </div>
              
              <button
                className="actions-btn"
                onClick={() => setShowActions(!showActions)}
              >
                {showActions ? '✕ Hide Actions' : '⚡ Run Playbook'}
              </button>
              
              {showActions && <PlaybookActions incident={incident} />}
            </div>
          )}

          {Object.keys(incident.details || {}).length > 0 && (
            <details className="details-json">
              <summary>Technical Details</summary>
              <pre>{JSON.stringify(incident.details, null, 2)}</pre>
            </details>
          )}
        </div>
      )}

      <style>{`
        .incident-card {
          border: 1px solid #dee2e6;
          border-radius: 8px;
          overflow: hidden;
          background: white;
          transition: box-shadow 0.2s;
        }

        .incident-card:hover {
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }

        .incident-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          cursor: pointer;
          user-select: none;
        }

        .incident-title {
          display: flex;
          align-items: center;
          gap: 8px;
          flex: 1;
        }

        .kind-icon {
          font-size: 1.2em;
        }

        .severity-badge,
        .status-badge {
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          color: white;
          text-transform: uppercase;
        }

        .summary {
          font-weight: 500;
          color: #212529;
        }

        .incident-meta {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .time-ago {
          font-size: 0.875rem;
          color: #6c757d;
        }

        .expand-btn {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px;
          color: #6c757d;
        }

        .incident-details {
          padding: 16px;
          border-top: 1px solid #dee2e6;
          background: #f8f9fa;
        }

        .details-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 12px;
          margin-bottom: 16px;
        }

        .detail-item {
          font-size: 0.875rem;
        }

        .detail-item strong {
          color: #495057;
        }

        .detail-item code {
          background: #e9ecef;
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 0.85em;
        }

        .playbooks-section {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid #dee2e6;
        }

        .playbooks-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 8px 0;
        }

        .playbook-tag {
          background: #e7f3ff;
          color: #0066cc;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 0.875rem;
          font-weight: 500;
        }

        .actions-btn {
          background: #0066cc;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          margin-top: 8px;
        }

        .actions-btn:hover {
          background: #0052a3;
        }

        .details-json {
          margin-top: 16px;
          padding: 12px;
          background: white;
          border-radius: 6px;
          border: 1px solid #dee2e6;
        }

        .details-json summary {
          cursor: pointer;
          font-weight: 500;
          color: #495057;
        }

        .details-json pre {
          margin-top: 12px;
          margin-bottom: 0;
          font-size: 0.75rem;
          max-height: 300px;
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
};
