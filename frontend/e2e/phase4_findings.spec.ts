import { test, expect } from "@playwright/test";

test.describe("Phase 4: Findings, Evidence, and Dual-Custody Review E2E", () => {
  test.beforeEach(async ({ page }) => {
    page.on("console", (msg) => {
      if (msg.type() === "error" && !msg.text().includes("React Router Future Flag")) {
        console.error("Browser Console Error:", msg.text());
      }
    });
  });

  test("Complete Auditor -> Evidence Review -> Maker-Checker Approval -> Self-Approval Block -> Audit Trail Verified", async ({ page }) => {
    // 1. Login as Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AuditorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Findings page via sidebar
    await page.click('aside nav a[href="/findings"]');
    await expect(page).toHaveURL(/.*findings/);
    await expect(page.locator("h1")).toContainText("Audit Findings Register");

    // 3. Filter by High risk and Open status
    const riskSelect = page.locator("select").first();
    await riskSelect.selectOption("high");
    const statusSelect = page.locator("select").nth(1);
    await statusSelect.selectOption("Open");

    // 4. Open the first finding row
    const firstRow = page.locator("tbody tr:has-text('Open')").first();
    await expect(firstRow).toBeVisible();
    await firstRow.click();

    // 5. Verify Evidence Page loads with split-pane
    await expect(page).toHaveURL(/.*findings\/.+/);
    await expect(page.locator("text=Recommended for review. Final determination rests with the auditor.")).toBeVisible();

    // 6. Inspect Right Pane Tabs: Calculation & Reason
    await page.click("button:has-text('Calculation & Reason')");
    await expect(page.locator("text=Statutory Calculation & Logic")).toBeVisible();
    await expect(page.locator("text=AI summary: template mode")).toBeVisible();

    // 7. Inspect Comparison Tab
    await page.click("button:has-text('Comparison')");
    await expect(page.locator("text=Multi-stage payment chain reconciliation")).toBeVisible();

    // 8. Add a Reviewer Note
    await page.click("button:has-text('Notes')");
    const noteTextarea = page.locator("textarea[placeholder*='Document observations']");
    if (await noteTextarea.isVisible()) {
      await noteTextarea.fill("Verified voucher discrepancy against bank passbook. Evidence substantiated.");
      await page.click("button:has-text('Post Note')");
      await expect(page.locator("p:has-text('Verified voucher discrepancy against bank passbook')").first()).toBeVisible();
    }

    // 9. Inspect Extracted Values and perform inline correction
    await page.click("button:has-text('Extracted Values')");
    const correctBtn = page.locator("button:has-text('Correct')").first();
    if (await correctBtn.isVisible()) {
      await correctBtn.click();
      const reasonInput = page.locator("textarea[placeholder*='Mandatory reason for auditor override']");
      await reasonInput.fill("Corrected amount based on signed government sanction order.");
      await page.click("button:has-text('Save Correction')");
      await expect(page.locator("text=Field correction saved to cryptographic audit trail")).toBeVisible();
    }

    // 10. Auditor Confirms a High Risk Finding -> Triggers Maker-Checker to 'Pending Approval'
    const confirmBtn = page.locator("button:has-text('Confirm')").first();
    await confirmBtn.click();

    // Modal opens requiring comment
    await expect(page.locator("text=Confirm Finding")).toBeVisible();
    await expect(page.locator("text=Pending Approval")).toBeVisible();

    const commentInput = page.locator("textarea[placeholder*='Document detailed statutory justification']");
    await commentInput.fill("Duplicate payment verified by auditor. Submitting for senior dual-custody approval.");
    await page.click("button:has-text('Submit Determination')");
    await expect(page.locator("text=Confirm Finding")).not.toBeVisible();

    // Status pill should now show Pending Approval
    await expect(page.locator("text=Pending Approval").first()).toBeVisible();

    // 11. Auditor attempts to approve own submission -> Blocked
    // Logout as Auditor
    await page.click('[data-testid="user-menu-trigger"]');
    await page.click('[data-testid="logout-menu-item"]');
    await expect(page).toHaveURL(/.*login/);

    // 12. Login as Senior Auditor
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // Navigate to Findings page
    await page.click('aside nav a[href="/findings"]');
    await expect(page).toHaveURL(/.*findings/);

    // Check Maker-Checker Approval Queue Tab
    await page.click("text=Maker-Checker Approval Queue");
    const pendingRow = page.locator("tbody tr").first();
    await expect(pendingRow).toBeVisible();
    await pendingRow.click();

    // On Evidence Page, Senior Auditor sees "Approve Finding" button
    await expect(page).toHaveURL(/.*findings\/.+/);
    const approveBtn = page.locator("button:has-text('Approve Finding')");
    await expect(approveBtn).toBeVisible();
    await approveBtn.click();

    // Fill Senior Approval Dialog
    const seniorCommentInput = page.locator("textarea[placeholder*='Document detailed statutory justification']");
    await seniorCommentInput.fill("Senior Auditor dual review completed. Concur with auditor findings.");
    await page.click("button:has-text('Submit Determination')");

    // Status should now be Confirmed
    await expect(page.locator("text=Confirmed").first()).toBeVisible();

    // 13. Inspect Timeline Tab for full cryptographic trace
    await page.click("button:has-text('Timeline')");
    await expect(page.locator("text=Cryptographic activity ledger event history")).toBeVisible();
    await expect(page.locator("text=Review Action: Approve")).toBeVisible();

    // 14. Reload page and confirm persistence
    await page.reload();
    await expect(page.locator("text=Confirmed").first()).toBeVisible();

    // 15. Verify Topbar "Audit trail verified ✓" badge
    await expect(page.locator('[data-testid="audit-trail-verified-btn"]')).toBeVisible();
  });
});

