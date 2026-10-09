"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { buttonClass, Field, inputClass } from "@/components/states";
import { useI18n } from "@/lib/i18n";

export default function SettingsPage() {
  const { setLocale } = useI18n();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  return (
    <div className="grid max-w-lg gap-6">
      <h1 className="text-2xl font-semibold">Settings</h1>
      <form className="grid gap-3" onSubmit={async (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const locale = String(form.get("locale"));
        await api("/auth/me", { method: "PATCH", body: JSON.stringify({ display_name: form.get("display_name"), locale }) });
        if (locale === "en" || locale === "fr") setLocale(locale);
        setMessage("Profile saved");
      }}>
        <Field label="Display name"><input className={inputClass} name="display_name" required /></Field>
        <Field label="Language"><select className={inputClass} name="locale" defaultValue="en"><option value="en">English</option><option value="fr">Français</option></select></Field>
        <button className={buttonClass} type="submit">Save profile</button>
      </form>
      <form className="grid gap-3" method="post" action="/settings" onSubmit={async (event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        setError("");
        try {
          await api("/auth/change-password", { method: "POST", body: JSON.stringify({ current_password: form.get("current"), new_password: form.get("next") }) });
          setMessage("Password changed");
        } catch (caught) {
          setError(caught instanceof ApiError ? caught.message : "Could not change password");
        }
      }}>
        <Field label="Current password"><input className={inputClass} name="current" type="password" required /></Field>
        <Field label="New password"><input className={inputClass} name="next" type="password" minLength={10} required /></Field>
        <button className={buttonClass} type="submit">Change password</button>
      </form>
      {message ? <p className="text-sm text-success">{message}</p> : null}
      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
    </div>
  );
}
