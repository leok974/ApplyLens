export type RiskFlag = {
  signal: string;
  evidence: string;
  weight: number;
};

export type RiskResult = {
  risk_score: number;
  quarantined: boolean;
  flags: RiskFlag[];
};

export type SecurityStats = {
  highRiskCount: number;
  quarantinedCount: number;
  lastScanAt?: string;
};

export type SecurityPolicies = {
  autoQuarantineHighRisk: boolean;
  autoArchiveExpiredPromos: boolean;
  autoUnsubscribeInactive: { enabled: boolean; threshold: number }; // N in 60d
};
