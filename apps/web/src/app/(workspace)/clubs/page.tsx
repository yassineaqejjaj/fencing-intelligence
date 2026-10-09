"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading } from "@/components/states";

export default function ClubsPage() {
  const queryClient = useQueryClient();
  const clubs = useQuery({ queryKey: ["clubs"], queryFn: () => api<{ items: { id: string; name: string; country: string; city: string }[] }>("/clubs") });
  const org = useQuery({ queryKey: ["org"], queryFn: () => api<{ name: string; members: { email: string; role: string; display_name: string }[] }>("/organizations/current") });
  const [error, setError] = useState<unknown>(null);
  const create = useMutation({
    mutationFn: (body: Record<string, string>) => api("/clubs", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["clubs"] }),
  });
  if (clubs.isLoading || org.isLoading) return <Loading />;
  if (clubs.isError || org.isError) return <ErrorNote error={clubs.error || org.error} />;
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-semibold">{org.data?.name}</h1>
      <form className="grid gap-3 rounded-lg bg-surface p-4 md:grid-cols-3" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        create.mutate({ name: String(form.get("name")), country: String(form.get("country") || ""), city: String(form.get("city") || "") }, { onError: setError });
      }}>
        <Field label="Club name"><input className={inputClass} name="name" required /></Field>
        <Field label="Country"><input className={inputClass} name="country" /></Field>
        <Field label="City"><input className={inputClass} name="city" /></Field>
        <button className={buttonClass} type="submit">Create club</button>
      </form>
      {error ? <ErrorNote error={error} /> : null}
      {clubs.data?.items.length ? <ul className="grid gap-2">{clubs.data.items.map((club) => <li key={club.id} className="rounded-lg bg-surface px-4 py-3">{club.name} · {club.city} {club.country}</li>)}</ul> : <Empty>No club yet.</Empty>}
      <h2 className="text-lg">Members</h2>
      <ul className="grid gap-2">{org.data?.members.map((member) => <li key={member.email} className="rounded-lg bg-surface px-4 py-3">{member.display_name} · {member.role}</li>)}</ul>
    </div>
  );
}
