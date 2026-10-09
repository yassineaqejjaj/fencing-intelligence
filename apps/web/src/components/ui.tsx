"use client";

import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ChevronRight } from "lucide-react";

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="fi-rise flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow ? (
          <p className="mb-2 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3 py-1 text-[11px] font-semibold tracking-[0.16em] text-primary uppercase">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-3xl font-semibold tracking-tight text-balance md:text-[2.75rem] md:leading-[1.05]">{title}</h1>
        {description ? <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-muted">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section
      className={`rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-5 shadow-[0_12px_32px_-16px_rgb(0_0_0/0.6)] ${className}`}
    >
      {children}
    </section>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "success" | "warning" | "danger" | "info"; children: React.ReactNode }) {
  const tones: Record<string, string> = {
    neutral: "border-white/10 bg-white/[0.06] text-muted",
    success: "border-success/30 bg-success/10 text-success",
    warning: "border-warning/30 bg-warning/10 text-warning",
    danger: "border-danger/30 bg-danger/10 text-danger",
    info: "border-primary/30 bg-primary/10 text-primary",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${tones[tone]}`}>
      {children}
    </span>
  );
}

export function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" }) {
  const initials = name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
  const box = size === "sm" ? "h-8 w-8 text-xs" : "h-11 w-11 text-sm";
  return (
    <span
      aria-hidden
      className={`flex ${box} shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-secondary/80 to-primary/70 font-semibold text-white shadow-lg`}
    >
      {initials}
    </span>
  );
}

export function RowLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group flex items-center justify-between gap-4 rounded-2xl border border-transparent px-4 py-3.5 transition-all duration-150 ease-out hover:border-white/10 hover:bg-white/[0.04] active:scale-[0.99]"
    >
      <span className="flex min-w-0 flex-1 items-center gap-3">{children}</span>
      <ChevronRight size={16} className="shrink-0 text-muted transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-text" />
    </Link>
  );
}

export function StatCard({
  icon: Icon,
  label,
  value,
  href,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  href?: string;
}) {
  const body = (
    <>
      <span className="flex h-9 w-9 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.06] text-primary">
        <Icon size={17} />
      </span>
      <span className="mt-4 block text-xs font-medium tracking-[0.12em] text-muted uppercase">{label}</span>
      <span className="mt-1 block text-[2rem] leading-none font-semibold tracking-tight tabular-nums">{value}</span>
    </>
  );
  const cls =
    "fi-rise block rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-5 shadow-[0_12px_32px_-16px_rgb(0_0_0/0.6)] transition-all duration-150 ease-out hover:border-white/20 hover:bg-white/[0.05] active:scale-[0.98]";
  return href ? (
    <Link href={href} className={cls}>
      {body}
    </Link>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function ScorePill({ left, right }: { left: number; right: number }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-2xl border border-white/10 bg-black/40 px-3.5 py-1.5 text-lg font-semibold tracking-tight tabular-nums">
      {left}
      <span className="text-xs font-medium text-muted">–</span>
      {right}
    </span>
  );
}
