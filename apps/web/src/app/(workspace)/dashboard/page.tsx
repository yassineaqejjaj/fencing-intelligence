"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ChartLine, Clapperboard, Plus, Swords, Users } from "lucide-react";
import { api, type Intelligence } from "@/lib/api";
import { IntelligenceView } from "@/components/intelligence-view";
import { ErrorNote, Loading } from "@/components/states";
import { Avatar, Badge, Card, PageHeader, RowLink, ScorePill, StatCard } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

type Athlete = { id: string; display_name: string; weapon: string; dominant_hand: string };
type Bout = {
  id: string;
  weapon: string;
  started_on: string | null;
  notes: string;
  left: { athlete_id: string; score: number } | null;
  right: { athlete_id: string; score: number } | null;
};

export default function DashboardPage() {
  const { locale } = useI18n();
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[]; total: number }>("/athletes") });
  const videos = useQuery({ queryKey: ["videos"], queryFn: () => api<{ total: number }>("/videos") });
  const bouts = useQuery({ queryKey: ["bouts"], queryFn: () => api<{ items: Bout[] }>("/bouts") });
  if (athletes.isLoading || videos.isLoading || bouts.isLoading) return <Loading />;
  if (athletes.isError || videos.isError || bouts.isError) return <ErrorNote error={athletes.error || videos.error || bouts.error} />;

  const names = new Map((athletes.data?.items ?? []).map((athlete) => [athlete.id, athlete.display_name]));
  const recent = [...(bouts.data?.items ?? [])].sort((a, b) => (b.started_on ?? "").localeCompare(a.started_on ?? "")).slice(0, 4);
  const demo = recent.some((bout) => bout.notes.toLowerCase().includes("invented"));

  const focusId = recent[0]?.left?.athlete_id ?? athletes.data?.items[0]?.id;

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={locale === "fr" ? "Aujourd'hui" : "Today"}
        title="The salle"
        description={
          demo
            ? locale === "fr"
              ? "La poule ci-dessous est inventée pour la démo. Chaque taux est calculé à partir de ces enregistrements."
              : "The poule below is invented so you can walk the review. Every rate is calculated from those records."
            : athletes.data?.total === 0
              ? locale === "fr"
                ? "Créez un club et un athlète, puis importez une vidéo d'assaut pour commencer une revue."
                : "Create a club and an athlete, then upload a bout video to start a review."
              : locale === "fr"
                ? "Reprenez là où la dernière phrase s'est arrêtée."
                : "Pick up where the last phrase left off."
        }
        actions={
          <>
            <Link href="/videos/upload" className="inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-4 py-2 text-sm font-semibold text-[#04121a] shadow-[0_8px_32px_-8px_rgb(0_212_255/0.5)] transition-all hover:brightness-110 active:scale-[0.97]">
              <Plus size={15} /> Upload bout
            </Link>
            <Link href="/bouts" className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm font-medium transition-colors hover:bg-white/[0.1]">
              <Swords size={15} /> New bout
            </Link>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard icon={Users} label="Athletes" value={String(athletes.data?.total ?? 0)} href="/athletes" />
        <StatCard icon={Clapperboard} label="Videos" value={String(videos.data?.total ?? 0)} href="/videos" />
        <StatCard icon={Swords} label="Bouts" value={String(bouts.data?.items.length ?? 0)} href="/bouts" />
      </div>

      {focusId ? <FocusReading athleteId={focusId} href={`/athletes/${focusId}`} /> : null}

      <div className="grid gap-6 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-semibold tracking-wide">Recent bouts</h2>
            <Link href="/bouts" className="text-sm text-primary hover:brightness-125">All bouts</Link>
          </div>
          {recent.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">No bouts yet.</p>
          ) : (
            <ul className="divide-y divide-white/[0.07]">
              {recent.map((bout) => (
                <li key={bout.id}>
                  <RowLink href={`/bouts/${bout.id}`}>
                    <div className="min-w-0">
                      <p className="truncate text-[15px] font-medium">
                        {names.get(bout.left?.athlete_id ?? "") ?? "Left"}
                        <span className="mx-2 text-muted">vs</span>
                        {names.get(bout.right?.athlete_id ?? "") ?? "Right"}
                      </p>
                      <p className="mt-1 flex items-center gap-2 text-xs text-muted">
                        <Badge tone="info">{bout.weapon}</Badge>
                        {bout.started_on ?? "Date unset"}
                      </p>
                    </div>
                    <ScorePill left={bout.left?.score ?? 0} right={bout.right?.score ?? 0} />
                  </RowLink>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <div className="mb-2 flex items-center justify-between">
            <h2 className="flex items-center gap-2 text-sm font-semibold tracking-wide">
              <ChartLine size={15} className="text-primary" /> Athletes
            </h2>
            <Link href="/athletes" className="text-sm text-primary hover:brightness-125">All athletes</Link>
          </div>
          <ul className="grid gap-1">
            {(athletes.data?.items ?? []).slice(0, 5).map((athlete) => (
              <li key={athlete.id}>
                <RowLink href={`/athletes/${athlete.id}`}>
                  <Avatar name={athlete.display_name} size="sm" />
                  <span className="min-w-0">
                    <span className="block truncate text-[15px] font-medium">{athlete.display_name}</span>
                    <span className="block text-xs text-muted capitalize">{athlete.weapon} · {athlete.dominant_hand} hand</span>
                  </span>
                </RowLink>
              </li>
            ))}
          </ul>
          {(athletes.data?.items ?? []).length === 0 ? <p className="py-6 text-center text-sm text-muted">No athletes yet.</p> : null}
        </Card>
      </div>
    </div>
  );
}

function FocusReading({ athleteId, href }: { athleteId: string; href: string }) {
  const { locale } = useI18n();
  const intelligence = useQuery({
    queryKey: ["intelligence", athleteId],
    queryFn: () => api<Intelligence>(`/athletes/${athleteId}/intelligence`),
  });
  if (intelligence.isLoading) return <Loading />;
  if (intelligence.isError || !intelligence.data) return null;
  return (
    <section className="grid gap-3">
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold tracking-wide">
            {locale === "fr" ? "Lecture du jour" : "Today's reading"}
          </h2>
          <p className="text-xs text-muted">
            {locale === "fr"
              ? "Phrases issues des actions et touches validées — rien n'est inventé."
              : "Sentences from validated actions and touches — nothing is invented."}
          </p>
        </div>
      </div>
      <IntelligenceView data={intelligence.data} compact athleteHref={href} />
    </section>
  );
}
