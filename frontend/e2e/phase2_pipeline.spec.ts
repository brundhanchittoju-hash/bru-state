import { test, expect } from "@playwright/test";

test.describe("PHASE 2: Audit Case & Document Pipeline E2E Flow", () => {
  test("complete end-to-end audit document workflow", async ({ page }) => {
    // 1. Log in as Senior Auditor
    await page.goto("/login");
    await page.fill('input[type="email"]', "senior.auditor@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "SeniorPassword@2024");
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/.*dashboard/);

    // 2. Navigate to Audit Cases
    await page.click('aside nav a[href="/cases"]');
    await expect(page).toHaveURL(/.*cases/);
    await expect(page.locator("h1")).toContainText("Audit Case Management");

    // 3. Initiate New Audit Case
    await page.click('button:has-text("New Audit Case")');
    await expect(page.locator("text=Initiate Statutory Audit Case")).toBeVisible();

    const testCaseTitle = `E2E Mandya Irrigation & MGNREGA Audit ${Date.now()}`;
    await page.fill('input[placeholder*="Mandya ZP Water"]', testCaseTitle);
    await page.fill('input[placeholder*="Hunsur"]', "Pandavapura");
    await page.fill('input[placeholder*="Bilikere"]', "Melukote");

    await page.click('button:has-text("Create Audit Case")');

    // 4. Verify redirected to Case Detail page
    await expect(page).toHaveURL(/\/cases\/[a-f0-9-]+/);
    await expect(page.locator("h2").first()).toContainText(testCaseTitle);
    await expect(page.locator("text=SAI-2024-").first()).toBeVisible();

    // 5. Upload Evidence Document
    await page.click("button:has-text('Evidence Docs')");
    await page.click('button:has-text("Upload New Evidence")');
    await expect(page.locator("text=Upload Audit Evidence Document")).toBeVisible();

    // Create a mock PDF buffer for testing
    const samplePdfContent = Buffer.from(
      "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 75 >>\nstream\nBT /F1 12 Tf 72 712 Td (TAX INVOICE INV-2024-88 GSTIN: 29AAAAA0000A1ZY Total: Rs. 50,000) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n0000000201 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n327\n%%EOF"
    );

    // Set file input in modal
    const fileChooserPromise = page.waitForEvent("filechooser");
    await page.click('text="browse"');
    const fileChooser = await fileChooserPromise;
    await fileChooser.setFiles({
      name: "tax_invoice_e2e.pdf",
      mimeType: "application/pdf",
      buffer: samplePdfContent,
    });

    await page.click('button:has-text("Upload & Extract")');

    // 6. Wait for upload to complete and card to appear
    await expect(page.locator("text=tax_invoice_e2e.pdf").first()).toBeVisible({ timeout: 15000 });

    // 7. Click to open Side-by-Side Viewer
    await page.locator('[data-testid="open-viewer-btn"]').first().click();
    await expect(page.locator("text=Extracted Statutory Fields")).toBeVisible({ timeout: 10000 });

    // 8. Test Add Missing Field
    await page.click('button:has-text("Add Missing Field")');
    await expect(page.locator("text=Tag Missing Statutory Field")).toBeVisible();
    await page.fill('input[placeholder*="pan, sanction_number"]', "pan");
    await page.fill('input[placeholder*="AAACB1234F"]', "AAACB1234F");
    await page.click('button:has-text("Add Field")');

    // Confirm field card appears
    await expect(page.locator("text=AAACB1234F")).toBeVisible();

    // 9. Test Manual Field Override
    const editBtn = page.locator('button:has-text("Edit")').first();
    await editBtn.click();
    await expect(page.locator("text=Manual Field Override (Human-in-the-Loop)")).toBeVisible();

    await page.fill('[data-testid="override-value-input"]', "AAACB1234G");
    await page.fill('[data-testid="override-reason-input"]', "Senior auditor verified PAN against IT portal records.");
    await page.click('[data-testid="save-override-btn"]');

    // Verify Overridden badge
    await expect(page.locator("text=Overridden").first()).toBeVisible();
    await expect(page.locator("text=AAACB1234G")).toBeVisible();

    // 10. Revert Override
    const revertBtn = page.locator('button[title="Revert to original extracted value"]').first();
    await revertBtn.click();
    await expect(page.locator("text=AAACB1234F")).toBeVisible();

    // 11. Test Document Reclassification
    await page.click('[data-testid="reclassify-trigger-btn"]');
    await expect(page.locator("text=Reclassify Document")).toBeVisible();
    await page.locator('div[role="dialog"] select').selectOption("Voucher");
    await page.fill('input[placeholder*="Corrected document header"]', "Verified voucher voucher head");
    await page.click('[data-testid="confirm-reclassification-btn"]');

    await expect(page.locator("text=Voucher").first()).toBeVisible();

    // 12. Check Top Bar Cryptographic Audit Trail Status
    const auditVerifiedBadge = page.locator('[data-testid="audit-trail-verified-btn"]');
    await expect(auditVerifiedBadge).toBeVisible();
  });
});
