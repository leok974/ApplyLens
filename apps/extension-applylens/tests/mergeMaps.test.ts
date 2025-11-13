import { describe, it, expect } from "vitest";
import { mergeSelectorMaps } from "../src/learning/mergeMaps";

describe("mergeSelectorMaps", () => {
  it("prefers local map on conflicts", () => {
    const server = {
      "input[name='q1']": "first_name",
      "input[name='q2']": "last_name",
    };
    const local = {
      "input[name='q2']": "preferred_last_name",
      "input[name='q3']": "email",
    };

    const merged = mergeSelectorMaps(server, local);

    expect(merged["input[name='q1']"]).toBe("first_name");
    expect(merged["input[name='q2']"]).toBe("preferred_last_name");
    expect(merged["input[name='q3']"]).toBe("email");
  });

  it("returns server map when local is empty", () => {
    const server = {
      "input[name='q1']": "first_name",
      "input[name='q2']": "last_name",
    };
    const local = {};

    const merged = mergeSelectorMaps(server, local);

    expect(merged["input[name='q1']"]).toBe("first_name");
    expect(merged["input[name='q2']"]).toBe("last_name");
  });

  it("returns local map when server is empty", () => {
    const server = {};
    const local = {
      "input[name='q1']": "first_name",
      "input[name='q2']": "last_name",
    };

    const merged = mergeSelectorMaps(server, local);

    expect(merged["input[name='q1']"]).toBe("first_name");
    expect(merged["input[name='q2']"]).toBe("last_name");
  });

  it("handles both maps empty", () => {
    const server = {};
    const local = {};

    const merged = mergeSelectorMaps(server, local);

    expect(merged).toEqual({});
  });
});
