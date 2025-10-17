/**
 * Playbook Actions - Phase 5.4 PR4
 * 
 * Execute remediation actions with dry-run preview.
 */
import React, { useState, useEffect } from 'react';
import type { Incident, AvailableAction, ActionResult } from '../../types/incidents';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

interface PlaybookActionsProps {
  incident: Incident;
}

export const PlaybookActions: React.FC<PlaybookActionsProps> = ({ incident }) => {
  const [actions, setActions] = useState<AvailableAction[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAction, setSelectedAction] = useState<AvailableAction | null>(null);
  const [dryRunResult, setDryRunResult] = useState<ActionResult | null>(null);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch available actions
  useEffect(() => {
    fetchActions();
  }, [incident.id]);

  const fetchActions = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE}/api/playbooks/incidents/${incident.id}/actions`
      );
      
      if (!response.ok) throw new Error('Failed to fetch actions');
      
      const data = await response.json();
      setActions(data);
    } catch (err) {
      console.error('Error fetching actions:', err);
      setError(err instanceof Error ? err.message : 'Failed to load actions');
    } finally {
      setLoading(false);
    }
  };

  const runDryRun = async (action: AvailableAction) => {
    try {
      setSelectedAction(action);
      setDryRunResult(null);
      setError(null);
      setExecuting(true);

      const response = await fetch(
        `${API_BASE}/api/playbooks/incidents/${incident.id}/actions/dry-run`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_type: action.action_type,
            params: action.params,
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Dry-run failed');
      }

      const result = await response.json();
      setDryRunResult(result);
    } catch (err) {
      console.error('Dry-run error:', err);
      setError(err instanceof Error ? err.message : 'Dry-run failed');
    } finally {
      setExecuting(false);
    }
  };

  const executeAction = async (approved_by?: string) => {
    if (!selectedAction || !dryRunResult) return;

    try {
      setExecuting(true);
      setError(null);

      const response = await fetch(
        `${API_BASE}/api/playbooks/incidents/${incident.id}/actions/execute`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_type: selectedAction.action_type,
            params: selectedAction.params,
            approved_by: approved_by || 'web-user',
          }),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Execution failed');
      }

      const result = await response.json();
      
      // Show success and reset
      alert(`Action executed successfully!\n\n${result.message}`);
      setSelectedAction(null);
      setDryRunResult(null);
    } catch (err) {
      console.error('Execution error:', err);
      setError(err instanceof Error ? err.message : 'Execution failed');
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading actions...</div>;
  }

  if (error && !selectedAction) {
    return <div className="error">Error: {error}</div>;
  }

  if (actions.length === 0) {
    return <div className="no-actions">No actions available</div>;
  }

  return (
    <div className="playbook-actions">
      {!selectedAction ? (
        <div className="actions-list">
          <h6>Available Actions:</h6>
          {actions.map((action) => (
            <div key={action.action_type} className="action-item">
              <div className="action-info">
                <strong>{action.display_name}</strong>
                <p>{action.description}</p>
                {action.requires_approval && (
                  <span className="approval-badge">Requires Approval</span>
                )}
              </div>
              <button
                className="dry-run-btn"
                onClick={() => runDryRun(action)}
                disabled={executing}
              >
                🔍 Dry Run
              </button>
            </div>
          ))}
        </div>
      ) : (
        <div className="dry-run-result">
          <div className="result-header">
            <h6>{selectedAction.display_name}</h6>
            <button onClick={() => {
              setSelectedAction(null);
              setDryRunResult(null);
              setError(null);
            }}>
              ✕ Cancel
            </button>
          </div>

          {executing && !dryRunResult && (
            <div className="loading">Running dry-run...</div>
          )}

          {error && (
            <div className="error">
              <strong>Error:</strong> {error}
            </div>
          )}

          {dryRunResult && (
            <>
              <div className="result-message">
                <strong>Status:</strong> {dryRunResult.status}
                <br />
                <strong>Message:</strong> {dryRunResult.message}
              </div>

              {dryRunResult.estimated_duration && (
                <div className="result-estimate">
                  ⏱️ Estimated duration: {dryRunResult.estimated_duration}
                  {dryRunResult.estimated_cost !== undefined && (
                    <> | 💰 Estimated cost: ${dryRunResult.estimated_cost.toFixed(2)}</>
                  )}
                </div>
              )}

              {dryRunResult.changes && dryRunResult.changes.length > 0 && (
                <div className="result-changes">
                  <strong>Changes:</strong>
                  <ul>
                    {dryRunResult.changes.map((change, idx) => (
                      <li key={idx}>{change}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="action-buttons">
                <button
                  className="execute-btn"
                  onClick={() => {
                    const approver = selectedAction.requires_approval
                      ? prompt('Enter your email to approve:')
                      : undefined;
                    
                    if (!selectedAction.requires_approval || approver) {
                      executeAction(approver);
                    }
                  }}
                  disabled={executing}
                >
                  {executing ? '⏳ Executing...' : '✅ Execute Action'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      <style jsx>{`
        .playbook-actions {
          margin-top: 16px;
          padding: 16px;
          background: white;
          border-radius: 6px;
          border: 1px solid #dee2e6;
        }

        .actions-list h6 {
          margin-bottom: 12px;
          color: #495057;
        }

        .action-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px;
          margin-bottom: 8px;
          background: #f8f9fa;
          border-radius: 6px;
        }

        .action-info {
          flex: 1;
        }

        .action-info strong {
          display: block;
          margin-bottom: 4px;
          color: #212529;
        }

        .action-info p {
          margin: 0;
          font-size: 0.875rem;
          color: #6c757d;
        }

        .approval-badge {
          display: inline-block;
          margin-top: 4px;
          padding: 2px 8px;
          background: #fff3cd;
          color: #856404;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .dry-run-btn,
        .execute-btn {
          background: #0066cc;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          cursor: pointer;
          font-weight: 500;
          white-space: nowrap;
        }

        .dry-run-btn:hover,
        .execute-btn:hover {
          background: #0052a3;
        }

        .dry-run-btn:disabled,
        .execute-btn:disabled {
          background: #6c757d;
          cursor: not-allowed;
        }

        .dry-run-result {
          padding: 16px;
          background: #f8f9fa;
          border-radius: 6px;
        }

        .result-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid #dee2e6;
        }

        .result-header button {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 1.2em;
          color: #6c757d;
        }

        .result-message,
        .result-estimate {
          margin-bottom: 12px;
          font-size: 0.875rem;
        }

        .result-changes {
          margin-bottom: 16px;
        }

        .result-changes ul {
          margin: 8px 0;
          padding-left: 20px;
          font-size: 0.875rem;
        }

        .result-changes li {
          margin-bottom: 4px;
        }

        .action-buttons {
          display: flex;
          gap: 8px;
          margin-top: 16px;
        }

        .loading,
        .error,
        .no-actions {
          padding: 12px;
          text-align: center;
          color: #6c757d;
          font-size: 0.875rem;
        }

        .error {
          color: #dc3545;
          background: #f8d7da;
          border-radius: 6px;
        }
      `}</style>
    </div>
  );
};
