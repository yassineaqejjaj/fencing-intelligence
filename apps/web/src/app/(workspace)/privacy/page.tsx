"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { buttonClass, Field, inputClass, secondaryButton } from "@/components/states";

export default function PrivacyPage() {
  const [exportText, setExportText] = useState("");
  const [message, setMessage] = useState("");
  return (
    <div className="grid max-w-2xl gap-4">
      <h1 className="text-2xl font-semibold">Privacy</h1>
      <p className="text-muted">Private videos are not used for training unless you record research consent. Export contains your account, memberships, consents, and annotations you created.</p>
      <button className={buttonClass} type="button" onClick={async () => {
        const data = await api<unknown>("/privacy/export");
        setExportText(JSON.stringify(data, null, 2));
      }}>Export my data</button>
      {exportText ? <pre className="overflow-auto rounded-lg bg-surface p-3 text-xs">{exportText}</pre> : null}
      <button className={secondaryButton} type="button" onClick={async () => {
        await api("/privacy/consent", { method: "POST", body: JSON.stringify({ granted: true, purpose: "research_training" }) });
        setMessage("Research consent recorded.");
      }}>Grant research consent</button>
      <form className="grid gap-3" onSubmit={async (event) => {
        event.preventDefault();
        const password = new FormData(event.currentTarget).get("password");
        await api("/privacy/delete-account", { method: "POST", body: JSON.stringify({ password, delete_uploaded_videos: true }) });
        setMessage("Account deleted.");
      }}>
        <Field label="Password to delete the account"><input className={inputClass} name="password" type="password" required /></Field>
        <button className="rounded-md bg-danger px-3 py-2" type="submit">Delete account and uploaded videos</button>
      </form>
      {message ? <p>{message}</p> : null}
    </div>
  );
}
