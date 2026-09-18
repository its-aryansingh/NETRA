/**
 * Standard formatting utilities for NETRA frontend.
 * All financial formatting conforms to Intl.NumberFormat('en-IN').
 */

const inrFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const inrWholeFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const numberFormatter = new Intl.NumberFormat("en-IN", {
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

export function formatINR(val: number, options?: { whole?: boolean }): string {
  if (val === undefined || val === null || isNaN(val)) return "₹0.00";
  if (options?.whole) {
    return inrWholeFormatter.format(val);
  }
  return inrFormatter.format(val);
}

export function formatUSD(val: number): string {
  if (val === undefined || val === null || isNaN(val)) return "$0.00";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: val < 0.1 ? 4 : 2,
    maximumFractionDigits: 4,
  }).format(val);
}

export function formatNumber(val: number): string {
  if (val === undefined || val === null || isNaN(val)) return "0";
  return numberFormatter.format(val);
}

export function formatAge(seconds: number): string {
  if (!seconds || seconds <= 0) return "<1m";
  const m = Math.floor(seconds / 60);
  const h = Math.floor(m / 60);
  const d = Math.floor(h / 24);

  if (d > 0) return `${d}d ${h % 24}h`;
  if (h > 0) return `${h}h ${m % 60}m`;
  return `${m}m`;
}

export function formatTime(epoch: number): string {
  if (!epoch) return "";
  const d = new Date(epoch * 1000);
  return d.toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

export function formatDate(epoch: number): string {
  if (!epoch) return "";
  const d = new Date(epoch * 1000);
  return d.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
