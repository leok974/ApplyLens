/* Simple, typed API helpers for security routes */
import { RiskResult, SecurityStats, SecurityPolicies } from "@/types/security";

export async function rescanEmail(emailId: string): Promise<RiskResult> {
  const r = await fetch(`/api/security/rescan/${encodeURIComponent(emailId)}`, {
    method: "POST",
    credentials: "include",
  });
  if (!r.ok) throw new Error(`Rescan failed: ${r.status}`);
  const data = await r.json();
  // Expect service to return RiskResult or { data: RiskResult }
  return (data?.data ?? data) as RiskResult;
}

export async function getSecurityStats(): Promise<SecurityStats> {
  const r = await fetch(`/api/security/stats`, { credentials: "include" });
  if (!r.ok) throw new Error(`Stats failed: ${r.status}`);
  return await r.json();
}

/** Policy endpoints are placeholders; wire to your backend when ready */
export async function getPolicies(): Promise<SecurityPolicies> {
  const r = await fetch(`/api/policy/security`, { credentials: "include" });
  if (!r.ok) {
    // safe defaults
    return {
      autoQuarantineHighRisk: true,
      autoArchiveExpiredPromos: true,
      autoUnsubscribeInactive: { enabled: false, threshold: 10 },
    };
  }
  return await r.json();
}

export async function savePolicies(p: SecurityPolicies): Promise<void> {
  const r = await fetch(`/api/policy/security`, {
    method: "PUT",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(p),
  });
  if (!r.ok) throw new Error(`Save policies failed: ${r.status}`);
}

/** Bulk action: rescan multiple emails by ID */
export async function bulkRescan(ids: string[]): Promise<{ updated: number; total: number }> {
  const r = await fetch(`/api/security/bulk/rescan`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ids),
  });
  if (!r.ok) throw new Error(`Bulk rescan failed: ${r.status}`);
  return await r.json();
}

/** Bulk action: quarantine multiple emails by ID */
export async function bulkQuarantine(ids: string[]): Promise<{ quarantined: number; total: number }> {
  const r = await fetch(`/api/security/bulk/quarantine`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ids),
  });
  if (!r.ok) throw new Error(`Bulk quarantine failed: ${r.status}`);
  return await r.json();
}

/** Bulk action: release multiple emails from quarantine by ID */
export async function bulkRelease(ids: string[]): Promise<{ released: number; total: number }> {
  const r = await fetch(`/api/security/bulk/release`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(ids),
  });
  if (!r.ok) throw new Error(`Bulk release failed: ${r.status}`);
  return await r.json();
}
