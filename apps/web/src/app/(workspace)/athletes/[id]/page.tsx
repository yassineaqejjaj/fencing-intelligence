"use client";

import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { IntelligenceView } from "@/components/intelligence-view";
import { StatsView } from "@/components/stats-view";
import { buttonClass, ErrorNote, Field, inputClass, Loading } from "@/components/states";
import { Badge, Card, PageHeader } from "@/components/ui";
import { CATEGORIES, api, type Athlete, type AthleteStats, type Intelligence } from "@/lib/api";

function GuardianConsentCard({ athleteId, granted }: { athleteId: string; granted: boolean | null }) {
  const queryClient = useQueryClient();
  const record = useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api(`/athletes/${athleteId}/guardian-consent`, { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["athlete", athleteId] }),
  });
  return (
    <Card>
      <h2 className="mb-2 text-sm font-semibold tracking-wide">Guardian consent</h2>
      <p className="mb-4 text-sm text-muted">
        This athlete is a minor. Videos stay private and training use is blocked until a guardian consent is recorded.
        Current status: <strong>{granted ? "granted" : "missing"}</strong>.
      </p>
      <form
        className="grid gap-3 md:grid-cols-3 md:items-end"
        onSubmit={(event) => {
          event.preventDefault();
          const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
          const form = new FormData(event.currentTarget, submitter ?? undefined);
          record.mutate({
            granted: String(form.get("decision") || "") === "grant",
            guardian_name: String(form.get("guardian_name") || ""),
            note: String(form.get("note") || ""),
          });
        }}
      >
        <Field label="Guardian name"><input className={inputClass} name="guardian_name" /></Field>
        <Field label="Note (where/when signed)"><input className={inputClass} name="note" /></Field>
        <div className="flex gap-2">
          <button className={buttonClass} type="submit" name="decision" value="grant">Record grant</button>
        </div>
      </form>
      <div className="mt-2 flex gap-2">
        <button
          className="rounded-md border border-line px-3 py-2 text-sm"
          type="button"
          onClick={() => record.mutate({ granted: false, guardian_name: "", note: "revoked" })}
        >
          Record revocation
        </button>
      </div>
      {record.isError ? <div className="mt-3"><ErrorNote error={record.error} /></div> : null}
    </Card>
  );
}

export default function AthletePage() {
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const athlete = useQuery({ queryKey: ["athlete", params.id], queryFn: () => api<Athlete>(`/athletes/${params.id}`) });
  const intelligence = useQuery({ queryKey: ["intelligence", params.id], queryFn: () => api<Intelligence>(`/athletes/${params.id}/intelligence`) });
  const stats = useQuery({ queryKey: ["stats", params.id], queryFn: () => api<AthleteStats>(`/athletes/${params.id}/statistics`) });
  const save = useMutation({
    mutationFn: (body: Record<string, unknown>) => api<Athlete>(`/athletes/${params.id}`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["athlete", params.id] }),
  });
  if (athlete.isLoading || stats.isLoading) return <Loading />;
  if (athlete.isError || stats.isError) return <ErrorNote error={athlete.error || stats.error} />;
  const row = athlete.data;
  if (!row) return <Loading />;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Athlete"
        title={row.display_name}
        description={`${row.weapon} · ${row.country || "country not set"} · ${row.experience_level}. Reading first, numbers second — only from validated actions.`}
      />
      <div className="flex flex-wrap gap-2">
        <Badge tone="info">{row.weapon}</Badge>
        {row.license_number ? <Badge tone="neutral">License {row.license_number}</Badge> : <Badge tone="warning">No license</Badge>}
        {row.category !== "unspecified" ? <Badge tone="neutral">{row.category}</Badge> : null}
        {row.birth_year ? <Badge tone="neutral">Born {row.birth_year}</Badge> : null}
        {row.is_minor ? <Badge tone="warning">Minor — guardian consent {row.guardian_consent_granted ? "recorded" : "missing"}</Badge> : null}
      </div>
      {row.is_minor ? <GuardianConsentCard athleteId={row.id} granted={row.guardian_consent_granted} /> : null}
      <Card>
        <h2 className="mb-4 text-sm font-semibold tracking-wide">Federation identity</h2>
        <form
          className="grid gap-3 md:grid-cols-4 md:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const birth = String(form.get("birth_year") || "");
            save.mutate({
              display_name: row.display_name,
              club_id: row.club_id,
              country: row.country,
              weapon: row.weapon,
              dominant_hand: row.dominant_hand,
              experience_level: row.experience_level,
              training_objectives: row.training_objectives,
              license_number: String(form.get("license_number") || ""),
              birth_year: birth ? Number(birth) : null,
              category: String(form.get("category") || "unspecified"),
            });
          }}
        >
          <Field label="License no."><input className={inputClass} name="license_number" defaultValue={row.license_number} /></Field>
          <Field label="Birth year"><input className={inputClass} name="birth_year" type="number" defaultValue={row.birth_year ?? ""} /></Field>
          <Field label="Category">
            <select className={inputClass} name="category" defaultValue={row.category}>
              {CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
            </select>
          </Field>
          <button className={buttonClass} type="submit">Save identity</button>
        </form>
        {save.isError ? <div className="mt-3"><ErrorNote error={save.error} /></div> : null}
      </Card>
      {intelligence.isError ? <ErrorNote error={intelligence.error} /> : null}
      {intelligence.data ? <IntelligenceView data={intelligence.data} /> : null}
      {stats.data ? <StatsView stats={stats.data} /> : null}
    </div>
  );
}
