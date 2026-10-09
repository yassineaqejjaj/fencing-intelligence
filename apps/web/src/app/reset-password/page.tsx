"use client";

import { useState } from "react";
import { ApiError, api } from "@/lib/api";
import { buttonClass, Field, inputClass } from "@/components/states";

export default function ResetPage() {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-8 px-6">
      <form
        className="flex flex-col gap-4"
        method="post"
        action="/reset-password"
        onSubmit={async (event) => {
          event.preventDefault();
          const email = new FormData(event.currentTarget).get("email");
          setError("");
          try {
            const result = await api<{ message: string }>("/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
            setMessage(result.message);
          } catch (caught) {
            setError(caught instanceof ApiError ? caught.message : "Request failed");
          }
        }}
      >
        <h1 className="text-2xl font-semibold">Reset password</h1>
        <Field label="Email"><input className={inputClass} name="email" type="email" required /></Field>
        <button className={buttonClass} type="submit">Send reset link</button>
        {message ? <p className="text-sm text-muted">{message}</p> : null}
        {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      </form>
      <form
        className="flex flex-col gap-4"
        method="post"
        action="/reset-password"
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setError("");
          try {
            await api("/auth/reset-password", {
              method: "POST",
              body: JSON.stringify({ token: form.get("token"), password: form.get("password") }),
            });
            setMessage("Password updated. You can sign in.");
          } catch (caught) {
            setError(caught instanceof ApiError ? caught.message : "Reset failed");
          }
        }}
      >
        <Field label="Reset token"><input className={inputClass} name="token" required /></Field>
        <Field label="New password"><input className={inputClass} name="password" type="password" minLength={10} required /></Field>
        <button className={buttonClass} type="submit">Update password</button>
      </form>
    </main>
  );
}
