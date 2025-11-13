export type ExtApplication = {
  id: number;
  company?: string;
  role?: string;
  job_url?: string;
  source?: string;
  applied_at?: string;
  created_at: string;
};

export type ExtOutreach = {
  id: number;
  company?: string;
  role?: string;
  recruiter_name?: string;
  recruiter_profile_url?: string;
  message_preview?: string;
  sent_at?: string;
  source?: string;
  created_at: string;
};

export async function fetchExtApplications(limit = 10): Promise<ExtApplication[]> {
  const r = await fetch(`/api/extension/applications?limit=${limit}`);
  if (!r.ok) throw new Error(`apps fetch failed: ${r.status}`);
  return r.json();
}

export async function fetchExtOutreach(limit = 10): Promise<ExtOutreach[]> {
  const r = await fetch(`/api/extension/outreach?limit=${limit}`);
  if (!r.ok) throw new Error(`outreach fetch failed: ${r.status}`);
  return r.json();
}

export async function pingProfile(): Promise<boolean> {
  try {
    const r = await fetch(`/api/profile/me`);
    return r.ok;
  } catch {
    return false;
  }
}
