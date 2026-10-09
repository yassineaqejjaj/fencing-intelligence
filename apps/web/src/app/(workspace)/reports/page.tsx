"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Athlete } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading } from "@/components/states";

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const reports = useQuery({ queryKey: ["reports"], queryFn: () => api<{ items: { id: string; title: string; kind: string }[] }>("/reports") });
  const [url, setUrl] = useState("");
  const create = useMutation({
    mutationFn: (body: Record<string, string>) => api<{ id: string }>("/reports", { method: "POST", body: JSON.stringify(body) }),
    onSuccess: async (created) => {
      const download = await api<{ url: string }>(`/reports/${created.id}/download`);
      setUrl(download.url);
      await queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
  });
  if (athletes.isLoading || reports.isLoading) return <Loading />;
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-semibold">Reports</h1>
      <form className="grid gap-3 rounded-lg bg-surface p-4 md:grid-cols-3" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        create.mutate({ kind: "athlete", athlete_id: String(form.get("athlete_id")), title: String(form.get("title") || "Performance report") });
      }}>
        <Field label="Athlete"><select className={inputClass} name="athlete_id" required>{athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}</select></Field>
        <Field label="Title"><input className={inputClass} name="title" placeholder="Performance report" /></Field>
        <button className={buttonClass} type="submit">Generate PDF</button>
      </form>
      {create.isError ? <ErrorNote error={create.error} /> : null}
      {url ? <a className="text-primary" href={url}>Download the latest report</a> : null}
      {reports.data?.items.length ? <ul>{reports.data.items.map((report) => <li key={report.id} className="py-1">{report.title}</li>)}</ul> : <Empty>No reports generated.</Empty>}
    </div>
  );
}
