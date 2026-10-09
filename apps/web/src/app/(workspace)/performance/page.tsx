"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { IntelligenceView } from "@/components/intelligence-view";
import { StatsView } from "@/components/stats-view";
import { Empty, ErrorNote, inputClass, Loading } from "@/components/states";
import { PageHeader } from "@/components/ui";
import { api, type Athlete, type AthleteStats, type Intelligence } from "@/lib/api";
import { useI18n } from "@/lib/i18n";

export default function PerformancePage() {
  const { locale } = useI18n();
  const [athleteId, setAthleteId] = useState("");
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const intelligence = useQuery({
    queryKey: ["intelligence", athleteId],
    enabled: Boolean(athleteId),
    queryFn: () => api<Intelligence>(`/athletes/${athleteId}/intelligence`),
  });
  const stats = useQuery({
    queryKey: ["stats", athleteId],
    enabled: Boolean(athleteId),
    queryFn: () => api<AthleteStats>(`/athletes/${athleteId}/statistics`),
  });
  if (athletes.isLoading) return <Loading />;
  if (athletes.isError) return <ErrorNote error={athletes.error} />;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={locale === "fr" ? "Lecture du tireur" : "Athlete reading"}
        title={locale === "fr" ? "Ce que la piste dit" : "What the piste is saying"}
        description={
          locale === "fr"
            ? "Phrases en langage de salle, puis les chiffres. Rien n'est inventé : seulement des actions et des touches validées."
            : "Plain-language readings first, then the numbers. Nothing is invented — only validated actions and touches."
        }
      />
      <label className="grid max-w-md gap-1.5 text-sm">
        <span className="text-xs font-medium tracking-wide text-muted uppercase">{locale === "fr" ? "Athlète" : "Athlete"}</span>
        <select className={inputClass} value={athleteId} onChange={(event) => setAthleteId(event.target.value)}>
          <option value="">{locale === "fr" ? "Choisir un athlète" : "Choose an athlete"}</option>
          {athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}
        </select>
      </label>
      {!athleteId ? <Empty>{locale === "fr" ? "Choisissez un athlète pour voir la lecture. Les graphiques n'apparaissent pas sans données validées." : "Select an athlete to see the reading. Charts are not shown without that data."}</Empty> : null}
      {intelligence.isLoading || stats.isLoading ? <Loading /> : null}
      {intelligence.isError ? <ErrorNote error={intelligence.error} /> : null}
      {stats.isError ? <ErrorNote error={stats.error} /> : null}
      {intelligence.data ? <IntelligenceView data={intelligence.data} /> : null}
      {stats.data ? (
        <section className="grid gap-3">
          <div>
            <h2 className="font-semibold">{locale === "fr" ? "Les chiffres" : "The numbers"}</h2>
            <p className="text-xs text-muted">
              {locale === "fr"
                ? "Taux et volumes calculés uniquement sur les actions et touches validées."
                : "Rates and counts from validated actions and touches only."}
            </p>
          </div>
          <StatsView stats={stats.data} />
        </section>
      ) : null}
    </div>
  );
}
