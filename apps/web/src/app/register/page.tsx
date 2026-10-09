"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { buttonClass, Field, inputClass } from "@/components/states";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");

  return (
    <main className="mx-auto grid min-h-screen max-w-5xl items-center gap-8 px-6 py-12 lg:grid-cols-[1.1fr_1fr]">
      <div className="fi-rise hidden lg:block">
        <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-mask font-mono text-xs text-voyant">FI</span>
        <h1 className="mt-6 max-w-md text-5xl font-semibold tracking-tight text-balance">Start your own salle.</h1>
        <p className="mt-4 max-w-md leading-relaxed text-muted">
          An account creates your organization. Private video stays inside it — playback is signed, access is audited.
        </p>
      </div>
      <div className="fi-rise mx-auto w-full max-w-md rounded-3xl border border-line bg-gradient-to-b from-surface to-surface p-7 shadow-[var(--shadow-float)]">
        <h1 className="text-3xl font-semibold tracking-tight">Create an account</h1>
        <form
          className="mt-6 flex flex-col gap-4"
          method="post"
          action="/register"
          onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            setError("");
            try {
              await api("/auth/register", {
                method: "POST",
                body: JSON.stringify({
                  email: form.get("email"),
                  password: form.get("password"),
                  display_name: form.get("display_name"),
                  organization_name: form.get("organization_name"),
                  locale: form.get("locale"),
                }),
              });
              router.push("/dashboard");
            } catch (caught) {
              setError(caught instanceof ApiError ? caught.message : "Registration failed");
            }
          }}
        >
          <Field label="Name"><input className={inputClass} name="display_name" required /></Field>
          <Field label="Email"><input className={inputClass} name="email" type="email" required /></Field>
          <Field label="Password"><input className={inputClass} name="password" type="password" minLength={10} required /></Field>
          <Field label="Organization"><input className={inputClass} name="organization_name" required /></Field>
          <Field label="Language">
            <select className={inputClass} name="locale" defaultValue="en">
              <option value="en">English</option>
              <option value="fr">Français</option>
            </select>
          </Field>
          {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
          <button className={buttonClass} type="submit">Create account</button>
        </form>
        <p className="mt-5 text-sm text-muted"><Link href="/login" className="text-primary">Already registered</Link></p>
      </div>
    </main>
  );
}
