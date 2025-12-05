// schema.d.ts — TypeScript definitions for schema.js

export type CanonicalField =
  | "full_name"
  | "first_name"
  | "last_name"
  | "email"
  | "phone"
  | "location"
  | "linkedin"
  | "github"
  | "portfolio"
  | "website"
  | "headline"
  | "summary"
  | "cover_letter"
  | "salary_expectation"
  | "visa_status"
  | "relocation"
  | "remote_preference"
  | "years_experience"
  | "work_authorization"
  | "notice_period"
  | "pronouns"
  | "diversity_gender"
  | "diversity_race"
  | "diversity_veteran"
  | "diversity_disability"
  | "referral_source"
  | "how_hear";

export type FieldType =
  | "text"
  | "textarea"
  | "select"
  | "checkbox"
  | "radio"
  | "email"
  | "tel"
  | "url"
  | "file"
  | "number";

export interface FieldInfo {
  canonical: CanonicalField | null;
  labelText: string;
  nameAttr: string;
  idAttr: string;
  type: FieldType;
  selector: string;
  value: string;
  placeholder: string;
}

export function inferCanonicalField(
  labelText: string,
  nameAttr: string,
  idAttr: string,
  placeholder: string,
  inputType: string
): CanonicalField | null;

export const CORE_CANONICAL: Set<CanonicalField>;

export function schemaHash(fields: FieldInfo[]): string;
