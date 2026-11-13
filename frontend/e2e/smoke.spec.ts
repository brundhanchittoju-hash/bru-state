import { test, expect } from "@playwright/test";
import crypto from "crypto";

const ROLES = [
  { role: "administrator", email: "admin@stateaudit.kar.gov.in", pass: "AdminPassword@2024", canSeeUsers: true },
  { role: "audit_officer", email: "officer@stateaudit.kar.gov.in", pass: "OfficerPassword@2024", canSeeUsers: false },
  { role: "senior_auditor", email: "senior.auditor@stateaudit.kar.gov.in", pass: "SeniorPassword@2024", canSeeUsers: false },
  { role: "auditor", email: "auditor@stateaudit.kar.gov.in", pass: "AuditorPassword@2024", canSeeUsers: false },
];

test.describe("STATE AUDIT AI — End-to-End Smoke Tests", () => {
  test("login as each role and confirm sidebar differences", async ({ page }) => {
    for (const r of ROLES) {
      await page.goto("/login");

      // Fill login form
      await page.fill('input[type="email"]', r.email);
      await page.fill('input[type="password"]', r.pass);
      await page.click('button[type="submit"]');

      // Wait for dashboard navigation
      await expect(page).toHaveURL(/.*dashboard/);
      await expect(page.locator("main h1")).toContainText("Audit Executive Dashboard");

      // Verify sidebar role-based visibility
      const usersLink = page.locator('aside nav a[href="/users"]');
      if (r.canSeeUsers) {
        await expect(usersLink).toBeVisible();
      } else {
        await expect(usersLink).toHaveCount(0);
      }

      // Logout
      await page.click('[data-testid="user-menu-trigger"]');
      await page.click('[data-testid="logout-menu-item"]');
      await expect(page).toHaveURL(/.*login/);
    }
  });

  test("toggle dark mode and persist theme across page reload", async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AdminPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    const htmlElement = page.locator("html");

    // Click theme toggle button
    const themeBtn = page.locator('header button[aria-label="Toggle theme"]');
    await themeBtn.click();

    // Check if class includes 'dark'
    await expect(htmlElement).toHaveClass(/dark/);

    // Reload page
    await page.reload();
    await expect(htmlElement).toHaveClass(/dark/);

    // Toggle back to light
    await themeBtn.click();
    await expect(htmlElement).not.toHaveClass(/dark/);
  });

  test("session persistence across browser reload", async ({ page }) => {
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AdminPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    // Reload page
    await page.reload();
    await expect(page).toHaveURL(/.*dashboard/);
    await expect(page.locator("header")).toContainText("Ramesh Kumar (Admin)");
  });

  test("upload file through API and download back with matching SHA-256 checksum", async ({ request }) => {
    // 1. Authenticate via API
    const authRes = await request.post("/api/auth/login", {
      data: {
        email: "auditor@stateaudit.kar.gov.in",
        password: "AuditorPassword@2024",
      },
    });
    expect(authRes.ok()).toBeTruthy();
    const { access_token } = await authRes.json();

    // 2. Query case ID
    const casesRes = await request.get("/api/cases", {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(casesRes.ok()).toBeTruthy();
    const cases = await casesRes.json();
    expect(cases.length).toBeGreaterThan(0);
    const caseId = cases[0].id;
    expect(caseId).toBeTruthy();

    // 3. Prepare test PNG content with unique marker
    const uniqueBuffer = Buffer.from(
      "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06" +
      "\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01" +
      `\r\n-\xb4_${Date.now()}_audit_test\x00\x00\x00\x00IEND\xaeB\`\x82`,
      "latin1"
    );
    const expectedHash = crypto.createHash("sha256").update(uniqueBuffer).digest("hex");

    // 4. Upload file
    const uploadRes = await request.post("/api/documents/upload", {
      headers: { Authorization: `Bearer ${access_token}` },
      multipart: {
        case_id: caseId,
        title: "E2E Automated Voucher",
        file: {
          name: "e2e_voucher.png",
          mimeType: "image/png",
          buffer: uniqueBuffer,
        },
      },
    });
    expect(uploadRes.status()).toBe(201);
    const uploadedDoc = await uploadRes.json();
    expect(uploadedDoc.sha256_hash).toBe(expectedHash);

    // 5. Download file back
    const downloadRes = await request.get(`/api/documents/${uploadedDoc.id}/download`, {
      headers: { Authorization: `Bearer ${access_token}` },
    });
    expect(downloadRes.ok()).toBeTruthy();
    const downloadedBuffer = await downloadRes.body();
    const downloadedHash = crypto.createHash("sha256").update(downloadedBuffer).digest("hex");

    // Assert identical cryptographic checksum
    expect(downloadedHash).toBe(expectedHash);
  });

  test("navigate all sidebar routes in light and dark mode without console errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    // Login as admin
    await page.goto("/login");
    await page.fill('input[type="email"]', "admin@stateaudit.kar.gov.in");
    await page.fill('input[type="password"]', "AdminPassword@2024");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/.*dashboard/);

    const routes = [
      { path: "/dashboard", heading: "Audit Executive Dashboard" },
      { path: "/cases", heading: "Audit Case Management" },
      { path: "/documents", heading: "Document Ingestion & Repository" },
      { path: "/verification", heading: "Financial Verification & Rule Engine" },
      { path: "/findings", heading: "Audit Findings Register" },
      { path: "/reports", heading: "Statutory Audit Reports" },
      { path: "/analytics", heading: "Audit Analytics & Intelligence" },
      { path: "/users", heading: "User Administration" },
      { path: "/settings", heading: "System Settings & Governance" },
    ];

    for (const r of routes) {
      await page.click(`aside nav a[href="${r.path}"]`);
      await expect(page.locator("main h1")).toContainText(r.heading);
      await page.waitForTimeout(100);
    }

    // Toggle theme to dark while navigating and verify
    await page.click('header button[aria-label="Toggle theme"]');
    await expect(page.locator("html")).toHaveClass(/dark/);
    await page.click('aside nav a[href="/settings"]');
    await expect(page.locator("main h1")).toContainText("System Settings & Governance");

    // Filter out React Router v7 future warnings if any
    const realErrors = consoleErrors.filter(
      (err) => !err.includes("React Router Future Flag Warning")
    );
    expect(realErrors).toHaveLength(0);
  });
});
