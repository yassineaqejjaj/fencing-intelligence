"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trophy } from "lucide-react";
import { api, type Competition } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading } from "@/components/states";
import { Avatar, Badge, Card, PageHeader, RowLink } from "@/components/ui";

export default function CompetitionsPage() {
  const queryClient = useQueryClient();
  const competitions = useQuery({ queryKey: ["competitions"], queryFn: () => api<{ items: Competition[] }>("/competitions") });
  const [error, setError] = useState<unknown>(null);
  const create = useMutation({
    mutationFn: (body: Record<string, string>) => api("/competitions", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["competitions"] }),
  });
  if (competitions.isLoading) return <Loading />;
  if (competitions.isError) return <ErrorNote error={competitions.error} />;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Directoire technique"
        title="Competitions"
        description="Entries, poule sheets, standings, and the DE draw — all generated from stored records."
      />
      <Card>
        <form
          className="grid gap-3 md:grid-cols-[1.4fr_1fr_1fr_1fr_auto] md:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            setError(null);
            const start = String(form.get("start_date") || "");
            create.mutate(
              {
                name: String(form.get("name")),
                weapon: String(form.get("weapon")),
                category: String(form.get("category") || ""),
                ...(start ? { start_date: start } : {}),
              },
              { onError: setError },
            );
            event.currentTarget.reset();
          }}
        >
          <Field label="Name"><input className={inputClass} name="name" required placeholder="Regional Open" /></Field>
          <Field label="Weapon">
            <select className={inputClass} name="weapon" defaultValue="epee">
              <option value="epee">Épée</option>
              <option value="foil">Foil</option>
              <option value="sabre">Sabre</option>
            </select>
          </Field>
          <Field label="Category"><input className={inputClass} name="category" placeholder="u17" /></Field>
          <Field label="Start"><input className={inputClass} name="start_date" type="date" /></Field>
          <button className={buttonClass} type="submit"><Plus size={15} /> Create</button>
        </form>
        {error ? <div className="mt-3"><ErrorNote error={error} /></div> : null}
      </Card>
      {competitions.data?.items.length ? (
        <ul className="grid gap-3 md:grid-cols-2">
          {competitions.data.items.map((competition) => (
            <li key={competition.id}>
              <RowLink href={`/competitions/${competition.id}`}>
                <span className="flex flex-1 items-center gap-3 rounded-3xl border border-line bg-gradient-to-b from-surface to-surface p-4">
                  <Avatar name={competition.name} />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{competition.name}</span>
                    <span className="mt-1 flex items-center gap-2 text-xs text-muted">
                      {competition.weapon ? <Badge tone="info">{competition.weapon}</Badge> : <Trophy size={13} />}
                      {competition.start_date ?? "Date unset"}
                    </span>
                  </span>
                </span>
              </RowLink>
            </li>
          ))}
        </ul>
      ) : <Empty>No competitions yet. Create the event before entries open.</Empty>}
    </div>
  );
}
