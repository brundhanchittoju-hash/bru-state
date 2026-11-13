import { format, formatDistanceToNow, parseISO } from "date-fns";

/**
 * Formats numeric currency with Indian lakh/crore grouping and ₹ symbol.
 * Example: 123456.78 -> "₹ 1,23,456.78"
 */
export function formatINR(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined || isNaN(Number(amount))) {
    return "₹ 0.00";
  }
  const numeric = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(numeric);
}

/**
 * Formats a date into "DD MMM YYYY" format (e.g., 28 Oct 2024).
 */
export function formatDate(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "—";
  try {
    const d = typeof dateInput === "string" ? parseISO(dateInput) : dateInput;
    return format(d, "dd MMM yyyy");
  } catch {
    return String(dateInput);
  }
}

/**
 * Formats relative time (e.g. "2 hours ago").
 */
export function formatRelativeTime(dateInput: string | Date | null | undefined): string {
  if (!dateInput) return "—";
  try {
    const d = typeof dateInput === "string" ? parseISO(dateInput) : dateInput;
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return "recently";
  }
}

/**
 * Formats byte size into human readable string (KB, MB).
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}
