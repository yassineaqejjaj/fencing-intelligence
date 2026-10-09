"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type BoutMomentum, type BoutReading, type CompetitionBout } from "@/lib/api";
import { BoutReadingView, BoutStory } from "@/components/intelligence-view";
import { buttonClass, ErrorNote, Loading, secondaryButton } from "@/components/states";
import { Badge, PageHeader, ScorePill } from "@/components/ui";

export default function BoutPage() {
  const params = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const bout = useQuery({ queryKey: ["bout", params.id], queryFn: () => api<CompetitionBout>(`/bouts/${params.id}`) });
  const momentum = useQuery({
    queryKey: ["momentum", params.id],
    queryFn: () => api<BoutMomentum>(`/bouts/${params.id}/momentum`),
  });
  const reading = useQuery({
    queryKey: ["bout-reading", params.id],
    queryFn: () => api<BoutReading>(`/bouts/${params.id}/reading`),
  });
  const complete = useMutation({
    mutationFn: () => api(`/bouts/${params.id}/complete`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bout", params.id] }),
  });
  if (bout.isLoading) return <Loading />;
  if (bout.isError) return <ErrorNote error={bout.error} />;
  const row = bout.data;
  if (!row) return <Loading />;
  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={row.round ? `${row.round} · ${row.bracket_label}` : row.bracket_label || "Friendly bout"}
        title={`${row.weapon} bout`}
        description={row.competition_id ? undefined : "Not attached to a competition."}
        actions={
          <>
            {row.competition_id ? <Link href={`/competitions/${row.competition_id}`} className={secondaryButton}>Open event</Link> : null}
            <Link href={`/videos/upload?bout=${row.id}`} className={secondaryButton}>Upload bout video</Link>
            {row.status !== "completed" ? <button type="button" className={buttonClass} onClick={() => complete.mutate()}>Complete bout</button> : null}
          </>
        }
      />
      <div className="flex flex-wrap items-center gap-3">
        <ScorePill left={row.left?.score ?? 0} right={row.right?.score ?? 0} />
        <Badge tone={row.status === "completed" ? "success" : row.status === "in_progress" ? "warning" : "neutral"}>{row.status}</Badge>
        {row.piste ? <Badge tone="neutral">Piste {row.piste}</Badge> : null}
      </div>
      {complete.isError ? <ErrorNote error={complete.error} /> : null}
      {reading.isError ? <ErrorNote error={reading.error} /> : null}
      {reading.isLoading ? <Loading /> : null}
      {reading.data ? <BoutReadingView data={reading.data} /> : null}
      {momentum.data ? <BoutStory data={momentum.data} /> : null}
    </div>
  );
}
