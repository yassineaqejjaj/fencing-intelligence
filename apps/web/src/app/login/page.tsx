"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { buttonClass, Field, inputClass } from "@/components/states";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <main className="mx-auto grid min-h-screen max-w-5xl items-center gap-8 px-6 py-12 lg:grid-cols-[1.1fr_1fr]">
      <div className="fi-rise hidden lg:block">
        <span className="flex h-11 w-11 items-center justify-center rounded-lg bg-mask font-mono text-xs text-voyant">FI</span>
        <h1 className="mt-6 max-w-md text-5xl font-semibold tracking-tight text-balance">
          Read the bout like you were still on the piste.
        </h1>
        <p className="mt-4 max-w-md leading-relaxed text-muted">
          Slow the phrase, mark the action, validate the touch. Then the reading speaks in language a fencer can use — never a number invented by a model.
        </p>
        <div className="mt-8 rounded-3xl border border-line bg-surface p-5 text-sm">
          <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">Demo club</p>
          <p className="mt-2 text-muted">Invented fencers and bouts. Not a real season.</p>
          <p className="mt-1 font-mono text-[13px]">demo@example.com · DemoFence2026</p>
        </div>
      </div>
      <div className="fi-rise mx-auto w-full max-w-md rounded-3xl border border-line bg-gradient-to-b from-surface to-surface p-7 shadow-[var(--shadow-float)]">
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-muted lg:hidden">Demo: demo@example.com · DemoFence2026</p>
        <form
          className="mt-6 flex flex-col gap-4"
          method="post"
          action="/login"
          onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            setPending(true);
            setError("");
            try {
              await api("/auth/login", {
                method: "POST",
                body: JSON.stringify({ email: form.get("email"), password: form.get("password") }),
              });
              router.push("/dashboard");
            } catch (caught) {
              setError(caught instanceof ApiError ? caught.message : "Sign-in failed");
            } finally {
              setPending(false);
            }
          }}
        >
          <Field label="Email">
            <input className={inputClass} name="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </Field>
          <Field label="Password">
            <input className={inputClass} name="password" type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
          <button
            type="button"
            className="text-left text-sm font-semibold text-primary hover:brightness-125"
            onClick={() => {
              setEmail("demo@example.com");
              setPassword("DemoFence2026");
            }}
          >
            Use the demo club
          </button>
          {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
          <button className={buttonClass} disabled={pending} type="submit">
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="mt-5 text-sm text-muted">
          <Link href="/register" className="text-primary hover:brightness-125">Create an account</Link>
          {" · "}
          <Link href="/reset-password" className="text-primary hover:brightness-125">Reset password</Link>
        </p>
      </div>
    </main>
  );
}
