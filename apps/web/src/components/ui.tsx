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
          <p className="mb-2 font-mono text-[11px] font-medium tracking-[0.14em] text-muted uppercase">
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
      className={`rounded-xl border border-line bg-surface p-5 ${className}`}
    >
      {children}
    </section>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "success" | "warning" | "danger" | "info"; children: React.ReactNode }) {
  const tones: Record<string, string> = {
    neutral: "border-line bg-tenue text-muted",
    success: "border-line bg-tenue text-text",
    warning: "border-warning/40 bg-warning/15 text-text",
    danger: "border-lamp-red/30 bg-lamp-red/10 text-text",
    info: "border-line bg-tenue text-text",
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded border px-1.5 py-0.5 font-mono text-[10px] font-medium tracking-wide uppercase ${tones[tone]}`}>
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
      className={`flex ${box} shrink-0 items-center justify-center rounded-lg bg-mask font-mono text-[11px] font-medium text-tenue`}
    >
      {initials}
    </span>
  );
}

export function RowLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="group flex items-center justify-between gap-4 rounded-lg border border-transparent px-3 py-3 transition-colors duration-200 ease-out hover:border-line hover:bg-tenue active:scale-[0.98]"
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
      <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-tenue text-mask">
        <Icon size={17} />
      </span>
      <span className="mt-4 block font-mono text-[11px] tracking-[0.12em] text-muted uppercase">{label}</span>
      <span className="mt-1 block font-mono text-[2rem] leading-none font-medium tracking-tight">{value}</span>
    </>
  );
  const cls =
    "fi-rise block rounded-xl border border-line bg-surface p-5 transition-colors duration-200 ease-out hover:bg-tenue active:scale-[0.98]";
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
    <span className="inline-flex items-center gap-2 rounded-lg border border-line bg-surface px-3 py-1 font-mono text-lg font-medium">
      <span className="text-lamp-red"><span className="sr-only">Left </span>{left}</span>
      <span className="text-xs text-muted">:</span>
      <span className="text-lamp-green"><span className="sr-only">Right </span>{right}</span>
    </span>
  );
}
