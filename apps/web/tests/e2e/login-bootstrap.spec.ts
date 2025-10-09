import { test, expect } from "@playwright/test";
import path from "node:path";

/**
 * Bootstrap an authenticated storage state for auth-enabled tests.
 * This spec is NO-OP unless RUN_LOGIN=1
 *
 * ENV VARS:
 *  RUN_LOGIN=1                      // enable this spec to actually run
 *  LOGIN_URL=/login                 // relative path to login page (default /login)
 *  LOGIN_USER=you@example.com
 *  LOGIN_PASS=secret
 *  LOGIN_USER_SELECTOR=[name="email"]         // default selector
 *  LOGIN_PASS_SELECTOR=[name="password"]      // default selector
 *  LOGIN_SUBMIT_SELECTOR=button[type="submit"]// default selector
 *  LOGIN_SUCCESS_URL=/dashboard               // optional: assert URL contains
 *  LOGIN_SUCCESS_SELECTOR=[data-testid="app-shell"] // optional: assert element visible
 *  STORAGE_STATE=tests/.auth/state.json       // path to write storage state (default matches config)
 */

const shouldRun = process.env.RUN_LOGIN === "1";
test.skip(!shouldRun, "Set RUN_LOGIN=1 to execute login bootstrap.");

const LOGIN_URL = process.env.LOGIN_URL || "/login";
const LOGIN_USER = process.env.LOGIN_USER || "";
const LOGIN_PASS = process.env.LOGIN_PASS || "";
const SEL_USER = process.env.LOGIN_USER_SELECTOR || '[name="email"]';
const SEL_PASS = process.env.LOGIN_PASS_SELECTOR || '[name="password"]';
const SEL_SUBMIT = process.env.LOGIN_SUBMIT_SELECTOR || 'button[type="submit"]';
const SUCCESS_URL = process.env.LOGIN_SUCCESS_URL; // optional
const SUCCESS_SELECTOR = process.env.LOGIN_SUCCESS_SELECTOR; // optional
const STORAGE_STATE = process.env.STORAGE_STATE || "tests/.auth/state.json";

test("bootstrap auth storageState", async ({ page }) => {
  test.skip(!LOGIN_USER || !LOGIN_PASS, "LOGIN_USER and LOGIN_PASS are required.");

  // Go to login
  await page.goto(LOGIN_URL);
  await page.waitForSelector(SEL_USER, { state: "visible" });

  // Fill form
  await page.fill(SEL_USER, LOGIN_USER);
  await page.fill(SEL_PASS, LOGIN_PASS);
  await Promise.all([
    page.waitForLoadState("networkidle"),
    page.click(SEL_SUBMIT),
  ]);

  // Optional success checks
  if (SUCCESS_SELECTOR) {
    await expect(page.locator(SUCCESS_SELECTOR)).toBeVisible({ timeout: 10_000 });
  }
  if (SUCCESS_URL) {
    await expect(page).toHaveURL(new RegExp(SUCCESS_URL.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")));
  }

  // Persist storage state for auth project
  const statePath = path.resolve(process.cwd(), STORAGE_STATE);
  await page.context().storageState({ path: statePath });
  // Sanity log in report
  console.log(`[login-bootstrap] Wrote storageState → ${statePath}`);
});
