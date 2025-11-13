import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchLearningProfile } from "../src/learning/profileClient";

const originalFetch = global.fetch;

describe("fetchLearningProfile", () => {
  beforeEach(() => {
    global.fetch = originalFetch;
  });

  it("returns null on non-200", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
    });

    const profile = await fetchLearningProfile("example.com", "abc123");
    expect(profile).toBeNull();
  });

  it("returns null on network error", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

    const profile = await fetchLearningProfile("example.com", "abc123");
    expect(profile).toBeNull();
  });

  it("maps backend snake_case fields into LearningProfile", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        host: "example.com",
        schema_hash: "abc123",
        canonical_map: { "input[name='q1']": "first_name" },
        style_hint: { gen_style_id: "concise_bullets_v2", confidence: 0.9 },
      }),
    });

    const profile = await fetchLearningProfile("example.com", "abc123");
    expect(profile).not.toBeNull();
    expect(profile!.host).toBe("example.com");
    expect(profile!.schemaHash).toBe("abc123");
    expect(profile!.canonicalMap["input[name='q1']"]).toBe("first_name");
    expect(profile!.styleHint?.genStyleId).toBe("concise_bullets_v2");
    expect(profile!.styleHint?.confidence).toBe(0.9);
  });

  it("handles missing optional fields gracefully", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        host: "example.com",
        schema_hash: "abc123",
        canonical_map: {},
        style_hint: null,
      }),
    });

    const profile = await fetchLearningProfile("example.com", "abc123");
    expect(profile).not.toBeNull();
    expect(profile!.canonicalMap).toEqual({});
    expect(profile!.styleHint).toBeNull();
  });

  it("constructs correct query URL", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        host: "test.com",
        schema_hash: "hash456",
        canonical_map: {},
        style_hint: null,
      }),
    });
    global.fetch = mockFetch;

    await fetchLearningProfile("test.com", "hash456");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const callUrl = mockFetch.mock.calls[0][0];
    expect(callUrl).toContain("/api/extension/learning/profile");
    expect(callUrl).toContain("host=test.com");
    expect(callUrl).toContain("schema_hash=hash456");
  });
});
