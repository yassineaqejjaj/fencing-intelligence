"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { CATEGORIES, api, type Athlete } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading } from "@/components/states";
import { Avatar, Badge, Card, PageHeader, RowLink } from "@/components/ui";

export default function AthletesPage() {
  const queryClient = useQueryClient();
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const [error, setError] = useState<unknown>(null);
  const create = useMutation({
    mutationFn: (body: Record<string, string>) => api("/athletes", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["athletes"] }),
  });
  if (athletes.isLoading) return <Loading />;
  if (athletes.isError) return <ErrorNote error={athletes.error} />;
  return (
    <div className="grid gap-6">
      <PageHeader eyebrow="Squad" title="Athletes" description="Hand, weapon, and objectives travel with every annotation they author or receive." />
      <Card>
        <form
          className="grid gap-3 md:grid-cols-4 md:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            setError(null);
            const birth = String(form.get("birth_year") || "");
            create.mutate(
              {
                display_name: String(form.get("display_name")),
                weapon: String(form.get("weapon")),
                dominant_hand: String(form.get("dominant_hand")),
                country: String(form.get("country") || ""),
                experience_level: "club",
                training_objectives: "",
                license_number: String(form.get("license_number") || ""),
                ...(birth ? { birth_year: birth } : {}),
                category: String(form.get("category") || "unspecified"),
              },
              { onError: setError },
            );
            event.currentTarget.reset();
          }}
        >
          <Field label="Name"><input className={inputClass} name="display_name" required /></Field>
          <Field label="Weapon">
            <select className={inputClass} name="weapon" defaultValue="epee">
              <option value="epee">Épée</option>
              <option value="foil">Foil</option>
              <option value="sabre">Sabre</option>
            </select>
          </Field>
          <Field label="Hand">
            <select className={inputClass} name="dominant_hand" defaultValue="right">
              <option value="right">Right</option>
              <option value="left">Left</option>
            </select>
          </Field>
          <Field label="Country"><input className={inputClass} name="country" /></Field>
          <Field label="License no."><input className={inputClass} name="license_number" placeholder="FRA-…" /></Field>
          <Field label="Birth year"><input className={inputClass} name="birth_year" type="number" min={1900} max={2030} /></Field>
          <Field label="Category">
            <select className={inputClass} name="category" defaultValue="unspecified">
              {CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
            </select>
          </Field>
          <button className={buttonClass} type="submit"><Plus size={15} /> Add</button>
        </form>
        {error ? <div className="mt-3"><ErrorNote error={error} /></div> : null}
      </Card>
      {athletes.data?.items.length ? (
        <ul className="grid gap-3 md:grid-cols-2">
          {athletes.data.items.map((athlete, index) => (
            <li key={athlete.id}>
              <RowLink href={`/athletes/${athlete.id}`}>
                <span className="fi-rise flex flex-1 items-center gap-3 rounded-3xl border border-line bg-gradient-to-b from-surface to-surface p-4" style={{ animationDelay: `${Math.min(index, 6) * 50}ms` }}>
                  <Avatar name={athlete.display_name} />
                  <span className="min-w-0">
                    <span className="block truncate font-medium">{athlete.display_name}</span>
                    <span className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <Badge tone="info">{athlete.weapon}</Badge>
                      {athlete.dominant_hand} hand
                      {athlete.license_number ? <span className="font-mono">{athlete.license_number}</span> : <span>No license</span>}
                      {athlete.category !== "unspecified" ? <span>{athlete.category}</span> : null}
                    </span>
                  </span>
                </span>
              </RowLink>
            </li>
          ))}
        </ul>
      ) : <Empty>No athletes yet.</Empty>}
    </div>
  );
}
