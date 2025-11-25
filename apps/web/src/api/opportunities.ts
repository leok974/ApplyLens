/**
 * Resume & Opportunities - API Client
 *
 * Type-safe client for resume upload and job opportunities endpoints.
 */

import { apiFetch } from '@/lib/apiBase';

/**
 * Resume API
 */

export interface ResumeProfile {
  id: number;
  owner_email: string;
  source: 'upload';  // Always 'upload' - no generation
  is_active: boolean;
  headline: string | null;
  summary: string | null;
  skills: string[] | null;
  experiences: Array<{
    company: string;
    role: string;
    duration: string;
    description?: string;
  }> | null;
  projects: Array<{
    name: string;
    description: string;
    tech_stack?: string[];
  }> | null;
  created_at: string;
  updated_at: string;
}

/**
 * Upload a resume file (PDF, DOCX, or TXT).
 *
 * @example
 * ```ts
 * const file = document.querySelector('input[type="file"]').files[0];
 * const resume = await uploadResume(file);
 * ```
 */
export async function uploadResume(file: File): Promise<ResumeProfile> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiFetch('/resume/upload', {
    method: 'POST',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: formData,
  });

  return response as ResumeProfile;
}

/**
 * Get the current active resume profile.
 *
 * Returns null if no active resume exists.
 *
 * @example
 * ```ts
 * const resume = await getCurrentResume();
 * if (resume) {
 *   console.log(`Active resume: ${resume.headline}`);
 * }
 * ```
 */
export async function getCurrentResume(): Promise<ResumeProfile | null> {
  const response = await apiFetch('/resume/current');
  return response as ResumeProfile | null;
}

/**
 * Activate a specific resume profile, deactivating others.
 *
 * @example
 * ```ts
 * const resume = await activateResume(7);
 * ```
 */
export async function activateResume(profileId: number): Promise<ResumeProfile> {
  const response = await apiFetch(`/resume/activate/${profileId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
  });

  return response as ResumeProfile;
}

/**
 * List all resume profiles for the authenticated user.
 *
 * @example
 * ```ts
 * const resumes = await listResumes();
 * ```
 */
export async function listResumes(): Promise<ResumeProfile[]> {
  const response = await apiFetch('/resume/all');
  return response as ResumeProfile[];
}

/**
 * Opportunities API
 */

export interface JobOpportunity {
  id: number;
  owner_email: string;
  source: string;  // 'indeed', 'linkedin', 'handshake', etc.
  title: string;
  company: string;
  location: string | null;
  remote_flag: boolean | null;
  salary_text: string | null;
  level: string | null;
  tech_stack: string[] | null;
  apply_url: string | null;
  posted_at: string | null;
  created_at: string;
  // Match data (if available)
  match_bucket: 'perfect' | 'strong' | 'possible' | 'skip' | null;
  match_score: number | null;
}

export interface OpportunityDetail extends JobOpportunity {
  source_message_id: string | null;
  updated_at: string;
  match: {
    id: number;
    bucket: 'perfect' | 'strong' | 'possible' | 'skip';
    score: number;
    reasons: string[];
    missing_skills: string[];
    resume_tweaks: string[];
    created_at: string;
    updated_at: string;
  } | null;
}

/**
 * List job opportunities for the authenticated user.
 *
 * @example
 * ```ts
 * const opportunities = await listOpportunities({
 *   source: 'linkedin',
 *   matchBucket: 'strong',
 *   limit: 50
 * });
 * ```
 */
export async function listOpportunities(params?: {
  source?: string;
  company?: string;
  matchBucket?: 'perfect' | 'strong' | 'possible' | 'skip';
  limit?: number;
  offset?: number;
}): Promise<JobOpportunity[]> {
  const queryParams = new URLSearchParams();

  if (params?.source) {
    queryParams.set('source', params.source);
  }
  if (params?.company) {
    queryParams.set('company', params.company);
  }
  if (params?.matchBucket) {
    queryParams.set('match_bucket', params.matchBucket);
  }
  if (params?.limit) {
    queryParams.set('limit', params.limit.toString());
  }
  if (params?.offset) {
    queryParams.set('offset', params.offset.toString());
  }

  const url = queryParams.toString()
    ? `/opportunities?${queryParams.toString()}`
    : '/opportunities';

  const response = await apiFetch(url);
  return response as JobOpportunity[];
}

/**
 * Get detailed information for a specific opportunity.
 *
 * @example
 * ```ts
 * const detail = await getOpportunityDetail(42);
 * if (detail.match) {
 *   console.log(`Match: ${detail.match.bucket} (${detail.match.score})`);
 * }
 * ```
 */
export async function getOpportunityDetail(opportunityId: number): Promise<OpportunityDetail> {
  const response = await apiFetch(`/opportunities/${opportunityId}`);
  return response as OpportunityDetail;
}

/**
 * Batch Role Match API
 */

export interface RoleMatchBatchItem {
  opportunity_id: number;
  match_bucket: string;
  match_score: number;
}

export interface RoleMatchBatchResponse {
  processed: number;
  items: RoleMatchBatchItem[];
}

/**
 * Run batch role matching on all unmatched opportunities.
 *
 * @example
 * ```ts
 * const result = await runBatchRoleMatch(50);
 * console.log(`Matched ${result.processed} opportunities`);
 * ```
 */
export async function runBatchRoleMatch(limit = 50): Promise<RoleMatchBatchResponse> {
  const response = await apiFetch('/v2/agent/role-match/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ limit }),
  });

  if (!response) {
    throw new Error('Failed to batch match opportunities');
  }

  return response as RoleMatchBatchResponse;
}
