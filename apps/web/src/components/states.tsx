"use client";

import { ApiError } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export function Loading() {
  const { t } = useI18n();
  return (
    <div className="grid gap-3" role="status" aria-busy="true" aria-label={t.loading}>
      <div className="fi-skeleton h-9 w-2/3 rounded-xl" />
      <div className="fi-skeleton h-28 rounded-2xl" />
      <div className="fi-skeleton h-16 w-5/6 rounded-2xl" />
      <p className="text-sm text-muted">{t.loading}…</p>
    </div>
  );
}

export function ErrorNote({ error }: { error: unknown }) {
  const { t } = useI18n();
  const message = error instanceof ApiError ? error.message : error instanceof Error ? error.message : t.error;
  return (
    <p role="alert" className="rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-text">
      {message}
    </p>
  );
}

export function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-3xl border border-dashed border-white/15 bg-white/[0.02] px-6 py-10 text-center text-sm text-muted">
      {children}
    </div>
  );
}

export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.05] to-white/[0.015] p-5 shadow-[0_12px_32px_-16px_rgb(0_0_0/0.6)]"
    >
      <h2 className="mb-4 text-xs font-semibold tracking-[0.14em] text-muted uppercase">{title}</h2>
      {children}
    </section>
  );
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-sm">
      <span className="text-xs font-medium tracking-wide text-muted uppercase">{label}</span>
      {children}
    </label>
  );
}

export const inputClass =
  "rounded-xl border border-white/10 bg-white/[0.05] px-3.5 py-2.5 text-sm text-text placeholder:text-muted/60 transition-colors hover:border-white/20 focus:border-primary/60 focus:outline-none";
export const buttonClass =
  "inline-flex items-center justify-center gap-2 rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-5 py-2.5 text-sm font-semibold text-[#04121a] shadow-[0_8px_32px_-8px_rgb(0_212_255/0.5)] transition-all duration-150 ease-out hover:brightness-110 active:scale-[0.97] disabled:opacity-50 disabled:shadow-none motion-reduce:transform-none";
export const secondaryButton =
  "inline-flex items-center justify-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm font-medium text-text transition-all duration-150 ease-out hover:bg-white/[0.1] active:scale-[0.97] disabled:opacity-50 motion-reduce:transform-none";
