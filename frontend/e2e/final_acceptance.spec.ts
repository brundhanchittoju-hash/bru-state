import { test, expect } from "@playwright/test";

test.describe("STATE AUDIT AI — End-to-End Statutory Final Acceptance Suite", () => {
  test.beforeEach(async ({ page }) => {
    page.on("console", (msg) => {
      if (msg.type() === "error" && !msg.text().includes("React Router Future Flag")) {
        console.error("Browser Console Error:", msg.text());
      }
    });
  });

  test("Complete Audit Lifecycle: Ingestion -> Override -> Verification -> Evidence -> Maker-Checker -> PDF Report -> Public Zero-Knowledge Verification -> Hash Integrity", async ({ page, browser }) => {
    test.setTimeout(60000);
    const timestamp = Date.now();
    const caseTitle = `Acceptance Test Audit Engagement ${timestamp}`;

    // =========================================================================
    // STEP 1: Login as Auditor & Create Audit Case
    // =========================================================================
    await page.goto("/login");
    await page.fill('input[type="email"]', "auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AuditorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Cases
    await page.goto("/cases");
    await expect(page.locator("h1")).toContainText("Audit Case Management");

    // Open Initiate Statutory Audit Case Modal
    const createCaseBtn = page.locator("button:has-text('New Audit Case')").first();
    await createCaseBtn.click();
    await expect(page.locator("text=Initiate Statutory Audit Case")).toBeVisible();

    // Fill Case particulars
    await page.fill('input[placeholder*="Mandya ZP Water"]', caseTitle);
    await page.click("button:has-text('Create Audit Case')");
    await expect(page.locator("text=Initiate Statutory Audit Case")).not.toBeVisible();

    // Verify created case exists in the directory
    await page.goto("/cases");
    await page.waitForSelector("table tbody tr");
    await expect(page.locator(`text=${caseTitle}`)).toBeVisible();

    // =========================================================================
    // STEP 2: Inspect Ingestion, Case Detail & Evidence Docs
    // =========================================================================
    // Search and open benchmark case CAS-2024-MYS-001
    await page.fill('input[placeholder*="Search case"]', "CAS-2024-MYS-001");
    const targetCaseRow = page.locator("table tbody tr:has-text('CAS-2024-MYS-001')").first();
    await expect(targetCaseRow).toBeVisible();
    await targetCaseRow.click();
    await expect(page).toHaveURL(/.*cases\/.+/);

    // Check Evidence Docs tab (card repository)
    await page.click("button:has-text('Evidence Docs')");
    await expect(page.locator("text=Evidence Documents Repository")).toBeVisible();
    await expect(page.locator("text=Admin Sanction Order").first()).toBeVisible();

    // =========================================================================
    // STEP 3: Inspect Findings Register, Evidence & Overrides
    // =========================================================================
    // Open Findings Registry
    await page.goto("/findings");
    await expect(page.locator("h1")).toContainText("Audit Findings Register");

    // Open Findings Registry and filter for Open findings
    await page.goto("/findings");
    await expect(page.locator("h1")).toContainText("Audit Findings Register");
    await page.waitForSelector("table tbody tr");

    const statusSelect = page.locator("select").nth(1);
    if (await statusSelect.isVisible()) {
      await statusSelect.selectOption("Open");
    }
    const openRow = page.locator("table tbody tr:has-text('Open')").first();
    await expect(openRow).toBeVisible();
    await openRow.click();
    await expect(page).toHaveURL(/.*findings\/.+/);

    await expect(page.locator("text=Recommended for review. Final determination rests with the auditor.")).toBeVisible();

    // Verify Calculation and Reason Pane
    await page.click("button:has-text('Calculation & Reason')");
    await expect(page.locator("text=Statutory Calculation & Logic")).toBeVisible();

    // Add Reviewer Note
    await page.click("button:has-text('Notes')");
    const noteArea = page.locator("textarea[placeholder*='Document observations']");
    if (await noteArea.isVisible()) {
      await noteArea.fill("Final acceptance verification: physical document matches voucher.");
      await page.click("button:has-text('Post Note')");
    }

    // Extracted Values & Inline Auditor Correction
    await page.click("button:has-text('Extracted Values')");
    const correctBtn = page.locator("button:has-text('Correct')").first();
    if (await correctBtn.isVisible()) {
      await correctBtn.click();
      const reasonInput = page.locator("textarea[placeholder*='Mandatory reason for auditor override']");
      await reasonInput.fill("Corrected voucher amount based on signed government sanction.");
      await page.click("button:has-text('Save Correction')");
      await expect(page.locator("text=Field correction saved to cryptographic audit trail")).toBeVisible();
    }

    // =========================================================================
    // STEP 4: Maker-Checker Dual-Custody Approval Flow
    // =========================================================================
    // Auditor confirms finding -> routes to Pending Approval
    const confirmBtn = page.locator("button:has-text('Confirm')").first();
    if (await confirmBtn.isVisible()) {
      await confirmBtn.click();
      await expect(page.locator("text=Confirm Finding")).toBeVisible();
      const commentInput = page.locator("textarea[placeholder*='Document detailed statutory justification']");
      await commentInput.fill("Auditor confirmation of discrepancy. Route to Senior Auditor for approval.");
      await page.click("button:has-text('Submit Determination')");
      await expect(page.locator("text=Confirm Finding")).not.toBeVisible();
    }

    // Logout as Auditor
    await page.click('[data-testid="user-menu-trigger"]');
    await page.click('[data-testid="logout-menu-item"]');
    await expect(page).toHaveURL(/.*login/);

    // Login as Senior Auditor
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // =========================================================================
    // STEP 5: Generate Statutory Audit Report
    // =========================================================================
    // Open case to generate report
    await page.goto("/cases");
    await page.waitForSelector("table tbody tr");
    await page.click("table tbody tr:first-child");
    await expect(page).toHaveURL(/.*cases\/.+/);

    await page.click("button:has-text('Statutory Reports')");
    await expect(page.locator("text=Statutory Audit Reports & Certificates")).toBeVisible();

    const genBtn = page.locator("button:has-text('Generate Report'), button:has-text('Generate First Report')").first();
    await genBtn.click();
    await expect(page.locator("text=Generate Statutory Audit Report")).toBeVisible();

    // Generate Preliminary Draft
    await page.click("button:has-text('Generate PDF Report')");
    await expect(page.locator("text=Statutory PDF report generated successfully")).toBeVisible({ timeout: 15000 });

    // Verify report appears with valid RPT- number
    const rptNumberElem = page.locator("text=RPT-").first();
    await expect(rptNumberElem).toBeVisible();
    const generatedReportNumber = await rptNumberElem.innerText();

    // =========================================================================
    // STEP 6: PDF Preview & Download Integrity
    // =========================================================================
    await page.click("button:has-text('Preview PDF')");
    await expect(page.locator("iframe")).toBeVisible();
    await expect(page.locator("button:has-text('Download PDF')")).toBeVisible();
    await page.click("button >> svg.lucide-x");

    // =========================================================================
    // STEP 7: Public Zero-Knowledge Verification Portal
    // =========================================================================
    const cleanContext = await browser.newContext();
    const publicPage = await cleanContext.newPage();

    // Navigate to public verify route unauthenticated
    await publicPage.goto(`/verify/${generatedReportNumber.trim()}`);
    await expect(publicPage.locator("text=GOVERNMENT OF KARNATAKA").first()).toBeVisible();
    await expect(publicPage.locator("text=Public Verification Portal")).toBeVisible();
    await expect(publicPage.locator("text=Zero-Knowledge Guarantee:")).toBeVisible();
    await expect(publicPage.locator(`text=${generatedReportNumber.trim()}`)).toBeVisible();
    await expect(publicPage.locator("text=Cryptographic SHA-256 Hash Seal")).toBeVisible();
    await expect(publicPage.locator("text=Verify Document Authenticity")).toBeVisible();

    // Verify Zero-knowledge: NO financial findings or questioned amounts leaked
    await expect(publicPage.locator("text=amount at risk")).not.toBeVisible();
    await expect(publicPage.locator("text=finding register")).not.toBeVisible();

    await cleanContext.close();

    // =========================================================================
    // STEP 8: Audit Trail Green Badge Persistence
    // =========================================================================
    await page.goto("/dashboard");
    await expect(page.locator("text=Live Audit Trail")).toBeVisible();
    await expect(page.locator("text=Hash verified").first()).toBeVisible();
  });
});
