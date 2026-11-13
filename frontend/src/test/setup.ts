import "@testing-library/jest-dom";

// Ensure demo login buttons are enabled in test environments
if (typeof (import.meta as any).env.VITE_ENABLE_DEMO_LOGIN === "undefined") {
  (import.meta as any).env.VITE_ENABLE_DEMO_LOGIN = "true";
}
