import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import { ErrorBoundary } from "@/components/shared/ErrorBoundary";
import { AppLayout } from "@/components/layout/AppLayout";

import { LoginPage } from "@/pages/LoginPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { AuditCasesPage } from "@/pages/AuditCasesPage";
import { AuditCaseDetailPage } from "@/pages/AuditCaseDetailPage";
import { DocumentsPage } from "@/pages/DocumentsPage";
import { FinancialVerificationPage } from "@/pages/FinancialVerificationPage";
import { FindingsPage } from "@/pages/FindingsPage";
import { FindingEvidencePage } from "@/pages/FindingEvidencePage";
import { ReportsPage } from "@/pages/ReportsPage";
import { ReportVerifyPage } from "@/pages/ReportVerifyPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { VendorsPage } from "@/pages/VendorsPage";
import { VendorDetailPage } from "@/pages/VendorDetailPage";
import { SearchPage } from "@/pages/SearchPage";
import { UsersPage } from "@/pages/UsersPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { ForbiddenPage } from "@/pages/ForbiddenPage";
import { NotFoundPage } from "@/pages/NotFoundPage";

const ProtectedRoute: React.FC<{
  children: React.ReactNode;
  allowedRoles?: string[];
}> = ({ children, allowedRoles }) => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-4 border-primary border-r-transparent" />
          <p className="text-xs font-medium text-muted-foreground font-mono">
            Loading Karnataka State Audit System...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user?.role && !allowedRoles.includes(user.role.code)) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public Routes */}
              <Route path="/login" element={<LoginPage />} />
              <Route path="/verify/:reportId" element={<ReportVerifyPage />} />

              {/* Protected App Routes inside Shell */}
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="dashboard" element={<DashboardPage />} />
                <Route path="cases" element={<AuditCasesPage />} />
                <Route path="cases/:id" element={<AuditCaseDetailPage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="verification" element={<FinancialVerificationPage />} />
                <Route path="findings" element={<FindingsPage />} />
                <Route path="findings/:id" element={<FindingEvidencePage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route path="analytics" element={<AnalyticsPage />} />
                <Route path="vendors" element={<VendorsPage />} />
                <Route path="vendors/:id" element={<VendorDetailPage />} />
                <Route path="search" element={<SearchPage />} />
                <Route
                  path="users"
                  element={
                    <ProtectedRoute allowedRoles={["administrator"]}>
                      <UsersPage />
                    </ProtectedRoute>
                  }
                />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="403" element={<ForbiddenPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
            <Toaster position="top-right" richColors closeButton />
          </BrowserRouter>
        </AuthProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
};

export default App;
