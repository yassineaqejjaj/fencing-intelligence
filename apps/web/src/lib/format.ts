import type { Rate } from "./api";

export function formatRate(rate: Rate | undefined): string {
  if (!rate || rate.value === null || rate.value === undefined) return "—";
  return `${(rate.value * 100).toFixed(1)}%`;
}

export function formatCount(value: number | undefined): string {
  return value === undefined ? "—" : String(value);
}
