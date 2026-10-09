"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Zap } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { buttonClass, Field, inputClass } from "@/components/states";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  // Demo credentials exist only in local development seeds. Never advertise
  // them on production builds (next start sets NODE_ENV=production).
  const showDemoHint = process.env.NODE_ENV !== "production";

  return (
    <main className="mx-auto grid min-h-screen max-w-5xl items-center gap-8 px-6 py-12 lg:grid-cols-[1.1fr_1fr]">
      <div className="fi-rise hidden lg:block">
        <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-[#04121a]">
          <Zap size={20} strokeWidth={2.5} />
        </span>
        <h1 className="mt-6 max-w-md text-5xl font-semibold tracking-tight text-balance">
          Read the bout like you were still on the piste.
        </h1>
        <p className="mt-4 max-w-md leading-relaxed text-muted">
          Slow the phrase, mark the action, validate the touch. Then the reading speaks in language a fencer can use — never a number invented by a model.
        </p>
        {showDemoHint ? (
          <div className="mt-8 rounded-3xl border border-white/10 bg-white/[0.04] p-5 text-sm">
            <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">Local demo</p>
            <p className="mt-2 text-muted">The demo club is loaded for</p>
            <p className="mt-1 font-mono text-[13px]">demo@example.com · DemoFence2026</p>
          </div>
        ) : null}
      </div>
      <div className="fi-rise mx-auto w-full max-w-md rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.06] to-white/[0.02] p-7 shadow-[0_24px_64px_-24px_rgb(0_0_0/0.7)]">
        {showDemoHint ? <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase lg:hidden">Local demo</p> : null}
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Sign in</h1>
        {showDemoHint ? <p className="mt-2 text-sm text-muted lg:hidden">Demo: demo@example.com · DemoFence2026</p> : null}
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
            <input className={inputClass} name="email" type="email" autoComplete="email" required />
          </Field>
          <Field label="Password">
            <input className={inputClass} name="password" type="password" autoComplete="current-password" required />
          </Field>
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
