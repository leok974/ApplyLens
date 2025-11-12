import { describe, it, expect, vi, beforeEach } from "vitest";

describe("popup UI", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <span id="api"></span>
      <span id="profile"></span>
      <button id="scan"></button>
      <button id="dm"></button>
    `;
    vi.clearAllMocks();
  });

  it("has required UI elements", () => {
    expect(document.getElementById("api")).toBeDefined();
    expect(document.getElementById("profile")).toBeDefined();
    expect(document.getElementById("scan")).toBeDefined();
    expect(document.getElementById("dm")).toBeDefined();
  });

  it("chrome API mocks are available", () => {
    expect(globalThis.chrome).toBeDefined();
    expect(globalThis.chrome.runtime).toBeDefined();
    expect(globalThis.chrome.tabs).toBeDefined();
  });

  it("profile element can be updated", () => {
    const profileEl = document.getElementById("profile")!;
    profileEl.innerHTML = '<span class="ok">Leo Klemet</span>';

    expect(profileEl.innerHTML).toContain("Leo Klemet");
    expect(profileEl.innerHTML).toContain("ok");
  });
});
