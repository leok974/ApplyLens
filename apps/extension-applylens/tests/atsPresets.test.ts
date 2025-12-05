// tests/atsPresets.test.ts — Test ATS-specific field detection

import { describe, it, expect } from "vitest";
import { detectATS, applyATSPreset } from "../atsPresets.js";
import type { FieldInfo, FieldType, CanonicalField } from "../schema.d.ts";

describe("detectATS", () => {
  it("should detect Lever", () => {
    expect(detectATS("jobs.lever.co")).toBe("Lever");
    expect(detectATS("jobs.lever.co")).toBe("Lever");
  });

  it("should detect Greenhouse", () => {
    expect(detectATS("boards.greenhouse.io")).toBe("Greenhouse");
    expect(detectATS("acme.greenhouse.io")).toBe("Greenhouse");
  });

  it("should detect Workday", () => {
    expect(detectATS("company.myworkdayjobs.com")).toBe("Workday");
    expect(detectATS("company.wd1.myworkdayjobs.com")).toBe("Workday");
    expect(detectATS("company.wd5.myworkdayjobs.com")).toBe("Workday");
  });

  it("should detect Ashby", () => {
    expect(detectATS("jobs.ashbyhq.com")).toBe("Ashby");
    expect(detectATS("company.ashbyhq.com")).toBe("Ashby");
  });

  it("should detect SmartRecruiters", () => {
    expect(detectATS("jobs.smartrecruiters.com")).toBe("SmartRecruiters");
    expect(detectATS("careers.smartrecruiters.com")).toBe("SmartRecruiters");
  });

  it("should return null for unknown platforms", () => {
    expect(detectATS("example.com")).toBe(null);
    expect(detectATS("jobs.example.com")).toBe(null);
  });
});

describe("applyATSPreset - Lever", () => {
  it("should detect cover letter in Additional Information", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Additional Information",
        nameAttr: "cards[abc][field5]",
        idAttr: "",
        type: "textarea" as FieldType,
        selector: "textarea[name='cards[abc][field5]']",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "jobs.lever.co");
    expect(patched[0].canonical).toBe("cover_letter");
  });

  it("should detect full name in field0", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Name",
        nameAttr: "cards[abc][field0]",
        idAttr: "",
        type: "text" as FieldType,
        selector: "input[name='cards[abc][field0]']",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "jobs.lever.co");
    expect(patched[0].canonical).toBe("full_name");
  });
});

describe("applyATSPreset - Greenhouse", () => {
  it("should detect cover_letter field by ID", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Cover Letter",
        nameAttr: "",
        idAttr: "cover_letter",
        type: "textarea" as FieldType,
        selector: "#cover_letter",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "boards.greenhouse.io");
    expect(patched[0].canonical).toBe("cover_letter");
  });

  it("should skip file upload fields", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Resume/CV",
        nameAttr: "resume",
        idAttr: "",
        type: "file" as FieldType,
        selector: "input[type='file'][name='resume']",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "boards.greenhouse.io");
    expect(patched[0].canonical).toBe(null);
  });
});

describe("applyATSPreset - Workday", () => {
  it("should detect email from clean label", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Email Address",
        nameAttr: "",
        idAttr: "input-1",
        type: "email" as FieldType,
        selector: "#input-1",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "company.myworkdayjobs.com");
    expect(patched[0].canonical).toBe("email");
  });

  it("should detect phone from label", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Phone Number",
        nameAttr: "",
        idAttr: "input-2",
        type: "tel" as FieldType,
        selector: "#input-2",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "wd1.myworkdayjobs.com");
    expect(patched[0].canonical).toBe("phone");
  });

  it("should skip complex address fields", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Street Address Line 1",
        nameAttr: "",
        idAttr: "input-10",
        type: "text" as FieldType,
        selector: "#input-10",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "company.myworkdayjobs.com");
    expect(patched[0].canonical).toBe(null);
  });
});

describe("applyATSPreset - Ashby", () => {
  it("should detect cover letter from 'Why' questions", () => {
    const fields: FieldInfo[] = [
      {
        canonical: null,
        labelText: "Why do you want to work at our company?",
        nameAttr: "",
        idAttr: "",
        type: "textarea" as FieldType,
        selector: "textarea[name='question_1']",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "jobs.ashbyhq.com");
    expect(patched[0].canonical).toBe("cover_letter");
  });
});

describe("applyATSPreset - Generic", () => {
  it("should return fields unchanged for unknown platforms", () => {
    const fields: FieldInfo[] = [
      {
        canonical: "email" as CanonicalField,
        labelText: "Email",
        nameAttr: "email",
        idAttr: "",
        type: "email" as FieldType,
        selector: "input[name='email']",
        value: "",
        placeholder: "",
      },
    ];

    const patched = applyATSPreset(fields, "random.example.com");
    expect(patched).toEqual(fields);
  });
});
