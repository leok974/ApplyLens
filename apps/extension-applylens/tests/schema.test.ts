// tests/schema.test.ts — Test canonical field inference

import { describe, it, expect } from "vitest";
import { inferCanonicalField, isProfileField, isSensitiveField } from "../schema.js";

describe("inferCanonicalField", () => {
  it("should detect email fields", () => {
    expect(inferCanonicalField("Email Address", "", "", "", "email")).toBe("email");
    expect(inferCanonicalField("Your email", "email", "", "", "text")).toBe("email");
    expect(inferCanonicalField("E-mail", "", "user_email", "", "text")).toBe("email");
  });

  it("should detect phone fields", () => {
    expect(inferCanonicalField("Phone Number", "", "", "", "tel")).toBe("phone");
    expect(inferCanonicalField("Mobile", "phone", "", "", "text")).toBe("phone");
    expect(inferCanonicalField("Telephone", "", "tel", "", "text")).toBe("phone");
    expect(inferCanonicalField("Cell phone", "", "", "Enter cell", "text")).toBe("phone");
  });

  it("should detect name fields with proper precedence", () => {
    expect(inferCanonicalField("Full Name", "", "", "", "text")).toBe("full_name");
    expect(inferCanonicalField("Your Name", "name", "", "", "text")).toBe("full_name");
    expect(inferCanonicalField("Legal name", "", "", "", "text")).toBe("full_name");

    expect(inferCanonicalField("First Name", "", "", "", "text")).toBe("first_name");
    expect(inferCanonicalField("Given name", "fname", "", "", "text")).toBe("first_name");

    expect(inferCanonicalField("Last Name", "", "", "", "text")).toBe("last_name");
    expect(inferCanonicalField("Family name", "", "lname", "", "text")).toBe("last_name");
    expect(inferCanonicalField("Surname", "", "", "", "text")).toBe("last_name");
  });

  it("should detect LinkedIn fields", () => {
    expect(inferCanonicalField("LinkedIn Profile", "", "", "", "url")).toBe("linkedin");
    expect(inferCanonicalField("LinkedIn URL", "linkedin", "", "", "text")).toBe("linkedin");
    expect(inferCanonicalField("Your linked-in", "", "", "", "text")).toBe("linkedin");
  });

  it("should detect GitHub fields", () => {
    expect(inferCanonicalField("GitHub Profile", "", "", "", "url")).toBe("github");
    expect(inferCanonicalField("GitHub username", "github", "", "", "text")).toBe("github");
  });

  it("should detect portfolio/website fields", () => {
    expect(inferCanonicalField("Portfolio", "", "", "", "url")).toBe("portfolio");
    expect(inferCanonicalField("Personal site", "portfolio", "", "", "text")).toBe("portfolio");
    expect(inferCanonicalField("Website", "", "", "", "url")).toBe("website");
    expect(inferCanonicalField("Homepage", "", "", "", "text")).toBe("website");
  });

  it("should detect location fields", () => {
    expect(inferCanonicalField("Location", "", "", "", "text")).toBe("location");
    expect(inferCanonicalField("City", "location", "", "", "text")).toBe("location");
    expect(inferCanonicalField("Current location", "", "", "", "text")).toBe("location");
    expect(inferCanonicalField("Where are you located?", "", "", "", "text")).toBe("location");
  });

  it("should detect cover letter fields", () => {
    expect(inferCanonicalField("Cover Letter", "", "", "", "textarea")).toBe("cover_letter");
    expect(inferCanonicalField("Why do you want to join?", "", "", "", "textarea")).toBe("cover_letter");
    expect(inferCanonicalField("Tell us about yourself", "motivation", "", "", "textarea")).toBe("cover_letter");
    expect(inferCanonicalField("Why are you interested?", "", "", "", "text")).toBe("cover_letter");
  });

  it("should detect headline/summary fields", () => {
    expect(inferCanonicalField("Professional Headline", "", "", "", "text")).toBe("headline");
    expect(inferCanonicalField("Tagline", "", "", "", "text")).toBe("headline");

    expect(inferCanonicalField("Summary", "", "", "", "textarea")).toBe("summary");
    expect(inferCanonicalField("Bio", "bio", "", "", "textarea")).toBe("summary");
    expect(inferCanonicalField("About you", "", "", "", "textarea")).toBe("summary");
  });

  it("should detect salary fields", () => {
    expect(inferCanonicalField("Salary Expectation", "", "", "", "text")).toBe("salary_expectation");
    expect(inferCanonicalField("Expected salary", "salary", "", "", "number")).toBe("salary_expectation");
    expect(inferCanonicalField("Compensation", "", "", "", "text")).toBe("salary_expectation");
  });

  it("should detect visa/work authorization fields", () => {
    expect(inferCanonicalField("Visa Status", "", "", "", "text")).toBe("visa_status");
    expect(inferCanonicalField("Work authorization", "visa", "", "", "text")).toBe("visa_status");
    expect(inferCanonicalField("Do you require sponsorship?", "", "", "", "text")).toBe("visa_status");
    expect(inferCanonicalField("Authorized to work?", "", "", "", "text")).toBe("visa_status");
  });

  it("should detect years of experience", () => {
    expect(inferCanonicalField("Years of experience", "", "", "", "number")).toBe("years_experience");
    expect(inferCanonicalField("Experience level", "", "", "", "text")).toBe("years_experience");
  });

  it("should detect remote/relocation preferences", () => {
    expect(inferCanonicalField("Remote work preference", "", "", "", "text")).toBe("remote_preference");
    expect(inferCanonicalField("Work from home", "", "", "", "text")).toBe("remote_preference");

    expect(inferCanonicalField("Willing to relocate?", "", "", "", "text")).toBe("relocation");
    expect(inferCanonicalField("Relocation preference", "", "", "", "text")).toBe("relocation");
  });

  it("should detect diversity fields", () => {
    expect(inferCanonicalField("Pronouns", "", "", "", "text")).toBe("pronouns");
    expect(inferCanonicalField("Preferred pronouns", "", "", "", "text")).toBe("pronouns");

    expect(inferCanonicalField("Gender", "", "", "", "text")).toBe("diversity_gender");
    expect(inferCanonicalField("Gender identity", "", "", "", "text")).toBe("diversity_gender");

    expect(inferCanonicalField("Race/Ethnicity", "", "", "", "text")).toBe("diversity_race");
    expect(inferCanonicalField("Veteran Status", "", "", "", "text")).toBe("diversity_veteran");
    expect(inferCanonicalField("Disability", "", "", "", "text")).toBe("diversity_disability");
  });

  it("should detect referral/source fields", () => {
    expect(inferCanonicalField("Referral", "", "", "", "text")).toBe("referral_source");
    expect(inferCanonicalField("Referred by", "referral", "", "", "text")).toBe("referral_source");

    expect(inferCanonicalField("How did you hear about us?", "", "", "", "text")).toBe("how_hear");
    expect(inferCanonicalField("Where did you find this job?", "", "", "", "text")).toBe("how_hear");
  });

  it("should return null for unknown fields", () => {
    expect(inferCanonicalField("Random field", "", "", "", "text")).toBe(null);
    expect(inferCanonicalField("XYZ", "xyz123", "", "", "text")).toBe(null);
  });

  it("should be case-insensitive", () => {
    expect(inferCanonicalField("EMAIL ADDRESS", "", "", "", "text")).toBe("email");
    expect(inferCanonicalField("FIRST NAME", "", "", "", "text")).toBe("first_name");
    expect(inferCanonicalField("LinkedIn", "", "", "", "text")).toBe("linkedin");
  });

  it("should combine multiple text sources", () => {
    // Label doesn't match, but name attr does
    expect(inferCanonicalField("Your info", "email_address", "", "", "text")).toBe("email");

    // ID matches even if label is vague
    expect(inferCanonicalField("Field 1", "", "first_name", "", "text")).toBe("first_name");

    // Placeholder matches
    expect(inferCanonicalField("", "", "", "Enter your phone", "text")).toBe("phone");
  });
});

describe("isProfileField", () => {
  it("should identify profile fields", () => {
    expect(isProfileField("full_name")).toBe(true);
    expect(isProfileField("email")).toBe(true);
    expect(isProfileField("phone")).toBe(true);
    expect(isProfileField("linkedin")).toBe(true);
    expect(isProfileField("github")).toBe(true);
    expect(isProfileField("location")).toBe(true);
    expect(isProfileField("headline")).toBe(true);
    expect(isProfileField("summary")).toBe(true);
  });

  it("should not identify non-profile fields", () => {
    expect(isProfileField("cover_letter")).toBe(false);
    expect(isProfileField("salary_expectation")).toBe(false);
    expect(isProfileField("visa_status")).toBe(false);
    expect(isProfileField("diversity_gender")).toBe(false);
    expect(isProfileField(null)).toBe(false);
  });
});

describe("isSensitiveField", () => {
  it("should identify sensitive fields", () => {
    expect(isSensitiveField("diversity_gender")).toBe(true);
    expect(isSensitiveField("diversity_race")).toBe(true);
    expect(isSensitiveField("diversity_veteran")).toBe(true);
    expect(isSensitiveField("diversity_disability")).toBe(true);
    expect(isSensitiveField("pronouns")).toBe(true);
    expect(isSensitiveField("salary_expectation")).toBe(true);
  });

  it("should not identify non-sensitive fields", () => {
    expect(isSensitiveField("email")).toBe(false);
    expect(isSensitiveField("full_name")).toBe(false);
    expect(isSensitiveField("cover_letter")).toBe(false);
    expect(isSensitiveField(null)).toBe(false);
  });
});
