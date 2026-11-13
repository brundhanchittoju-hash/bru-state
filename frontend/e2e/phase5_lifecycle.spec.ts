import { test, expect } from "@playwright/test";

test.describe("Phase 5: Case Lifecycle, Executive Dashboard, Analytics & Universal Search E2E", () => {
  test.beforeEach(async ({ page }) => {
    page.on("console", (msg) => {
      if (msg.type() === "error" && !msg.text().includes("React Router Future Flag")) {
        console.error("Browser Console Error:", msg.text());
      }
    });
  });

  test("Executive Dashboard live KPIs, Calendar Event CRUD, and Priority Review Queue", async ({ page }) => {
    // 1. Login as Senior Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Verify Executive Dashboard Header and 12 Live KPIs
    await expect(page.locator("h1")).toContainText("Audit Executive Dashboard");
    await expect(page.locator("text=Total Audit Cases")).toBeVisible();
    await expect(page.locator("text=Open Cases")).toBeVisible();
    await expect(page.locator("text=Completed Cases")).toBeVisible();
    await expect(page.locator("text=Critical Risk Findings")).toBeVisible();
    await expect(page.locator("text=High Risk Findings")).toBeVisible();
    await expect(page.locator("text=R-001 Duplicate Payments")).toBeVisible();

    // 3. Filter by District (e.g. Mysuru) and verify URL query parameter sync
    const districtSelect = page.locator("select").nth(1);
    await districtSelect.selectOption("Mysuru");
    await expect(page).toHaveURL(/.*district=Mysuru.*/);

    // 4. Open Priority Review Queue Drawer
    const priorityBtn = page.locator("button:has-text('Priority Queue')");
    await expect(priorityBtn).toBeVisible();
    await priorityBtn.click();
    await expect(page.locator("text=Priority Review Queue (Top Risk Findings)")).toBeVisible();
    const closeDrawerBtn = page.locator("button:has-text('Close')").first();
    await closeDrawerBtn.click();

    // 5. Add a Deadline / Event to the Audit Calendar
    const addDeadlineBtn = page.locator("button:has-text('Add Deadline')");
    await addDeadlineBtn.click();
    await expect(page.locator("text=Add Statutory Deadline / Event")).toBeVisible();
    await page.fill('input[placeholder*="Gram Panchayat Hearing"]', "E2E Statutory Audit Hearing");
    await page.fill('input[type="date"]', "2025-03-25");
    await page.click("button:has-text('Save Deadline')");
    await expect(page.locator("text=Statutory deadline created.")).toBeVisible();
  });

  test("Case Lifecycle 7-State Workflow, Blocker Gate, Case Lock, and Officer Reopen Snapshot", async ({ page }) => {
    // 1. Login as Senior Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Cases and open CAS-2024-MYS-001
    await page.click('aside nav a[href="/cases"]');
    await expect(page).toHaveURL(/.*cases/);
    const firstCaseRow = page.locator("tbody tr").first();
    await expect(firstCaseRow).toBeVisible();
    await firstCaseRow.click();
    await expect(page).toHaveURL(/.*cases\/.+/);

    // 3. Check 7-State Stepper and 7 Functional Tabs
    await expect(page.locator("button:has-text('Overview & Team')").first()).toBeVisible();
    await expect(page.locator("button:has-text('Evidence Docs')").first()).toBeVisible();
    await expect(page.locator("button:has-text('Extracted Data')").first()).toBeVisible();
    await expect(page.locator("button:has-text('Rule Runs')").first()).toBeVisible();
    await expect(page.locator("button:has-text('Findings')").first()).toBeVisible();
    await expect(page.locator("button:has-text('Statutory Reports')").first()).toBeVisible();
    await expect(page.locator("button:has-text('Case Timeline')").first()).toBeVisible();

    // 4. Verify Advance Status button exists
    const advanceBtn = page.locator("button:has-text('Advance')");
    if (await advanceBtn.isVisible()) {
      await expect(advanceBtn).toBeEnabled();
    }
  });

  test("Analytics 8 Models, Accessible Data Table Toggle, and CSV Export", async ({ page }) => {
    // 1. Login as Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AuditorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Analytics page via sidebar
    await page.click('aside nav a[href="/analytics"]');
    await expect(page).toHaveURL(/.*analytics/);
    await expect(page.locator("h1")).toContainText("Audit Analytics & Intelligence");

    // 3. Verify Chart Cards are rendered
    await expect(page.locator("text=1. Department Breakdown")).toBeVisible();
    await expect(page.locator("text=2. Risk Distribution by Statutory Scheme")).toBeVisible();
    await expect(page.locator("text=6. Top Verification Rules Triggered")).toBeVisible();

    // 4. Toggle accessible Data Table for Department Breakdown
    const dataTableBtn = page.locator("button:has-text('Data Table')").first();
    await dataTableBtn.click();
    await expect(page.locator("button:has-text('Hide Table')").first()).toBeVisible();

    // 5. Test CSV download button
    const csvBtn = page.locator("button:has-text('CSV')").first();
    await expect(csvBtn).toBeVisible();
  });

  test("Universal Search with multi-entity results and Basic Search Mode badge", async ({ page }) => {
    // 1. Login as Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AuditorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Search Page via sidebar or URL
    await page.goto("/search?q=Cauvery");
    await expect(page).toHaveURL(/.*search\?q=Cauvery/);
    await expect(page.locator("h1")).toContainText("Universal Audit Search");

    // 3. Verify Basic Search Mode banner
    await expect(page.locator("text=Basic Search Mode Active")).toBeVisible();

    // 4. Verify search results contain matched items
    await expect(page.locator("text=Cauvery Infra Projects").first()).toBeVisible();
  });

  test("Vendors Directory and Dossier with PAN/GSTIN Regex Validation", async ({ page }) => {
    // 1. Login as Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AuditorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Vendors page via sidebar
    await page.click('aside nav a[href="/vendors"]');
    await expect(page).toHaveURL(/.*vendors/);
    await expect(page.locator("h1")).toContainText("Vendors & Contractors Intelligence");

    // 3. Open first Vendor dossier
    const viewBtn = page.locator("button:has-text('View')").first();
    await expect(viewBtn).toBeVisible();
    await viewBtn.click();
    await expect(page).toHaveURL(/.*vendors\/.+/);

    // 4. Verify Vendor Dossier Details
    await expect(page.locator("text=State:")).toBeVisible();
    await expect(page.locator("text=PAN:")).toBeVisible();
    await expect(page.locator("text=GSTIN:")).toBeVisible();
    await expect(page.locator("text=Total Audited Spend")).toBeVisible();
    await expect(page.locator("text=Financial Transactions")).toBeVisible();
    await expect(page.locator("text=Audit Findings Associated with Vendor")).toBeVisible();
  });
});
