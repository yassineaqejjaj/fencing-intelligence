"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError, api, type Athlete } from "@/lib/api";
import { buttonClass, ErrorNote, Field, inputClass } from "@/components/states";

export default function UploadPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const presetBout = useSearchParams().get("bout") ?? "";
  const athletes = useQuery({ queryKey: ["athletes"], queryFn: () => api<{ items: Athlete[] }>("/athletes") });
  const bouts = useQuery({ queryKey: ["bouts"], queryFn: () => api<{ items: { id: string; weapon: string; left: { athlete_id: string } | null }[] }>("/bouts") });

  return (
    <form
      className="mx-auto grid max-w-xl gap-4"
      onSubmit={async (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const file = form.get("file");
        if (!(file instanceof File) || file.size === 0) {
          setError("Choose a video file");
          return;
        }
        setPending(true);
        setError("");
        const body = new FormData();
        body.set("file", file);
        body.set("title", String(form.get("title")));
        body.set("weapon", String(form.get("weapon")));
        body.set("visibility", String(form.get("visibility")));
        const athlete = String(form.get("athlete_id") || "");
        const bout = String(form.get("bout_id") || "");
        if (athlete) body.set("athlete_id", athlete);
        if (bout) body.set("bout_id", bout);
        body.set("training_consent", form.get("training_consent") ? "true" : "false");
        try {
          const created = await api<{ video: { id: string }; visibility_forced_private: boolean }>("/videos/upload", { method: "POST", body });
          router.push(`/videos/${created.video.id}${created.visibility_forced_private ? "?forced-private=1" : ""}`);
        } catch (caught) {
          setError(caught instanceof ApiError ? caught.message : "Upload failed");
        } finally {
          setPending(false);
        }
      }}
    >
      <h1 className="text-2xl font-semibold">Upload video</h1>
      <Field label="Title"><input className={inputClass} name="title" required /></Field>
      <Field label="Weapon">
        <select className={inputClass} name="weapon" defaultValue="epee">
          <option value="epee">Épée</option>
          <option value="foil">Foil</option>
          <option value="sabre">Sabre</option>
        </select>
      </Field>
      <Field label="Athlete">
        <select className={inputClass} name="athlete_id" defaultValue="">
          <option value="">None</option>
          {athletes.data?.items.map((athlete) => <option key={athlete.id} value={athlete.id}>{athlete.display_name}</option>)}
        </select>
      </Field>
      <Field label="Bout">
        <select key={bouts.isSuccess ? "bouts-ready" : "bouts-loading"} className={inputClass} name="bout_id" defaultValue={presetBout}>
          <option value="">None</option>
          {presetBout && bouts.data && !bouts.data.items.some((bout) => bout.id === presetBout) ? (
            <option value={presetBout}>{presetBout.slice(0, 8)}</option>
          ) : null}
          {bouts.data?.items.map((bout) => <option key={bout.id} value={bout.id}>{bout.weapon} · {bout.id.slice(0, 8)}</option>)}
        </select>
      </Field>
      <Field label="Visibility">
        <select className={inputClass} name="visibility" defaultValue="private">
          <option value="private">Private</option>
          <option value="club">Club</option>
        </select>
      </Field>
      <Field label="Video file"><input className={inputClass} name="file" type="file" accept="video/mp4,video/quicktime,video/webm" required /></Field>
      <label className="flex items-center gap-2 text-sm text-muted">
        <input name="training_consent" type="checkbox" />
        Allow this video to be used for future research training
      </label>
      {error ? <ErrorNote error={new ApiError(400, "upload", error)} /> : null}
      <button className={buttonClass} disabled={pending} type="submit">{pending ? "Uploading…" : "Upload and process"}</button>
    </form>
  );
}
