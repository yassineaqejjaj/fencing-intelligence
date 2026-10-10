"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, type Athlete, type FieProfile, type FieSearchHit } from "@/lib/api";
import { buttonClass, ErrorNote, Field, inputClass, secondaryButton } from "@/components/states";
import { Card } from "@/components/ui";

function seasonLabel(season: number | null) {
  if (!season) return "—";
  return `${season - 1}/${season}`;
}

export function FieRecord({ athlete }: { athlete: Athlete }) {
  const profile = athlete.fie_profile;
  return (
    <Card>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] tracking-[0.14em] text-muted uppercase">FIE</p>
          <h2 className="mt-1 text-sm font-semibold tracking-wide">Public record</h2>
        </div>
        {profile ? (
          <a className="font-mono text-xs underline" href={profile.source_url} target="_blank" rel="noreferrer">
            fie.org/{profile.fie_id}
          </a>
        ) : null}
      </div>
      {profile ? <ProfileBody profile={profile} /> : <p className="mb-4 text-sm text-muted">No FIE profile is linked yet. Paste the athlete page or an id.</p>}
      <LinkForm athleteId={athlete.id} linked={Boolean(profile)} />
    </Card>
  );
}

function ProfileBody({ profile }: { profile: FieProfile }) {
  const counts = [
    ["Olympic", profile.medal_counts.olympic],
    ["Olympic team", profile.medal_counts.olympic_team],
    ["Worlds", profile.medal_counts.worlds],
    ["Worlds team", profile.medal_counts.worlds_team],
  ] as const;
  return (
    <div className="mb-6 grid gap-6">
      <p className="text-sm text-muted">{profile.note}</p>
      <div className="grid gap-4 sm:grid-cols-4">
        <Stat label="Rank" value={profile.rank == null ? "—" : `#${profile.rank}`} />
        <Stat label="Points" value={profile.points ?? "—"} />
        <Stat label="Season" value={seasonLabel(profile.season)} />
        <Stat label="Head to head" value={`${profile.record.wins}–${profile.record.losses}`} />
      </div>
      <dl className="grid gap-2 text-sm sm:grid-cols-2">
        <Fact label="Nation" value={[profile.country, profile.country_code].filter(Boolean).join(" · ")} />
        <Fact label="Hand" value={profile.hand || "—"} />
        <Fact label="Born" value={profile.birth_date || "—"} />
        <Fact label="Height" value={profile.height_cm ? `${profile.height_cm} cm` : "—"} />
        <Fact label="License" value={profile.license_number ? `${profile.license_number} · ${profile.license_status || "status unknown"}` : "—"} />
        <Fact label="Bouts on the public list" value={String(profile.record.bouts)} />
      </dl>
      {profile.ranking.length ? (
        <div>
          <h3 className="mb-2 font-mono text-[11px] tracking-[0.14em] text-muted uppercase">Ranking by season</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="font-mono text-[10px] tracking-wide text-muted uppercase">
                <tr>
                  <th className="py-1 pr-3 font-medium">Season</th>
                  <th className="py-1 pr-3 font-medium">Weapon</th>
                  <th className="py-1 pr-3 font-medium">Category</th>
                  <th className="py-1 pr-3 font-medium">Rank</th>
                  <th className="py-1 font-medium">Points</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {profile.ranking.map((row) => (
                  <tr key={`${row.season}-${row.weapon}-${row.category}`} className="border-t border-line">
                    <td className="py-1.5 pr-3">{seasonLabel(row.season)}</td>
                    <td className="py-1.5 pr-3">{row.weapon || "—"}</td>
                    <td className="py-1.5 pr-3">{row.category}</td>
                    <td className="py-1.5 pr-3">{row.rank ?? "—"}</td>
                    <td className="py-1.5">{row.points ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      <div>
        <h3 className="mb-2 font-mono text-[11px] tracking-[0.14em] text-muted uppercase">Medal counts</h3>
        <ul className="grid gap-2 sm:grid-cols-2">
          {counts.map(([label, count]) => (
            <li key={label} className="flex items-baseline justify-between border-t border-line py-1.5 text-sm">
              <span>{label}</span>
              <span className="font-mono">{count.gold} gold · {count.silver} silver · {count.bronze} bronze</span>
            </li>
          ))}
        </ul>
        {profile.medals.length ? (
          <ul className="mt-3 grid gap-1 text-sm">
            {profile.medals.map((medal) => (
              <li key={`${medal.date}-${medal.name}`}>
                <span className="font-mono uppercase">{medal.medal}</span>
                {" · "}
                {medal.name}
                {medal.location ? ` · ${medal.location}` : ""}
                {medal.date ? ` · ${medal.date}` : ""}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      {profile.bouts.length ? (
        <div>
          <h3 className="mb-2 font-mono text-[11px] tracking-[0.14em] text-muted uppercase">Bouts</h3>
          <div className="max-h-80 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="font-mono text-[10px] tracking-wide text-muted uppercase">
                <tr>
                  <th className="py-1 pr-3 font-medium">Date</th>
                  <th className="py-1 pr-3 font-medium">Competition</th>
                  <th className="py-1 pr-3 font-medium">Opponent</th>
                  <th className="py-1 font-medium">Score</th>
                </tr>
              </thead>
              <tbody>
                {profile.bouts.map((bout, index) => (
                  <tr key={`${bout.date}-${bout.opponent}-${index}`} className="border-t border-line">
                    <td className="py-1.5 pr-3 font-mono">{bout.date || "—"}</td>
                    <td className="py-1.5 pr-3">{bout.competition || "—"}</td>
                    <td className="py-1.5 pr-3">{bout.opponent}{bout.opponent_country ? ` · ${bout.opponent_country}` : ""}</td>
                    <td className="py-1.5 font-mono">{bout.for_score ?? "—"}:{bout.against_score ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
      {profile.upcoming.length ? (
        <div>
          <h3 className="mb-2 font-mono text-[11px] tracking-[0.14em] text-muted uppercase">Upcoming on the FIE calendar</h3>
          <ul className="grid gap-1 text-sm">
            {profile.upcoming.map((event) => (
              <li key={`${event.start_date}-${event.name}`}>
                {event.name}
                {event.city ? ` · ${event.city}` : ""}
                {event.start_date ? ` · ${event.start_date}` : ""}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] tracking-[0.14em] text-muted uppercase">{label}</p>
      <p className="mt-1 font-mono text-2xl">{value}</p>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-t border-line py-1.5">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-mono">{value}</dd>
    </div>
  );
}

function LinkForm({ athleteId, linked }: { athleteId: string; linked: boolean }) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<unknown>(null);
  const link = useMutation({
    mutationFn: (profile_url: string) =>
      api<Athlete>(`/federation/fie/athletes/${athleteId}`, { method: "POST", body: JSON.stringify({ profile_url }) }),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["athlete", athleteId] });
      queryClient.invalidateQueries({ queryKey: ["athletes"] });
    },
    onError: setError,
  });
  return (
    <form
      className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        link.mutate(String(form.get("profile_url") || ""));
      }}
    >
      <Field label={linked ? "Replace the FIE link" : "FIE athlete page"}>
        <input className={inputClass} name="profile_url" placeholder="https://fie.org/athletes/30384" required />
      </Field>
      <button className={linked ? secondaryButton : buttonClass} type="submit" disabled={link.isPending}>
        {link.isPending ? "Reading FIE…" : linked ? "Refresh" : "Link profile"}
      </button>
      {error ? <div className="md:col-span-2"><ErrorNote error={error} /></div> : null}
    </form>
  );
}

export function FieSearch() {
  const queryClient = useQueryClient();
  const [hits, setHits] = useState<FieSearchHit[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const search = useMutation({
    mutationFn: (q: string) => api<{ items: FieSearchHit[] }>(`/federation/fie/search?q=${encodeURIComponent(q)}`),
    onSuccess: (body) => {
      setError(null);
      setHits(body.items);
    },
    onError: setError,
  });
  const add = useMutation({
    mutationFn: (fie_id: number) => api<Athlete>("/federation/fie/athletes", { method: "POST", body: JSON.stringify({ fie_id }) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["athletes"] }),
    onError: setError,
  });
  return (
    <Card>
      <h2 className="mb-1 text-sm font-semibold tracking-wide">Find a fencer on FIE</h2>
      <p className="mb-4 text-sm text-muted">Search the public list, then add one profile to this salle. Rank, license, and bout results come from that page.</p>
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          search.mutate(String(form.get("q") || ""));
        }}
      >
        <Field label="Name">
          <input className={inputClass} name="q" placeholder="El Falji" required minLength={2} />
        </Field>
        <button className={secondaryButton} type="submit" disabled={search.isPending}>{search.isPending ? "Searching…" : "Search"}</button>
      </form>
      {error ? <div className="mt-3"><ErrorNote error={error} /></div> : null}
      {hits ? (
        hits.length ? (
          <ul className="mt-4 divide-y divide-line">
            {hits.map((hit) => (
              <li key={hit.fie_id} className="flex flex-wrap items-center justify-between gap-3 py-3 text-sm">
                <span>
                  <span className="font-medium">{hit.name}</span>
                  <span className="mt-1 block font-mono text-xs text-muted">
                    {hit.country || "—"}
                    {hit.weapon ? ` · ${hit.weapon}` : ""}
                    {hit.rank != null ? ` · #${hit.rank}` : ""}
                    {hit.age != null ? ` · ${hit.age}` : ""}
                  </span>
                </span>
                <button className={buttonClass} type="button" disabled={add.isPending} onClick={() => add.mutate(hit.fie_id)}>
                  Add to the salle
                </button>
              </li>
            ))}
          </ul>
        ) : <p className="mt-4 text-sm text-muted">No public profile matches that name.</p>
      ) : null}
    </Card>
  );
}
