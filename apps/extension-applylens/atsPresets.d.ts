// atsPresets.d.ts — TypeScript definitions for atsPresets.js

import { FieldInfo } from "./schema";

export type ATSPlatform =
  | "Lever"
  | "Greenhouse"
  | "Workday"
  | "Ashby"
  | "SmartRecruiters"
  | null;

export function detectATS(hostname: string): ATSPlatform;

export function applyATSPreset(fields: FieldInfo[], hostname: string): FieldInfo[];
