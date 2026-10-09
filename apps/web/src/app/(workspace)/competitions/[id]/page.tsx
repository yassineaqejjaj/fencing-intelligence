"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Flag, Play, Swords, Trophy, Whistle } from "lucide-react";
import { api, type Athlete, type Competition, type CompetitionBout } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading, secondaryButton } from "@/components/states";
import { Badge, Card, PageHeader, ScorePill } from "@/components/ui";

type Entry = { athlete_id: string; display_name: string; seed: number };
type Standing = { athlete_id: string; display_name: string; bouts: number; victories: number; scored: number; conceded: number; indicator: number };
type Member = { user_id: string; display_name: string; role: string };

export default function CompetitionPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState("");
  const [failure, setFailure] = useState<unknown>(null);

  const competition = useQuery({ queryKey: ["competition", id], queryFn: () => api<Competition>(`/competitions/${id}`) });
  const entries = useQuery({ queryKey: ["entries", id], queryFn: () => api<{ items: Entry[] }>(`/competitions/${id}/entries`) });
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const bouts = useQuery({ queryKey: ["bouts"], queryFn: () => api<{ items: CompetitionBout[] }>("/bouts") });
  const table = useQuery({ queryKey: ["standings", id], queryFn: () => api<{ formula_version: number; items: Standing[] }>(`/competitions/${id}/standings`) });
  const members = useQuery({ queryKey: ["members"], queryFn: () => api<{ members: Member[] }>("/organizations/current") });

  const refresh = () => {
    setFailure(null);
    queryClient.invalidateQueries({ queryKey: ["entries", id] });
    queryClient.invalidateQueries({ queryKey: ["bouts"] });
    queryClient.invalidateQueries({ queryKey: ["standings", id] });
  };
  const act = async (work: () => Promise<unknown>, done: string) => {
    setNotice("");
    setFailure(null);
    try {
      await work();
      setNotice(done);
      refresh();
    } catch (caught) {
      setFailure(caught);
    }
  };

  if (competition.isLoading || entries.isLoading || bouts.isLoading) return <Loading />;
  if (competition.isError || entries.isError || bouts.isError) {
    return <ErrorNote error={competition.error || entries.error || bouts.error} />;
  }

  const names = new Map((athletes.data?.items ?? []).map((item) => [item.id, item.display_name]));
  const referees = new Map((members.data?.members ?? []).map((item) => [item.user_id, item.display_name]));
  const officials = (members.data?.members ?? []).filter((item) => ["coach", "club_administrator", "administrator"].includes(item.role));
  const eventBouts = (bouts.data?.items ?? []).filter((bout) => bout.competition_id === id);
  const pouleBouts = eventBouts.filter((bout) => bout.round === "poule");
  const deBouts = eventBouts.filter((bout) => bout.round === "de");
  const comp = competition.data;

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow="Competition"
        title={comp?.name ?? "Event"}
        description={`${comp?.weapon || "Open weapon"}${comp?.start_date ? ` · starts ${comp.start_date}` : ""} · ${entries.data?.items.length ?? 0} entries`}
      />
      {notice ? <p role="status" className="rounded-2xl border border-success/30 bg-success/10 px-4 py-3 text-sm">{notice}</p> : null}
      {failure ? <ErrorNote error={failure} /> : null}

      <div className="grid items-start gap-6 xl:grid-cols-2">
        <Card>
          <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold tracking-wide"><Swords size={15} className="text-primary" /> Entries</h2>
          <p className="mb-4 text-xs text-muted">Weapon must match the event. Withdrawal locks once the draw exists.</p>
          <form
            className="mb-4 grid gap-2 sm:grid-cols-[1fr_100px_auto]"
            onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              void act(
                () => api(`/competitions/${id}/entries`, { method: "POST", body: JSON.stringify({ athlete_id: String(form.get("athlete")), seed: Number(form.get("seed") || 0) }) }),
                "Entry added.",
              );
            }}
          >
            <select className={inputClass} name="athlete" required defaultValue="">
              <option value="" disabled>Choose an athlete</option>
              {(athletes.data?.items ?? []).map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}
            </select>
            <input className={inputClass} name="seed" type="number" min={0} placeholder="Seed" />
            <button className={secondaryButton} type="submit">Enter</button>
          </form>
          <ul className="divide-y divide-line">
            {(entries.data?.items ?? []).map((entry) => (
              <li key={entry.athlete_id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                <span className="font-medium">{entry.display_name} <span className="text-muted">· seed {entry.seed}</span></span>
                <button
                  type="button"
                  className="rounded-full px-3 py-1 text-xs text-muted hover:bg-surface hover:text-text"
                  onClick={() => void act(() => api(`/competitions/${id}/entries/${entry.athlete_id}`, { method: "DELETE" }), "Entry withdrawn.")}
                >
                  Withdraw
                </button>
              </li>
            ))}
          </ul>
          {(entries.data?.items ?? []).length === 0 ? <p className="py-4 text-center text-sm text-muted">No entries yet.</p> : null}
        </Card>

        <Card>
          <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold tracking-wide"><Flag size={15} className="text-primary" /> Poules</h2>
          <p className="mb-4 text-xs text-muted">Round-robin at 5 touches. Seeds snake across groups.</p>
          <form
            className="mb-4 flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const size = Number(new FormData(event.currentTarget).get("poule_size") || 6);
              void act(() => api(`/competitions/${id}/poules`, { method: "POST", body: JSON.stringify({ poule_size: size }) }), "Poule sheet drawn.");
            }}
          >
            <Field label="Group size"><input className={inputClass} name="poule_size" type="number" min={2} max={8} defaultValue={6} /></Field>
            <span className="self-end"><button className={buttonClass} type="submit">Draw poules</button></span>
          </form>
          {pouleBouts.length === 0 ? <p className="py-4 text-center text-sm text-muted">No poule bouts yet.</p> : (
            <ul className="grid max-h-72 gap-1 overflow-y-auto">
              {pouleBouts.map((bout) => (
                <BoutRow key={bout.id} bout={bout} names={names} referees={referees} onDone={() => refresh()} />
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card>
        <h2 className="mb-4 text-sm font-semibold tracking-wide">Standings <span className="ml-1 font-normal text-muted">· formula v{table.data?.formula_version ?? 1}</span></h2>
        {(table.data?.items ?? []).length === 0 ? <p className="text-sm text-muted">No entries yet.</p> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead>
                <tr className="text-left text-xs text-muted">
                  <th className="py-2 pr-4 font-medium">#</th>
                  <th className="py-2 pr-4 font-medium">Athlete</th>
                  <th className="py-2 pr-4 text-right font-medium">Bouts</th>
                  <th className="py-2 pr-4 text-right font-medium">V</th>
                  <th className="py-2 pr-4 text-right font-medium">Scored</th>
                  <th className="py-2 pr-4 text-right font-medium">Conceded</th>
                  <th className="py-2 text-right font-medium">Indicator</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {table.data?.items.map((row, index) => (
                  <tr key={row.athlete_id} className="border-t border-line">
                    <td className="py-2.5 pr-4 text-muted">{index + 1}</td>
                    <td className="py-2.5 pr-4 font-medium">{row.display_name}</td>
                    <td className="py-2.5 pr-4 text-right">{row.bouts}</td>
                    <td className="py-2.5 pr-4 text-right font-semibold">{row.victories}</td>
                    <td className="py-2.5 pr-4 text-right">{row.scored}</td>
                    <td className="py-2.5 pr-4 text-right">{row.conceded}</td>
                    <td className="py-2.5 text-right font-semibold">{row.indicator > 0 ? `+${row.indicator}` : row.indicator}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold tracking-wide"><Trophy size={15} className="text-primary" /> Direct elimination</h2>
        <p className="mb-4 text-xs text-muted">First round at 15 touches. Tied bouts never auto-advance — the referee sets the score.</p>
        <div className="mb-4 flex flex-wrap items-end gap-2">
          <form
            className="flex items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              const size = Number(new FormData(event.currentTarget).get("size") || 8);
              void act(() => api(`/competitions/${id}/de`, { method: "POST", body: JSON.stringify({ size, use_standings: true }) }), "DE draw created.");
            }}
          >
            <Field label="Table size">
              <select className={inputClass} name="size" defaultValue="8">
                <option value="2">2</option>
                <option value="4">4</option>
                <option value="8">8</option>
                <option value="16">16</option>
                <option value="32">32</option>
              </select>
            </Field>
            <button className={buttonClass} type="submit">Draw DE</button>
          </form>
          <button className={secondaryButton} type="button" onClick={() => void act(() => api(`/competitions/${id}/de/next`, { method: "POST" }), "Next round drawn.")}>
            <Play size={14} /> Advance winners
          </button>
        </div>
        {deBouts.length === 0 ? <p className="py-4 text-center text-sm text-muted">No DE bouts yet.</p> : (
          <ul className="grid gap-1">
            {deBouts.map((bout) => (
              <BoutRow key={bout.id} bout={bout} names={names} referees={referees} officials={officials} onDone={() => refresh()} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function BoutRow({
  bout,
  names,
  referees,
  officials,
  onDone,
}: {
  bout: CompetitionBout;
  names: Map<string, string>;
  referees: Map<string, string>;
  officials?: { user_id: string; display_name: string }[];
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const run = async (work: () => Promise<unknown>) => {
    setBusy(true);
    try {
      await work();
      onDone();
    } finally {
      setBusy(false);
    }
  };
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-surface px-4 py-3">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">
          {bout.left ? names.get(bout.left.athlete_id) ?? "Left" : <span className="text-muted">Bye</span>}
          <span className="mx-2 text-muted">vs</span>
          {bout.right ? names.get(bout.right.athlete_id) ?? "Right" : <span className="text-muted">Bye</span>}
        </p>
        <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
          <Badge tone={bout.status === "completed" ? "success" : bout.status === "in_progress" ? "warning" : "neutral"}>{bout.status}</Badge>
          {bout.bracket_label}
          {bout.referee_user_id ? <span className="flex items-center gap-1"><Whistle size={12} />{referees.get(bout.referee_user_id) ?? "Referee"}</span> : null}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <ScorePill left={bout.left?.score ?? 0} right={bout.right?.score ?? 0} />
        {bout.status !== "completed" && bout.left && bout.right ? (
          <button type="button" disabled={busy} className={secondaryButton} onClick={() => void run(() => api(`/bouts/${bout.id}/complete`, { method: "POST" }))}>
            Complete
          </button>
        ) : null}
        {officials && bout.left && bout.right ? (
          <select
            aria-label="Referee"
            className={inputClass}
            value={bout.referee_user_id ?? ""}
            disabled={busy}
            onChange={(event) => void run(() => api(`/bouts/${bout.id}/referee`, { method: "PATCH", body: JSON.stringify({ user_id: event.target.value || null }) }))}
          >
            <option value="">No referee</option>
            {officials.map((item) => <option key={item.user_id} value={item.user_id}>{item.display_name}</option>)}
          </select>
        ) : null}
      </div>
    </li>
  );
}
