"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Clapperboard, FlaskConical } from "lucide-react";
import { api, type Athlete, type Intelligence } from "@/lib/api";
import { IntelligenceView } from "@/components/intelligence-view";
import { Empty, ErrorNote, inputClass, Loading } from "@/components/states";
import { PageHeader } from "@/components/ui";
import { useI18n } from "@/lib/i18n";

type Suggestion = {
  observation: string;
  evidence_level: string;
  evidence: { metric: string; value: number; denominator: number };
  exercise: { name_en: string; description_en: string };
  video_references: { video_id: string; start_ms: number }[];
};

export default function CoachPage() {
  const { locale } = useI18n();
  const [athleteId, setAthleteId] = useState("");
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const intelligence = useQuery({
    queryKey: ["intelligence", athleteId],
    enabled: Boolean(athleteId),
    queryFn: () => api<Intelligence>(`/athletes/${athleteId}/intelligence`),
  });
  const recommendations = useQuery({
    queryKey: ["recommendations", athleteId],
    enabled: Boolean(athleteId),
    queryFn: () => api<{ data_status: string; items: Suggestion[] }>(`/athletes/${athleteId}/recommendations`),
  });
  if (athletes.isLoading) return <Loading />;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={locale === "fr" ? "Espace maître" : "Coach workspace"}
        title={locale === "fr" ? "Ce que les enregistrements suggèrent" : "What the records suggest"}
        description={
          locale === "fr"
            ? "La lecture d'abord, puis les exercices assemblés depuis les statistiques validées. Aucun modèle de langue n'invente une consigne."
            : "The reading first, then drills assembled from validated statistics. No language model invents a cue."
        }
      />
      <label className="grid max-w-md gap-1.5 text-sm">
        <span className="text-xs font-medium tracking-wide text-muted uppercase">Athlete</span>
        <select className={inputClass} value={athleteId} onChange={(event) => setAthleteId(event.target.value)}>
          <option value="">Choose an athlete</option>
          {athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}
        </select>
      </label>
      {intelligence.isLoading || recommendations.isLoading ? <Loading /> : null}
      {intelligence.isError ? <ErrorNote error={intelligence.error} /> : null}
      {recommendations.isError ? <ErrorNote error={recommendations.error} /> : null}
      {intelligence.data ? <IntelligenceView data={intelligence.data} compact athleteHref={`/athletes/${athleteId}`} /> : null}
      {recommendations.data && recommendations.data.items.length === 0 ? <Empty>No drill is suggested. There is not enough validated evidence, or the measured rates do not cross a threshold.</Empty> : null}
      <ul className="grid gap-4 lg:grid-cols-2">
        {recommendations.data?.items.map((item, index) => (
          <li
            key={item.evidence.metric}
            className="fi-rise rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-6"
            style={{ animationDelay: `${index * 70}ms` }}
          >
            <p className="flex items-center gap-2 text-[11px] font-semibold tracking-[0.16em] text-primary uppercase">
              <FlaskConical size={14} /> Evidence · {item.evidence_level}
            </p>
            <p className="mt-3 text-xl leading-snug font-semibold tracking-tight">{item.observation}</p>
            <div className="mt-4">
              <div className="flex items-baseline justify-between text-xs text-muted">
                <span className="font-mono">{item.evidence.metric}</span>
                <span className="tabular-nums">{(item.evidence.value * 100).toFixed(1)}% · {item.evidence.denominator} samples</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/10">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-primary to-secondary"
                  style={{ width: `${Math.round(item.evidence.value * 100)}%` }}
                />
              </div>
            </div>
            <div className="mt-5 rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="font-medium">{item.exercise.name_en}</p>
              <p className="mt-1 text-sm leading-relaxed text-muted">{item.exercise.description_en}</p>
            </div>
            {item.video_references.length ? (
              <Link
                href={`/videos/${item.video_references[0].video_id}`}
                className="mt-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-sm font-medium transition-colors hover:bg-white/[0.1]"
              >
                <Clapperboard size={15} className="text-primary" /> Open the bout clip
              </Link>
            ) : <p className="mt-4 text-sm text-muted">No unsuccessful clip was linked.</p>}
          </li>
        ))}
      </ul>
    </div>
  );
}
