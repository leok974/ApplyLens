import { describe, it, expect } from "vitest";
import {
  toFieldRows,
  getAcceptedRows,
  countManualEdits,
  validateRequiredFields,
} from "../src/answers/rows";
import type { BackendAnswersPayload } from "../src/types/answers";

describe("toFieldRows", () => {
  it("maps backend answers into field rows with defaults", () => {
    const payload: BackendAnswersPayload = {
      answers: {
        first_name: "Testy",
        last_name: "McTest",
      },
      fields: [
        {
          selector: "input[name='q1']",
          semantic_key: "first_name",
          label: "First name",
        },
        {
          selector: "input[name='q2']",
          semantic_key: "last_name",
          label: "Last name",
        },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows).toHaveLength(2);
    expect(rows[0]).toMatchObject({
      selector: "input[name='q1']",
      semanticKey: "first_name",
      label: "First name",
      suggestedText: "Testy",
      accepted: true,
      source: "profile",
    });
    expect(rows[1]).toMatchObject({
      selector: "input[name='q2']",
      semanticKey: "last_name",
      label: "Last name",
      suggestedText: "McTest",
      accepted: true,
      source: "profile",
    });
  });

  it("defaults to empty string if answer not found", () => {
    const payload: BackendAnswersPayload = {
      answers: {},
      fields: [
        {
          selector: "input[name='q1']",
          semantic_key: "first_name",
          label: "First name",
        },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows[0].suggestedText).toBe("");
    expect(rows[0].source).toBe("heuristic");
  });

  it("preserves confidence level from backend", () => {
    const payload: BackendAnswersPayload = {
      answers: { email: "test@example.com" },
      fields: [
        {
          selector: "input[name='email']",
          semantic_key: "email",
          label: "Email",
          confidence: "high",
        },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows[0].confidence).toBe("high");
  });

  it("treats whitespace-only answers as heuristic", () => {
    const payload: BackendAnswersPayload = {
      answers: { first_name: "   " },
      fields: [
        {
          selector: "input[name='fname']",
          semantic_key: "first_name",
          label: "First Name",
        },
      ],
    };

    const rows = toFieldRows(payload);

    expect(rows[0].source).toBe("heuristic");
  });
});

describe("getAcceptedRows", () => {
  it("filters to only accepted rows", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First",
        suggestedText: "John",
        accepted: true,
      },
      {
        selector: "input[name='q2']",
        semanticKey: "last_name",
        label: "Last",
        suggestedText: "Doe",
        accepted: false,
      },
      {
        selector: "input[name='q3']",
        semanticKey: "email",
        label: "Email",
        suggestedText: "john@example.com",
        accepted: true,
      },
    ];

    const accepted = getAcceptedRows(rows);

    expect(accepted).toHaveLength(2);
    expect(accepted[0].semanticKey).toBe("first_name");
    expect(accepted[1].semanticKey).toBe("email");
  });

  it("returns empty array when no rows accepted", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First",
        suggestedText: "John",
        accepted: false,
      },
    ];

    const accepted = getAcceptedRows(rows);

    expect(accepted).toHaveLength(0);
  });
});

describe("countManualEdits", () => {
  it("counts rows with source=manual", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First",
        suggestedText: "John",
        accepted: true,
        source: "profile" as const,
      },
      {
        selector: "input[name='q2']",
        semanticKey: "last_name",
        label: "Last",
        suggestedText: "Doe (edited)",
        accepted: true,
        source: "manual" as const,
      },
      {
        selector: "input[name='q3']",
        semanticKey: "email",
        label: "Email",
        suggestedText: "custom@example.com",
        accepted: true,
        source: "manual" as const,
      },
    ];

    const count = countManualEdits(rows);

    expect(count).toBe(2);
  });

  it("returns 0 when no manual edits", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First",
        suggestedText: "John",
        accepted: true,
        source: "profile" as const,
      },
    ];

    const count = countManualEdits(rows);

    expect(count).toBe(0);
  });
});

describe("validateRequiredFields", () => {
  it("detects missing required fields", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First Name",
        suggestedText: "John",
        accepted: true,
      },
      {
        selector: "input[name='q2']",
        semanticKey: "last_name",
        label: "Last Name",
        suggestedText: "",
        accepted: true,
      },
      {
        selector: "input[name='q3']",
        semanticKey: "email",
        label: "Email",
        suggestedText: "john@example.com",
        accepted: true,
      },
    ];

    const result = validateRequiredFields(rows, [
      "first_name",
      "last_name",
      "email",
    ]);

    expect(result.isValid).toBe(false);
    expect(result.missing).toEqual(["Last Name"]);
  });

  it("passes when all required fields have values", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First Name",
        suggestedText: "John",
        accepted: true,
      },
      {
        selector: "input[name='q2']",
        semanticKey: "last_name",
        label: "Last Name",
        suggestedText: "Doe",
        accepted: true,
      },
    ];

    const result = validateRequiredFields(rows, ["first_name", "last_name"]);

    expect(result.isValid).toBe(true);
    expect(result.missing).toEqual([]);
  });

  it("treats whitespace as missing", () => {
    const rows = [
      {
        selector: "input[name='q1']",
        semanticKey: "first_name",
        label: "First Name",
        suggestedText: "   ",
        accepted: true,
      },
    ];

    const result = validateRequiredFields(rows, ["first_name"]);

    expect(result.isValid).toBe(false);
    expect(result.missing).toEqual(["First Name"]);
  });
});
