"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Annotation } from "@/lib/api";
import { buttonClass, Empty, ErrorNote, Field, inputClass, secondaryButton } from "./states";

export function AnalysisTools({
  videoId,
  getTimeMs,
  seek,
}: {
  videoId: string;
  getTimeMs: () => number;
  seek: (ms: number) => void;
}) {
  const queryClient = useQueryClient();
  const [phraseStart, setPhraseStart] = useState<number | null>(null);
  const [selected, setSelected] = useState("");
  const [reading, setReading] = useState<ExperimentalReading | null>(null);
  const [error, setError] = useState<unknown>(null);
  const phrases = useQuery({
    queryKey: ["phrases", videoId],
    queryFn: () => api<{ items: { id: string; start_ms: number; end_ms: number; validated: boolean; notes: string }[] }>(`/videos/${videoId}/phrases`),
  });
  const annotations = useQuery({
    queryKey: ["annotations", videoId],
    queryFn: () => api<{ items: Annotation[] }>(`/videos/${videoId}/annotations`),
  });
  const versions = useQuery({
    queryKey: ["versions", selected],
    enabled: Boolean(selected),
    queryFn: () => api<{ items: { version: number; snapshot: { action_type_code?: string; status?: string; notes?: string } }[] }>(`/annotations/${selected}/versions`),
  });

  async function run(kind: string) {
    setError(null);
    setReading(null);
    try {
      const result = await api<{ summary: Record<string, unknown> }>(`/videos/${videoId}/analyses`, {
        method: "POST",
        body: JSON.stringify({ kind }),
      });
      setReading(describeExperimental(kind, result.summary));
      await queryClient.invalidateQueries({ queryKey: ["annotations", videoId] });
    } catch (caught) {
      setError(caught);
    }
  }

  return (
    <div className="grid gap-4">
      <section className="grid gap-2 rounded-lg bg-surface p-3">
        <h2 className="text-sm font-medium">Phrase</h2>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={secondaryButton} onClick={() => setPhraseStart(getTimeMs())}>Mark start</button>
          <button
            type="button"
            className={buttonClass}
            onClick={async () => {
              const end = getTimeMs();
              if (phraseStart === null || end <= phraseStart) {
                setError(new Error("Mark a start, then a later end."));
                return;
              }
              setError(null);
              await api(`/videos/${videoId}/phrases`, {
                method: "POST",
                body: JSON.stringify({ start_ms: phraseStart, end_ms: end, validated: true, notes: "" }),
              });
              setPhraseStart(null);
              await queryClient.invalidateQueries({ queryKey: ["phrases", videoId] });
            }}
          >
            Mark end and save
          </button>
        </div>
        {phraseStart !== null ? <p className="text-xs text-muted">Start at {phraseStart} ms</p> : null}
        {phrases.data?.items.length ? (
          <ul className="grid gap-1 text-sm">
            {phrases.data.items.map((phrase) => (
              <li key={phrase.id}>
                <button type="button" className="text-primary" onClick={() => seek(phrase.start_ms)}>
                  {phrase.start_ms}–{phrase.end_ms} ms {phrase.validated ? "· validated" : ""}
                </button>
              </li>
            ))}
          </ul>
        ) : <Empty>No phrase marked on this video.</Empty>}
      </section>

      <section className="grid gap-2 rounded-lg bg-surface p-3">
        <h2 className="text-sm font-medium">Annotation history</h2>
        <Field label="Annotation">
          <select className={inputClass} value={selected} onChange={(event) => setSelected(event.target.value)}>
            <option value="">Choose one</option>
            {annotations.data?.items.map((item) => (
              <option key={item.id} value={item.id}>{item.action_type_code} · {item.status}</option>
            ))}
          </select>
        </Field>
        {versions.isError ? <ErrorNote error={versions.error} /> : null}
        {versions.data?.items.length ? (
          <ul className="grid gap-1 text-sm">
            {versions.data.items.map((item) => (
              <li key={item.version}>v{item.version} · {item.snapshot.action_type_code} · {item.snapshot.status}</li>
            ))}
          </ul>
        ) : null}
      </section>

      <Calibration videoId={videoId} />

      <section className="grid gap-2 rounded-lg bg-surface p-3">
        <h2 className="text-sm font-medium">On-video checks</h2>
        <p className="text-xs text-muted">
          These are machine hints on the clip. They never score a touch and they never replace a referee. A person still validates the bout.
        </p>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={secondaryButton} onClick={() => run("pose")}>Estimate pose</button>
          <button type="button" className={secondaryButton} onClick={() => run("scoreboard")}>Check scoreboard lights</button>
        </div>
        {reading ? (
          <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
            <p className="text-sm font-semibold">{reading.title}</p>
            <ul className="mt-2 grid gap-1.5 text-sm leading-relaxed text-muted">
              {reading.lines.map((line) => <li key={line}>{line}</li>)}
            </ul>
          </div>
        ) : null}
        {error ? <ErrorNote error={error} /> : null}
      </section>
    </div>
  );
}

type ExperimentalReading = { title: string; lines: string[] };

function describeExperimental(kind: string, summary: Record<string, unknown>): ExperimentalReading {
  if (kind === "pose") {
    const frames = Number(summary.frames_sampled ?? 0);
    const poses = Number(summary.poses_found ?? 0);
    return {
      title: "Pose on this clip",
      lines: [
        frames
          ? `Looked at ${frames} frames and found ${poses} body pose${poses === 1 ? "" : "s"}.`
          : "No frames could be sampled on this clip.",
        "These are joint positions only. They do not name an attack, a parry, or a priority.",
        "Nothing here changes the bout score until a person validates it.",
      ],
    };
  }
  if (kind === "scoreboard") {
    const candidates = Number(summary.candidates ?? 0);
    return {
      title: "Scoreboard lights",
      lines: [
        candidates === 0
          ? "No light candidates in the selected region."
          : `${candidates} light candidate${candidates === 1 ? "" : "s"} marked as unvalidated score events.`,
        "Lights are candidates, not referee decisions. They do not change the bout score.",
        "Open the timeline and validate each event before it counts.",
      ],
    };
  }
  const drafts = Number(summary.draft_annotations ?? 0);
  return {
    title: "Movement check",
    lines: [
      drafts
        ? `${drafts} draft mark${drafts === 1 ? "" : "s"} added for review.`
        : "No movement drafts were added.",
      "Drafts stay drafts until a person validates them.",
    ],
  };
}

function Calibration({ videoId }: { videoId: string }) {
  const [length, setLength] = useState("14");
  const [ax, setAx] = useState("0.1");
  const [bx, setBx] = useState("0.9");
  const [result, setResult] = useState("");
  const [error, setError] = useState<unknown>(null);
  return (
    <section className="grid gap-2 rounded-lg bg-surface p-3">
      <h2 className="text-sm font-medium">Distance calibration</h2>
      <p className="text-xs text-muted">Without two piste-end points, distance stays in pixels.</p>
      <div className="grid grid-cols-3 gap-2">
        <Field label="Piste meters"><input className={inputClass} value={length} onChange={(event) => setLength(event.target.value)} /></Field>
        <Field label="Left end x"><input className={inputClass} value={ax} onChange={(event) => setAx(event.target.value)} /></Field>
        <Field label="Right end x"><input className={inputClass} value={bx} onChange={(event) => setBx(event.target.value)} /></Field>
      </div>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className={buttonClass}
          onClick={async () => {
            setError(null);
            try {
              await api(`/videos/${videoId}/calibration`, {
                method: "PUT",
                body: JSON.stringify({
                  piste_length_m: Number(length),
                  point_a: { x: Number(ax), y: 0.5 },
                  point_b: { x: Number(bx), y: 0.5 },
                }),
              });
              setResult("Calibration saved");
            } catch (caught) {
              setError(caught);
            }
          }}
        >
          Save calibration
        </button>
        <button
          type="button"
          className={secondaryButton}
          onClick={async () => {
            setError(null);
            try {
              const distance = await api<{ unit: string; value: number; reason: string | null }>(`/videos/${videoId}/distance`, {
                method: "POST",
                body: JSON.stringify({ point_a: { x: 0.2, y: 0.5 }, point_b: { x: 0.45, y: 0.5 } }),
              });
              setResult(`${distance.value.toFixed(2)} ${distance.unit}${distance.reason ? ` (${distance.reason})` : ""}`);
            } catch (caught) {
              setError(caught);
            }
          }}
        >
          Measure a sample gap
        </button>
      </div>
      {result ? <p className="text-sm">{result}</p> : null}
      {error ? <ErrorNote error={error} /> : null}
    </section>
  );
}
