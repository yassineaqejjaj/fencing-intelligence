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
    <div className="rounded-xl border border-dashed border-line px-6 py-10 text-center text-sm text-muted">
      {children}
    </div>
  );
}

export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section
      className="rounded-xl border border-line bg-surface p-5"
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
  "rounded-lg border border-line bg-surface px-3.5 py-2.5 text-sm text-text placeholder:text-muted/70 transition-colors hover:border-muted focus:border-mask focus:outline-none";
export const buttonClass =
  "fi-btn inline-flex items-center justify-center gap-2 bg-mask px-5 py-2.5 text-sm font-semibold text-tenue disabled:opacity-50 motion-reduce:transform-none";
export const secondaryButton =
  "fi-btn inline-flex items-center justify-center gap-2 border border-line bg-surface px-4 py-2 text-sm font-medium text-text hover:bg-tenue disabled:opacity-50 motion-reduce:transform-none";
