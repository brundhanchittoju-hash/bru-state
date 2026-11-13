import { test, expect } from "@playwright/test";

test.describe("Phase 6: Statutory Reports E2E Workflow", () => {
  test("generates preliminary report from case detail and verifies preview", async ({ page }) => {
    // 1. Login as Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AuditorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Open Case Detail
    await page.goto("/cases");
    await page.waitForSelector("table tbody tr");
    await page.click("table tbody tr:first-child");
    await expect(page).toHaveURL(/.*cases\/.+/);

    // 3. Switch to Reports tab
    await page.click("button:has-text('Statutory Reports')");
    await expect(page.locator("text=Statutory Audit Reports & Certificates")).toBeVisible();

    // 4. Click Generate Report
    const genBtn = page.locator("button:has-text('Generate Report'), button:has-text('Generate First Report')").first();
    await genBtn.click();

    // 5. Checklist modal
    await expect(page.locator("text=Generate Statutory Audit Report")).toBeVisible();
    await expect(page.locator("text=Report Type / Stage")).toBeVisible();

    // 6. Submit Generation
    await page.click("button:has-text('Generate PDF Report')");

    // 7. Verify toast and report in table
    await expect(page.locator("text=Statutory PDF report generated successfully")).toBeVisible({ timeout: 15000 });
    await expect(page.locator("text=RPT-").first()).toBeVisible();

    // 8. Test Preview Modal
    await page.click("button:has-text('Preview PDF')");
    await expect(page.locator("iframe")).toBeVisible();
    await page.click("button >> svg.lucide-x");
  });

  test("views reports listing and opens public verification seal", async ({ page, browser }) => {
    // 1. Login as Senior Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to /reports
    await page.goto("/reports");
    await expect(page.locator("text=Statutory Audit Reports").first()).toBeVisible();
    await expect(page.locator("text=Total Reports")).toBeVisible();

    // 3. Verify at least one report exists
    await page.waitForSelector("table tbody tr");
    const firstReportId = await page.locator("table tbody tr:first-child td span.font-mono").first().innerText();
    expect(firstReportId).toContain("RPT-");

    // 4. Open Public QR dialog
    await page.click("table tbody tr:first-child button[title='QR & Public Verification Seal']");
    await expect(page.locator("text=Public Verification Seal")).toBeVisible();
    await expect(page.locator("text=Public Verification Link:")).toBeVisible();

    // 5. Open public verification page unauthenticated in clean browser context
    const publicContext = await browser.newContext();
    const publicPage = await publicContext.newPage();
    await publicPage.goto(`/verify/${firstReportId.trim()}`);

    // 6. Verify zero-knowledge portal
    await expect(publicPage.locator("text=GOVERNMENT OF KARNATAKA").first()).toBeVisible();
    await expect(publicPage.locator("text=Public Verification Portal")).toBeVisible();
    await expect(publicPage.locator("text=Zero-Knowledge Guarantee:")).toBeVisible();
    await expect(publicPage.locator("text=Verify Document Authenticity")).toBeVisible();
    await expect(publicPage.locator(`text=${firstReportId.trim()}`)).toBeVisible();

    await publicContext.close();
  });
});
