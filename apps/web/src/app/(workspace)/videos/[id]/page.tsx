"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { Pause, Play } from "lucide-react";
import { api, type Annotation, type Athlete, type BoutMomentum, type BoutReading, type Video } from "@/lib/api";

const RoiEditor = dynamic(() => import("@/components/roi-editor").then((mod) => mod.RoiEditor), { ssr: false });
import { AnalysisTools } from "@/components/analysis-tools";
import { BoutReadingView, BoutStory } from "@/components/intelligence-view";
import { buttonClass, Empty, ErrorNote, Field, inputClass, Loading, secondaryButton } from "@/components/states";
import { Badge, Card, PageHeader } from "@/components/ui";

const ACTIONS = ["attack", "riposte", "parry", "counter_attack", "lunge", "advance", "retreat", "fleche", "en_garde", "feint", "remise"];
const OUTCOMES = ["touch_for", "touch_against", "off_target", "no_touch", "halt", "simultaneous"];

export default function AnalysisPage() {
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const forcedPrivate = search.get("forced-private") === "1";
  const queryClient = useQueryClient();
  const videoRef = useRef<HTMLVideoElement>(null);
  const [rate, setRate] = useState(1);
  const [loopIn, setLoopIn] = useState<number | null>(null);
  const [loopOut, setLoopOut] = useState<number | null>(null);
  const [mode, setMode] = useState("simplified");
  const [paused, setPaused] = useState(true);
  const [draft, setDraft] = useState({ action: "attack", outcome: "no_touch", target: "weapon_arm", notes: "", actor: "" });
  const [history, setHistory] = useState<string[]>([]);
  const [future, setFuture] = useState<string[]>([]);

  const detail = useQuery({
    queryKey: ["video", params.id],
    queryFn: () => api<{ video: Video; job: { status: string; error: string } | null }>(`/videos/${params.id}`),
    refetchInterval: (query) => (query.state.data?.video.status === "ready" || query.state.data?.video.status === "failed" ? false : 2000),
  });
  const playback = useQuery({
    queryKey: ["playback", params.id, detail.data?.video.status],
    enabled: detail.data?.video.status === "ready",
    queryFn: () => api<{ url: string; thumbnail_url: string | null }>(`/videos/${params.id}/playback`),
  });
  const annotations = useQuery({
    queryKey: ["annotations", params.id],
    queryFn: () => api<{ items: Annotation[] }>(`/videos/${params.id}/annotations`),
  });
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const bout = useQuery({
    queryKey: ["bout", detail.data?.video.bout_id],
    enabled: Boolean(detail.data?.video.bout_id),
    queryFn: () => api<{ id: string; left: { athlete_id: string; score: number } | null; right: { athlete_id: string; score: number } | null }>(`/bouts/${detail.data?.video.bout_id}`),
  });
  const momentum = useQuery({
    queryKey: ["momentum", detail.data?.video.bout_id],
    enabled: Boolean(detail.data?.video.bout_id),
    queryFn: () => api<BoutMomentum>(`/bouts/${detail.data?.video.bout_id}/momentum`),
  });
  const reading = useQuery({
    queryKey: ["bout-reading", detail.data?.video.bout_id],
    enabled: Boolean(detail.data?.video.bout_id),
    queryFn: () => api<BoutReading>(`/bouts/${detail.data?.video.bout_id}/reading`),
  });
  const names = new Map((athletes.data?.items ?? []).map((athlete) => [athlete.id, athlete.display_name]));

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    video.playbackRate = rate;
    const onTime = () => {
      if (loopIn !== null && loopOut !== null && video.currentTime * 1000 >= loopOut) {
        video.currentTime = loopIn / 1000;
      }
    };
    video.addEventListener("timeupdate", onTime);
    return () => video.removeEventListener("timeupdate", onTime);
  }, [rate, loopIn, loopOut, playback.data?.url]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.tagName === "SELECT") return;
      const video = videoRef.current;
      if (!video) return;
      const fps = detail.data?.video.fps || 30;
      if (event.code === "Space") {
        event.preventDefault();
        if (video.paused) void video.play();
        else video.pause();
      }
      if (event.code === "ArrowRight") video.currentTime += 1 / fps;
      if (event.code === "ArrowLeft") video.currentTime = Math.max(0, video.currentTime - 1 / fps);
      if (event.key === "[") setLoopIn(Math.round(video.currentTime * 1000));
      if (event.key === "]") setLoopOut(Math.round(video.currentTime * 1000));
      if ((event.metaKey || event.ctrlKey) && event.key === "z") {
        event.preventDefault();
        setHistory((past) => {
          const previous = past[past.length - 1];
          if (!previous) return past;
          setFuture((items) => [draft.notes, ...items]);
          setDraft((current) => ({ ...current, notes: previous }));
          return past.slice(0, -1);
        });
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [detail.data?.video.fps, draft.notes]);

  const save = useMutation({
    mutationFn: async () => {
      const video = videoRef.current;
      const start = Math.round((video?.currentTime || 0) * 1000);
      return api<Annotation>(`/videos/${params.id}/annotations`, {
        method: "POST",
        body: JSON.stringify({
          mode,
          action_type_code: draft.action,
          start_ms: start,
          end_ms: start + 400,
          actor_athlete_id: draft.actor || null,
          outcome: draft.outcome,
          target_area: draft.target,
          notes: draft.notes,
          status: "validated",
          body: { mode },
        }),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["annotations", params.id] });
      const boutId = detail.data?.video.bout_id;
      if (boutId) await queryClient.invalidateQueries({ queryKey: ["bout-reading", boutId] });
    },
  });

  if (detail.isError) return <ErrorNote error={detail.error} />;
  if (detail.isLoading || !detail.data) return <Loading />;
  const video = detail.data.video;

  return (
    <div className="grid gap-6">
      <PageHeader
        eyebrow={video.weapon}
        title={video.title}
        description={video.status === "ready" ? "Space plays. Arrows step a frame. [ and ] loop the phrase." : "Processing the video. This page refreshes until playback is ready."}
        actions={<Badge tone={video.status === "ready" ? "success" : video.status === "failed" ? "danger" : "warning"}>{video.status}</Badge>}
      />
      {forcedPrivate ? (
        <p role="status" className="rounded-lg border border-warning/40 bg-warning/10 p-3 text-sm">
          Visibility was forced to private: the linked athlete is a minor without guardian consent.
        </p>
      ) : null}

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="grid gap-4">
          <Card className="overflow-hidden !p-0">
            {video.status === "failed" ? <p role="alert" className="p-5 text-sm text-danger">{video.error || "Processing failed"}</p> : null}
            {video.status === "ready" && video.width && video.height ? (
              <div className="border-b border-white/10 p-4">
                <RoiEditor videoId={video.id} width={video.width} height={video.height} posterUrl={playback.data?.thumbnail_url ?? null} />
              </div>
            ) : null}
            {playback.data?.url ? (
              <video
                ref={videoRef}
                className="aspect-video w-full bg-black"
                src={playback.data.url}
                controls
                poster={playback.data.thumbnail_url || undefined}
                onPlay={() => setPaused(false)}
                onPause={() => setPaused(true)}
              />
            ) : video.status === "ready" ? (
              <p className="p-5 text-sm text-muted">
                {video.has_playback
                  ? "Playback link is being prepared…"
                  : "This sheet has validated marks and no video file yet. Upload the bout video to attach the picture. The reading still uses only what a person validated."}
              </p>
            ) : null}
            <div className="flex flex-wrap items-center gap-2 border-t border-white/10 p-4">
              <button
                type="button"
                className={secondaryButton}
                aria-label={paused ? "Play" : "Pause"}
                onClick={() => {
                  const el = videoRef.current;
                  if (!el) return;
                  if (el.paused) void el.play();
                  else el.pause();
                }}
              >
                {paused ? <Play size={15} /> : <Pause size={15} />}
              </button>
              <div className="flex rounded-full border border-white/10 bg-black/30 p-1" role="group" aria-label="Playback speed">
                {[0.25, 0.5, 1, 1.5, 2].map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setRate(value)}
                    aria-pressed={rate === value}
                    className={`rounded-full px-3 py-1 text-xs font-semibold tabular-nums transition-all ${rate === value ? "bg-primary text-[#04121a]" : "text-muted hover:text-text"}`}
                  >
                    {value}×
                  </button>
                ))}
              </div>
              <button type="button" className={secondaryButton} onClick={() => videoRef.current && setLoopIn(Math.round(videoRef.current.currentTime * 1000))}>Loop in{loopIn !== null ? ` · ${(loopIn / 1000).toFixed(1)}s` : ""}</button>
              <button type="button" className={secondaryButton} onClick={() => videoRef.current && setLoopOut(Math.round(videoRef.current.currentTime * 1000))}>Loop out{loopOut !== null ? ` · ${(loopOut / 1000).toFixed(1)}s` : ""}</button>
            </div>
            <div className="px-4 pb-4">
              <div className="relative h-12 overflow-hidden rounded-2xl border border-white/10 bg-black/40">
                <div className="absolute inset-x-3 top-1/2 h-1 -translate-y-1/2 rounded-full bg-white/10" />
                {(annotations.data?.items || []).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    title={`${item.action_type_code} · ${item.status}`}
                    aria-label={`${item.action_type_code} at ${item.start_ms} milliseconds`}
                    className={`absolute top-1/2 h-5 w-2.5 -translate-y-1/2 rounded-full transition-transform hover:scale-125 ${item.status === "validated" ? "bg-primary shadow-[0_0_12px_rgb(0_212_255/0.8)]" : "bg-warning"}`}
                    style={{ left: `calc(${(video.duration_seconds ? (item.start_ms / (video.duration_seconds * 1000)) * 100 : 0).toFixed(2)}% )` }}
                    onClick={() => {
                      if (videoRef.current) videoRef.current.currentTime = item.start_ms / 1000;
                    }}
                  />
                ))}
              </div>
              <p className="mt-2 text-xs text-muted">{(annotations.data?.items || []).length} marks · cyan is validated, amber is draft</p>
            </div>
          </Card>

          <AnalysisTools
            videoId={video.id}
            getTimeMs={() => Math.round((videoRef.current?.currentTime || 0) * 1000)}
            seek={(ms) => {
              if (videoRef.current) videoRef.current.currentTime = ms / 1000;
            }}
          />

          {bout.data ? (
            <Card>
              <div className="flex items-center justify-between gap-3">
                <div className="text-center">
                  <p className="text-xs text-muted">Left</p>
                  <p className="mt-1 max-w-32 truncate text-sm font-medium">{names.get(bout.data.left?.athlete_id ?? "") ?? "—"}</p>
                  <p className="mt-1 text-4xl font-semibold tabular-nums">{bout.data.left?.score ?? 0}</p>
                </div>
                <p className="text-xs font-semibold tracking-[0.2em] text-muted">SCORE</p>
                <div className="text-center">
                  <p className="text-xs text-muted">Right</p>
                  <p className="mt-1 max-w-32 truncate text-sm font-medium">{names.get(bout.data.right?.athlete_id ?? "") ?? "—"}</p>
                  <p className="mt-1 text-4xl font-semibold tabular-nums">{bout.data.right?.score ?? 0}</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <button
                  type="button"
                  className={secondaryButton}
                  onClick={async () => {
                    if (!bout.data?.left || !bout.data.right || !video.bout_id) return;
                    const time = Math.round((videoRef.current?.currentTime || 0) * 1000);
                    await api(`/bouts/${video.bout_id}/touches`, {
                      method: "POST",
                      body: JSON.stringify({
                        scorer_athlete_id: bout.data.left.athlete_id,
                        receiver_athlete_id: bout.data.right.athlete_id,
                        timestamp_ms: time,
                        target_area: draft.target,
                        video_id: video.id,
                      }),
                    });
                    await queryClient.invalidateQueries({ queryKey: ["bout", video.bout_id] });
                    await queryClient.invalidateQueries({ queryKey: ["momentum", video.bout_id] });
                    await queryClient.invalidateQueries({ queryKey: ["bout-reading", video.bout_id] });
                  }}
                >
                  Touch left
                </button>
                <button
                  type="button"
                  className={secondaryButton}
                  onClick={async () => {
                    if (!bout.data?.left || !bout.data.right || !video.bout_id) return;
                    const time = Math.round((videoRef.current?.currentTime || 0) * 1000);
                    await api(`/bouts/${video.bout_id}/touches`, {
                      method: "POST",
                      body: JSON.stringify({
                        scorer_athlete_id: bout.data.right.athlete_id,
                        receiver_athlete_id: bout.data.left.athlete_id,
                        timestamp_ms: time,
                        target_area: draft.target,
                        video_id: video.id,
                      }),
                    });
                    await queryClient.invalidateQueries({ queryKey: ["bout", video.bout_id] });
                    await queryClient.invalidateQueries({ queryKey: ["momentum", video.bout_id] });
                    await queryClient.invalidateQueries({ queryKey: ["bout-reading", video.bout_id] });
                  }}
                >
                  Touch right
                </button>
              </div>
            </Card>
          ) : (
            <Empty>Link this video to a bout to record the score.</Empty>
          )}
          {reading.data ? <BoutReadingView data={reading.data} /> : null}
          {momentum.data ? <BoutStory data={momentum.data} /> : null}
        </div>

        <form
          className="grid content-start gap-4 rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-5 xl:sticky xl:top-20"
          onSubmit={(event) => {
            event.preventDefault();
            save.mutate();
          }}
        >
          <h2 className="text-sm font-semibold tracking-wide">Annotation</h2>
          <div className="flex rounded-full border border-white/10 bg-black/30 p-1" role="group" aria-label="Annotation mode">
            {["simplified", "tactical", "technical"].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setMode(item)}
                aria-pressed={mode === item}
                className={`flex-1 rounded-full px-3 py-1.5 text-xs font-semibold capitalize transition-all ${mode === item ? "bg-primary text-[#04121a]" : "text-muted hover:text-text"}`}
              >
                {item}
              </button>
            ))}
          </div>
          <Field label="Actor">
            <select className={inputClass} value={draft.actor} onChange={(event) => setDraft({ ...draft, actor: event.target.value })}>
              <option value="">Unassigned</option>
              {athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Action">
              <select className={inputClass} value={draft.action} onChange={(event) => setDraft({ ...draft, action: event.target.value })}>
                {ACTIONS.map((code) => <option key={code} value={code}>{code}</option>)}
              </select>
            </Field>
            <Field label="Outcome">
              <select className={inputClass} value={draft.outcome} onChange={(event) => setDraft({ ...draft, outcome: event.target.value })}>
                {OUTCOMES.map((code) => <option key={code} value={code}>{code}</option>)}
              </select>
            </Field>
          </div>
          <Field label="Target">
            <input className={inputClass} value={draft.target} onChange={(event) => setDraft({ ...draft, target: event.target.value })} />
          </Field>
          <Field label="Notes">
            <textarea
              className={`${inputClass} min-h-20`}
              value={draft.notes}
              onChange={(event) => {
                setHistory((past) => [...past.slice(-20), draft.notes]);
                setFuture([]);
                setDraft({ ...draft, notes: event.target.value });
              }}
            />
          </Field>
          {save.isError ? <ErrorNote error={save.error} /> : null}
          <button className={buttonClass} type="submit">Save validated annotation</button>
          <button
            type="button"
            className={secondaryButton}
            disabled={future.length === 0}
            onClick={() => {
              const next = future[0];
              if (next === undefined) return;
              setFuture((items) => items.slice(1));
              setHistory((past) => [...past, draft.notes]);
              setDraft((current) => ({ ...current, notes: next }));
            }}
          >
            Redo note
          </button>
          <ul className="grid gap-2 text-sm">
            {(annotations.data?.items || []).map((item) => (
              <li key={item.id} className="flex items-center justify-between gap-2 rounded-2xl border border-white/[0.07] bg-black/30 px-3 py-2">
                <span className="truncate">{item.action_type_code} · {item.outcome || "no outcome"}{item.source !== "human" ? " · suggestion" : ""}</span>
                <Badge tone={item.status === "validated" ? "success" : "warning"}>{item.status}</Badge>
              </li>
            ))}
          </ul>
        </form>
      </div>
    </div>
  );
}

function ScoreSide({ label, score }: { label: string; score: number }) {
  return (
    <div>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-3xl">{score}</p>
    </div>
  );
}
