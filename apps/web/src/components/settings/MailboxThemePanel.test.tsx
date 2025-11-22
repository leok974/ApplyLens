import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MailboxThemeProvider } from "@/themes/mailbox/context";
import { useMailboxTheme } from "@/hooks/useMailboxTheme";
// NOTE: We import the Inner version to avoid nested providers.
// MailboxThemePanel wraps itself in MailboxThemeProvider, but our test needs
// a single shared provider for both the panel and ChatThemeProbe.
import { MailboxThemePanelInner } from "@/components/settings/MailboxThemePanel";

// This mirrors the wrapper div you should have around <MailChat />
// in ChatPageInner.
function ChatThemeProbe() {
  const { themeId } = useMailboxTheme();

  return (
    <div data-testid="chat-root" data-mailbox-theme={themeId}>
      Chat
    </div>
  );
}

function AppUnderTest() {
  return (
    <MailboxThemeProvider>
      <div>
        <MailboxThemePanelInner />
        <ChatThemeProbe />
      </div>
    </MailboxThemeProvider>
  );
}

describe("Mailbox theme end-to-end (Settings ↔ Chat)", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("updates chat theme when Banana Pro is selected", async () => {
    render(<AppUnderTest />);

    const chatRoot = screen.getByTestId("chat-root");
    // default should be classic
    expect(chatRoot.getAttribute("data-mailbox-theme")).toBe("classic");

    // Find and click the actual radio button input
    const bananaRadio = screen.getByRole("radio", { name: /Banana Pro.*Dark SaaS cockpit/i });
    fireEvent.click(bananaRadio);

    // Wait for state update
    await new Promise(resolve => setTimeout(resolve, 0));

    expect(chatRoot.getAttribute("data-mailbox-theme")).toBe("bananaPro");
  });

  it("updates chat theme when Deep Space is selected", async () => {
    render(<AppUnderTest />);

    const chatRoot = screen.getByTestId("chat-root");
    
    // Find and click the actual radio button
    const deepSpaceRadio = screen.getByRole("radio", { name: /Deep Space Cockpit.*Nebula-backed/i });
    fireEvent.click(deepSpaceRadio);

    await new Promise(resolve => setTimeout(resolve, 0));

    expect(chatRoot.getAttribute("data-mailbox-theme")).toBe("deepSpace");
  });
});
