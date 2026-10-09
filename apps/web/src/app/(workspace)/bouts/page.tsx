"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { api, type Athlete, type CompetitionBout } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading } from "@/components/states";
import { Avatar, Badge, Card, PageHeader, RowLink, ScorePill } from "@/components/ui";

export default function BoutsPage() {
  const queryClient = useQueryClient();
  const bouts = useQuery({ queryKey: ["bouts"], queryFn: () => api<{ items: CompetitionBout[] }>("/bouts") });
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const [error, setError] = useState<unknown>(null);
  const create = useMutation({
    mutationFn: (body: Record<string, string>) => api("/bouts", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bouts"] }),
  });
  if (bouts.isLoading || athletes.isLoading) return <Loading />;
  if (bouts.isError || athletes.isError) return <ErrorNote error={bouts.error || athletes.error} />;
  const names = Object.fromEntries((athletes.data?.items || []).map((athlete) => [athlete.id, athlete.display_name]));
  return (
    <div className="grid gap-6">
      <PageHeader eyebrow="Poules & DEs" title="Bouts" description="A bout pairs two athletes and collects every touch, phrase, and clip." />
      <Card>
        <form
          className="grid gap-3 md:grid-cols-[1fr_1fr_1fr_1fr_auto] md:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const started = String(form.get("started_on") || "");
            create.mutate(
              {
                weapon: String(form.get("weapon")),
                left_athlete_id: String(form.get("left")),
                right_athlete_id: String(form.get("right")),
                ...(started ? { started_on: started } : {}),
              },
              { onError: setError },
            );
          }}
        >
          <Field label="Weapon">
            <select className={inputClass} name="weapon" defaultValue="epee"><option value="epee">Épée</option><option value="foil">Foil</option><option value="sabre">Sabre</option></select>
          </Field>
          <Field label="Left"><select className={inputClass} name="left" required>{athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}</select></Field>
          <Field label="Right"><select className={inputClass} name="right" required>{athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}</select></Field>
          <Field label="Date"><input className={inputClass} name="started_on" type="date" /></Field>
          <button className={buttonClass} type="submit"><Plus size={15} /> Create</button>
        </form>
        {error ? <div className="mt-3"><ErrorNote error={error} /></div> : null}
      </Card>
      {bouts.data?.items.length ? (
        <Card className="!p-2">
          <ul className="divide-y divide-white/[0.07]">
            {bouts.data.items.map((bout) => (
              <li key={bout.id}>
                <RowLink href={`/bouts/${bout.id}`}>
                  <Avatar name={`${names[bout.left?.athlete_id || ""] || "Left"} ${names[bout.right?.athlete_id || ""] || "Right"}`} size="sm" />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{names[bout.left?.athlete_id || ""] || "Left"} <span className="text-muted">vs</span> {names[bout.right?.athlete_id || ""] || "Right"}</span>
                    <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted"><Badge tone="info">{bout.weapon}</Badge>{bout.bracket_label || bout.started_on || "Friendly"}{bout.status === "completed" ? " · final" : null}</span>
                  </span>
                  <ScorePill left={bout.left?.score ?? 0} right={bout.right?.score ?? 0} />
                </RowLink>
              </li>
            ))}
          </ul>
        </Card>
      ) : <Empty>No bouts yet.</Empty>}
    </div>
  );
}
