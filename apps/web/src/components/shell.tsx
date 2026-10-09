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
} from "lucide-react";
import { api, type User } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { Loading } from "./states";

const sections = [
  {
    label: "Analyse",
    links: [
      ["dashboard", "/dashboard", LayoutDashboard],
      ["videos", "/videos", Clapperboard],
      ["bouts", "/bouts", Swords],
      ["athletes", "/athletes", Users],
    ],
  },
  {
    label: "Lecture",
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
    label: "Système",
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
      <aside className="border-b border-line bg-surface lg:sticky lg:top-0 lg:h-screen lg:border-r lg:border-b-0">
        <div className="flex items-center gap-3 px-5 pt-5 pb-2">
          <Link href="/dashboard" className="leading-none" aria-label={t.product}>
            <span className="block text-[15px] font-bold tracking-tight uppercase">Fencing</span>
            <span className="block text-[15px] font-bold tracking-tight uppercase">Intelligence</span>
            <span className="mt-1 block font-mono text-[10px] tracking-[0.14em] text-muted uppercase">{locale === "fr" ? "Salle d'armes" : "Salle"}</span>
          </Link>
        </div>
        <nav className="flex gap-5 overflow-x-auto px-4 pt-3 pb-4 lg:flex-col lg:gap-1 lg:overflow-visible" aria-label="Main">
          {sections.map((section) => (
            <div key={section.label} className="min-w-max lg:min-w-0">
              <p className="hidden px-3 pt-4 pb-1.5 font-mono text-[10px] tracking-[0.16em] text-muted uppercase lg:block">
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
                      className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors duration-200 ease-out active:scale-[0.98] motion-reduce:transform-none ${
                        current
                          ? "bg-mask font-medium text-tenue"
                          : "text-muted hover:bg-tenue hover:text-text"
                      }`}
                    >
                      <Icon size={16} className={current ? "text-voyant" : ""} />
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
        <header className="sticky top-0 z-10 border-b border-line bg-background/90 backdrop-blur-md">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 md:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-mask font-mono text-[11px] font-medium text-tenue">
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
                className="rounded border border-line bg-surface px-2.5 py-1 font-mono text-[11px] text-muted hover:text-text active:scale-[0.98]"
                onClick={() => setLocale(locale === "en" ? "fr" : "en")}
                aria-label="Language"
              >
                {locale === "en" ? "FR" : "EN"}
              </button>
              <button
                type="button"
                className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium text-muted hover:bg-tenue hover:text-text active:scale-[0.98]"
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
