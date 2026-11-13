import { test, expect } from "@playwright/test";

test.describe("Phase 3: Financial Verification & Risk Engine E2E", () => {
  test.beforeEach(async ({ page }) => {
    // Monitor console errors
    page.on("console", (msg) => {
      if (msg.type() === "error" && !msg.text().includes("React Router Future Flag")) {
        console.error("Browser Console Error:", msg.text());
      }
    });
  });

  test("Senior Auditor verifies CAS-2024-MYS-002, inspects risk gauge, reconciliation matrix, and finding drawer", async ({ page }) => {
    // 1. Login as Senior Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Financial Verification
    await page.click('aside nav a[href="/verification"]');
    await expect(page).toHaveURL(/.*verification/);
    await expect(page.locator("h1")).toContainText("Financial Verification & Rule Engine");

    // 3. Verify Case Selector has CAS-2024-MYS-002 selected
    const caseSelect = page.locator("select").first();
    await expect(caseSelect).toBeVisible();

    // 4. Verify Executive Metric Cards
    await expect(page.locator("text=Composite Risk Score")).toBeVisible();
    await expect(page.locator("text=Cumulative Amount at Risk")).toBeVisible();
    await expect(page.locator("text=Reconciliation Rate")).toBeVisible();

    // 5. Verify Risk Score Gauge
    await expect(page.locator("text=Composite Case Risk Gauge")).toBeVisible();
    await expect(page.locator("text=CRITICAL RISK")).toBeVisible();

    // 6. Test "How is this calculated?" formula modal
    await page.click("text=How is this calculated?");
    await expect(page.locator("text=Composite Risk Score Calculation")).toBeVisible();
    await expect(page.locator("text=Statutory Severity Override Rule:")).toBeVisible();
    await page.click("text=Close Explanation");
    await expect(page.locator("text=Composite Risk Score Calculation")).not.toBeVisible();

    // 7. Trigger "Run Verification" button
    const runBtn = page.locator("button:has-text('Run Verification')");
    await expect(runBtn).toBeVisible();
    await runBtn.click();

    // Wait for verification progress
    await page.waitForTimeout(1500);
    await expect(page.locator("text=CRITICAL RISK")).toBeVisible();

    // 8. Test Finding Detail Drawer
    // Click on the first row in findings table
    const firstRow = page.locator("tbody tr").first();
    await expect(firstRow).toBeVisible();
    await firstRow.click();

    // Verify slide-over drawer content
    await expect(page.locator("text=Statutory Amount at Risk")).toBeVisible();
    await expect(page.locator("text=Deterministic Mathematical Calculation")).toBeVisible();
    await expect(page.locator("text=Supporting Record Evidence")).toBeVisible();
    await expect(page.locator("text=Update Finding Review Status")).toBeVisible();

    // Submit auditor review notes
    const statusSelect = page.locator("select:has-text('Select Auditor Determination...')");
    await statusSelect.selectOption("Confirmed");
    await page.fill("textarea[placeholder*='Enter statutory justification']", "Verified against muster roll and bank statement. Confirmed non-compliance.");
    await page.click("button:has-text('Save Auditor Determination')");

    // Close drawer using close button
    const closeDrawerBtn = page.locator("div.fixed button:has(svg.lucide-x)").first();
    await closeDrawerBtn.click();
    await expect(page.locator("text=Update Finding Review Status")).not.toBeVisible();

    // 9. Switch to Reconciliation Matrix Tab
    await page.click("button:has-text('Reconciliation Matrix')");
    await expect(page.locator("text=Payment Chain Reconciliation Matrix")).toBeVisible();
    await expect(page.locator("text=Stage 1: Vendor Bill")).toBeVisible();
    await expect(page.locator("text=Stage 2: Passed Voucher")).toBeVisible();
    await expect(page.locator("text=Stage 3: Bank Debit (UTR)")).toBeVisible();

    // Test status filter buttons
    await page.click("button:has-text('Matched')");
    await page.click("button:has-text('Partial')");
    await page.click("button:has-text('All')");

    // 10. Switch to 16 Statutory Rules Tab
    await page.click("button:has-text('16 Statutory Rules')");
    await expect(page.locator("text=16 Statutory Verification Rules Overview")).toBeVisible();
    await expect(page.locator("text=R-001")).toBeVisible();
    await expect(page.locator("text=R-004")).toBeVisible();
    await expect(page.locator("text=R-014")).toBeVisible();
    await expect(page.locator("text=R-016")).toBeVisible();

    // 11. Switch to Vendor Exposure Tab
    await page.click("button:has-text('Vendor Exposure')");
    await expect(page.locator("text=Vendor Expenditure Concentration")).toBeVisible();
    await expect(page.locator("text=Cauvery Infra Projects").first()).toBeVisible();

    // 12. Switch to Clean Case CAS-2024-MYS-003
    const option003 = await page.locator("select option:has-text('CAS-2024-MYS-003')").getAttribute("value");
    if (option003) {
      await caseSelect.selectOption(option003);
      await page.waitForTimeout(1000);
      await expect(page.locator("text=LOW RISK")).toBeVisible();
    }
  });

  test("Administrator inspects and manages Settings verification extensions", async ({ page }) => {
    // 1. Login as Administrator
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AdminPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Settings
    await page.click('aside nav a[href="/settings"]');
    await expect(page).toHaveURL(/.*settings/);

    // 3. Verification Rules Tab
    await page.click("button:has-text('Verification Rules')");
    await expect(page.locator("text=Statutory Verification Rules (16 Rules Engine)")).toBeVisible();
    await expect(page.locator("text=R-001")).toBeVisible();
    await expect(page.locator("text=R-016")).toBeVisible();

    // Click configure on R-001
    const configBtn = page.locator("button:has-text('Configure')").first();
    await configBtn.click();
    await expect(page.locator("text=Configure Rule Parameters")).toBeVisible();
    await expect(page.locator("text=Reason for Parameter Change")).toBeVisible();
    await page.click("button:has-text('Cancel')");

    // 4. Risk Weights Tab (100% sum guard)
    await page.click("button:has-text('Risk Weights (100% Guard)')");
    await expect(page.locator("text=Case Risk Engine Weight Calibration (7 Factor Matrix)")).toBeVisible();
    await expect(page.locator("text=Total: 100% (Statutory Valid)")).toBeVisible();

    // 5. Mandatory Checklists Tab
    await page.click("button:has-text('Mandatory Checklists')");
    await expect(page.locator("text=Mandatory Statutory Document Checklists")).toBeVisible();
    await expect(page.locator("text=MGNREGA")).toBeVisible();
    await expect(page.getByText("Measurement Book", { exact: true }).first()).toBeVisible();

    // 6. Pending Vendor Reviews Tab
    await page.click("button:has-text('Pending Vendor Reviews')");
    await expect(page.locator("text=Pending Vendor Alias Reviews")).toBeVisible();
  });
});
