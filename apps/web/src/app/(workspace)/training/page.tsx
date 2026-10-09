"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Athlete } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading } from "@/components/states";

export default function TrainingPage() {
  const queryClient = useQueryClient();
  const sessions = useQuery({ queryKey: ["sessions"], queryFn: () => api<{ items: { id: string; title: string; training_load: number | null; training_load_reason: string | null; rpe: number | null; duration_minutes: number | null }[] }>("/training/sessions") });
  const exercises = useQuery({ queryKey: ["exercises"], queryFn: () => api<{ items: { id: string; name_en: string; duration_minutes: number }[] }>("/training/exercises") });
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const create = useMutation({
    mutationFn: (body: Record<string, string | number | null>) => api("/training/sessions", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["sessions"] }),
  });
  if (sessions.isLoading || exercises.isLoading) return <Loading />;
  if (sessions.isError || exercises.isError) return <ErrorNote error={sessions.error || exercises.error} />;
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-semibold">Training</h1>
      <form className="grid gap-3 rounded-lg bg-surface p-4 md:grid-cols-4" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const duration = Number(form.get("duration") || 0);
        const rpe = Number(form.get("rpe") || 0);
        create.mutate({
          title: String(form.get("title")),
          athlete_id: String(form.get("athlete_id") || "") || null,
          duration_minutes: duration || null,
          rpe: rpe || null,
          scheduled_for: form.get("scheduled_for") ? `${form.get("scheduled_for")}T18:00:00+00:00` : null,
        });
      }}>
        <Field label="Title"><input className={inputClass} name="title" required /></Field>
        <Field label="Athlete"><select className={inputClass} name="athlete_id"><option value="">None</option>{athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}</select></Field>
        <Field label="Minutes"><input className={inputClass} name="duration" type="number" min={1} /></Field>
        <Field label="RPE"><input className={inputClass} name="rpe" type="number" min={1} max={10} /></Field>
        <Field label="Date"><input className={inputClass} name="scheduled_for" type="date" /></Field>
        <button className={buttonClass} type="submit">Plan session</button>
      </form>
      {create.isError ? <ErrorNote error={create.error} /> : null}
      <h2 className="text-lg">Exercise library</h2>
      <ul className="grid gap-2">{exercises.data?.items.map((exercise) => <li key={exercise.id} className="rounded-lg bg-surface px-4 py-3">{exercise.name_en} · {exercise.duration_minutes} min</li>)}</ul>
      <h2 className="text-lg">Sessions</h2>
      {sessions.data?.items.length ? sessions.data.items.map((session) => (
        <p key={session.id} className="rounded-lg bg-surface px-4 py-3">{session.title} · load {session.training_load ?? "not available"}{session.training_load_reason ? ` (${session.training_load_reason})` : ""}</p>
      )) : <Empty>No sessions planned.</Empty>}
    </div>
  );
}
