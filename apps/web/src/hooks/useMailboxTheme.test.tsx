import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MailboxThemeProvider } from "@/themes/mailbox/context";
import { useMailboxTheme } from "@/hooks/useMailboxTheme";

describe("useMailboxTheme + MailboxThemeProvider", () => {
  const STORAGE_KEY = "applylens:mailbox-theme";

  beforeEach(() => {
    // reset jsdom localStorage
    window.localStorage.clear();
    vi.restoreAllMocks();
  });

  function wrapper({ children }: { children: React.ReactNode }) {
    return <MailboxThemeProvider>{children}</MailboxThemeProvider>;
  }

  it("uses classic as default when nothing in localStorage", () => {
    const { result } = renderHook(() => useMailboxTheme(), { wrapper });

    expect(result.current.themeId).toBe("classic");
    // theme object should exist
    expect(result.current.theme).toBeDefined();
  });

  it("reads the themeId from localStorage on first mount", () => {
    window.localStorage.setItem(STORAGE_KEY, "bananaPro");

    const { result } = renderHook(() => useMailboxTheme(), { wrapper });

    expect(result.current.themeId).toBe("bananaPro");
  });

  it("writes themeId to localStorage when changed", () => {
    const setItemSpy = vi.spyOn(window.localStorage.__proto__, "setItem");

    const { result } = renderHook(() => useMailboxTheme(), { wrapper });

    act(() => {
      result.current.setThemeId("bananaPro");
    });

    expect(result.current.themeId).toBe("bananaPro");
    expect(setItemSpy).toHaveBeenCalledWith(STORAGE_KEY, "bananaPro");
  });

  it("ignores invalid theme ids", () => {
    const { result } = renderHook(() => useMailboxTheme(), { wrapper });

    act(() => {
      // @ts-expect-error testing invalid value
      result.current.setThemeId("does-not-exist");
    });

    // should still be the default
    expect(result.current.themeId).toBe("classic");
  });
});
