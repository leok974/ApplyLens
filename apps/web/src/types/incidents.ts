/**
 * Incident Types - Phase 5.4 PR4
 */

export interface Incident {
  id: number;
  kind: 'invariant' | 'budget' | 'planner';
  key: string;
  severity: 'sev1' | 'sev2' | 'sev3' | 'sev4';
  status: 'open' | 'acknowledged' | 'mitigated' | 'resolved' | 'closed';
  summary: string;
  details: Record<string, any>;
  playbooks: string[];
  issue_url?: string;
  assigned_to?: string;
  created_at: string;
  acknowledged_at?: string;
  mitigated_at?: string;
  resolved_at?: string;
  closed_at?: string;
  metadata?: Record<string, any>;
}

export interface IncidentAction {
  id: number;
  incident_id: number;
  action_type: string;
  params: Record<string, any>;
  dry_run: boolean;
  status: string;
  result?: Record<string, any>;
  approved_by?: string;
  created_at?: string;
}

export interface ActionRequest {
  action_type: string;
  params: Record<string, any>;
  approved_by?: string;
}

export interface ActionResult {
  status: string;
  message: string;
  details: Record<string, any>;
  estimated_duration?: string;
  estimated_cost?: number;
  changes: string[];
  actual_duration?: number;
  logs_url?: string;
  rollback_available: boolean;
  rollback_action?: {
    action_type: string;
    params: Record<string, any>;
  };
}

export interface AvailableAction {
  action_type: string;
  display_name: string;
  description: string;
  params: Record<string, any>;
  requires_approval: boolean;
}
