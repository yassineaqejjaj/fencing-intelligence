"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ErrorNote, Loading } from "@/components/states";

export default function ModelsPage() {
  const models = useQuery({ queryKey: ["models"], queryFn: () => api<{ items: { id: string; name: string; version: string; status: string; notes: string; metrics: Record<string, unknown> }[] }>("/models") });
  if (models.isLoading) return <Loading />;
  if (models.isError) return <ErrorNote error={models.error} />;
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-semibold">Models</h1>
      <p className="text-muted">Nothing on this page is a validated fencing recognizer.</p>
      <ul className="grid gap-3">
        {models.data?.items.map((model) => (
          <li key={model.id} className="rounded-lg bg-surface p-4">
            <p className="font-medium">{model.name} {model.version}</p>
            <p className="text-sm text-warning">{model.status}</p>
            <p className="mt-2 text-sm">{model.notes}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
