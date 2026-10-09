"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Building2,
  ChartLine,
  Clapperboard,
  Cpu,
  Database,
  Dumbbell,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Settings,
  ShieldCheck,
  Swords,
  Trophy,
  Users,
  Zap,
} from "lucide-react";
import { api, type User } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Loading } from "./states";

const sections = [
  {
    label: "Review",
    links: [
      ["dashboard", "/dashboard", LayoutDashboard],
      ["videos", "/videos", Clapperboard],
      ["bouts", "/bouts", Swords],
      ["athletes", "/athletes", Users],
    ],
  },
  {
    label: "Insight",
    links: [
      ["performance", "/performance", ChartLine],
      ["coach", "/coach", GraduationCap],
    ],
  },
  {
    label: "Club",
    links: [
      ["clubs", "/clubs", Building2],
      ["competitions", "/competitions", Trophy],
      ["training", "/training", Dumbbell],
      ["reports", "/reports", FileText],
    ],
  },
  {
    label: "System",
    links: [
      ["datasets", "/datasets", Database],
      ["models", "/models", Cpu],
      ["settings", "/settings", Settings],
      ["privacy", "/privacy", ShieldCheck],
    ],
  },
] as const;

export function Shell({ children }: { children: React.ReactNode }) {
  const { t, locale, setLocale } = useI18n();
  const pathname = usePathname();
  const router = useRouter();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<{ user: User; role: string }>("/auth/me") });

  useEffect(() => {
    if (me.isError) router.replace("/login");
  }, [me.isError, router]);

  if (me.isLoading) return <div className="p-8"><Loading /></div>;
  if (me.isError || !me.data) return <div className="p-8"><Loading /></div>;

  const initials = me.data.user.display_name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[264px_minmax(0,1fr)]">
      <aside className="border-b border-white/10 bg-surface/70 backdrop-blur-2xl lg:sticky lg:top-0 lg:h-screen lg:border-r lg:border-b-0">
        <div className="flex items-center gap-3 px-5 pt-5 pb-2">
          <Link href="/dashboard" className="flex items-center gap-3" aria-label={t.product}>
            <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-[#04121a] shadow-[0_8px_32px_-8px_rgb(0_212_255/0.5)]">
              <Zap size={18} strokeWidth={2.5} />
            </span>
            <span className="leading-tight">
              <span className="block text-[13px] font-semibold tracking-tight">{t.product}</span>
              <span className="block text-[11px] text-muted">{t.weapons}</span>
            </span>
          </Link>
        </div>
        <nav className="flex gap-5 overflow-x-auto px-4 pt-3 pb-4 lg:flex-col lg:gap-1 lg:overflow-visible" aria-label="Main">
          {sections.map((section) => (
            <div key={section.label} className="min-w-max lg:min-w-0">
              <p className="hidden px-3 pt-3 pb-1.5 text-[10px] font-semibold tracking-[0.18em] text-muted/70 uppercase lg:block">
                {section.label}
              </p>
              <div className="flex gap-1 lg:flex-col">
                {section.links.map(([key, href, Icon]) => {
                  const current = pathname === href || pathname.startsWith(`${href}/`);
                  return (
                    <Link
                      key={href}
                      href={href}
                      aria-current={current ? "page" : undefined}
                      className={`flex items-center gap-2.5 rounded-2xl px-3 py-2 text-sm transition-all duration-150 ease-out active:scale-[0.97] motion-reduce:transform-none ${
                        current
                          ? "border border-white/10 bg-white/[0.08] font-medium text-text shadow-sm"
                          : "border border-transparent text-muted hover:bg-white/[0.04] hover:text-text"
                      }`}
                    >
                      <Icon size={16} className={current ? "text-primary" : ""} />
                      {t[key as keyof typeof t]}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="sticky top-0 z-10 border-b border-white/10 bg-background/70 backdrop-blur-2xl">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 md:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-secondary to-primary text-xs font-semibold text-white">
                {initials}
              </span>
              <p className="truncate text-sm">
                <span className="font-medium">{me.data.user.display_name}</span>
                <span className="text-muted"> · {me.data.role}</span>
              </p>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                className="rounded-full border border-white/10 bg-white/[0.05] px-3 py-1.5 text-xs font-semibold text-muted transition-colors hover:text-text active:scale-[0.97]"
                onClick={() => setLocale(locale === "en" ? "fr" : "en")}
                aria-label="Language"
              >
                {locale === "en" ? "FR" : "EN"}
              </button>
              <button
                type="button"
                className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:bg-white/[0.06] hover:text-text active:scale-[0.97]"
                onClick={async () => {
                  await api("/auth/logout", { method: "POST" });
                  router.push("/");
                }}
              >
                <LogOut size={14} />
                {t.logout}
              </button>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">{children}</main>
      </div>
    </div>
  );
}
