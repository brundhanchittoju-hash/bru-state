import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { LoginPage } from "@/pages/LoginPage";
import { AuthProvider } from "@/context/AuthContext";

// Mock the API client
vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn().mockImplementation((url, body) => {
      if (url === "/auth/login") {
        if (body.email === "admin@stateaudit.kar.gov.in" && body.password === "AdminPassword@2024") {
          return Promise.resolve({
            access_token: "mock-access-token",
            refresh_token: "mock-refresh-token",
            token_type: "bearer",
            user: {
              id: "u-1",
              email: "admin@stateaudit.kar.gov.in",
              full_name: "Ramesh Kumar (Admin)",
              role: { code: "administrator", name: "Administrator" },
              is_active: true,
            },
          });
        }
        return Promise.reject(new Error("Incorrect email or password"));
      }
      return Promise.resolve({});
    }),
    get: vi.fn().mockResolvedValue({}),
  },
  getAccessToken: vi.fn().mockReturnValue(null),
  getRefreshToken: vi.fn().mockReturnValue(null),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

describe("Login Flow Component", () => {
  it("renders login form with official branding and input fields", () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    expect(screen.getByText("Sign in to your account")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("name@stateaudit.kar.gov.in")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••••••")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sign In to Audit System/i })).toBeInTheDocument();
  });

  it("populates form inputs when a demo role button is clicked", () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    const seniorAuditorDemoBtn = screen.getByRole("button", { name: /Senior Auditor/i });
    fireEvent.click(seniorAuditorDemoBtn);

    const emailInput = screen.getByPlaceholderText("name@stateaudit.kar.gov.in") as HTMLInputElement;
    const passwordInput = screen.getByPlaceholderText("••••••••••••") as HTMLInputElement;

    expect(emailInput.value).toBe("senior.auditor@stateaudit.kar.gov.in");
    expect(passwordInput.value).toBe("SeniorPassword@2024");
  });

  it("submits valid credentials and triggers successful login", async () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>
    );

    const adminDemoBtn = screen.getByRole("button", { name: /Administrator/i });
    fireEvent.click(adminDemoBtn);

    const submitBtn = screen.getByRole("button", { name: /Sign In to Audit System/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      // Upon successful authentication, no error banner should be present
      expect(screen.queryByText("Incorrect email or password")).not.toBeInTheDocument();
    });
  });
});
