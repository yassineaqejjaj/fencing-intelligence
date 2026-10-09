"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ErrorNote, Loading } from "@/components/states";

type Doctor = { counts: Record<string, number>; datasets: { name: string; presence: string; compatibility: string; license: string; notes: string; source_url: string }[] };

export default function DatasetsPage() {
  const doctor = useQuery({ queryKey: ["doctor"], queryFn: () => api<Doctor>("/datasets/doctor") });
  if (doctor.isLoading) return <Loading />;
  if (doctor.isError) return <ErrorNote error={doctor.error} />;
  return (
    <div className="grid gap-4">
      <h1 className="text-2xl font-semibold">Datasets</h1>
      <p className="text-sm text-muted">Installed {doctor.data?.counts.installed ?? 0} · missing {doctor.data?.counts.missing ?? 0} · restricted {doctor.data?.counts.restricted ?? 0} · incompatible {doctor.data?.counts.incompatible ?? 0}</p>
      <p className="text-sm text-muted">MFAD, the Fencing Footwork Dataset, fencing-AI, and FencingVision are recognized here. Their files are not included, because those repositories do not grant a license to copy them. Put a copy you are allowed to use under data/datasets/&lt;name&gt; and run the import from the API.</p>
      <ul className="grid gap-3">
        {doctor.data?.datasets.map((item) => (
          <li key={item.name} className="rounded-lg bg-surface p-4">
            <p className="font-medium">{item.name}</p>
            {item.source_url.startsWith("http") ? <a className="text-sm text-primary" href={item.source_url}>{item.source_url}</a> : null}
            <p className="text-sm text-muted">{item.presence} · {item.compatibility} · {item.license}</p>
            <p className="mt-2 text-sm">{item.notes}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
