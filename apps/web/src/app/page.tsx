import Link from "next/link";
import { ChartLine, Clapperboard, ShieldCheck, Sparkles } from "lucide-react";

const steps = [
  { icon: Clapperboard, title: "Watch", body: "Upload a bout. Playback uses a short-lived signed link, never a public file." },
  { icon: ShieldCheck, title: "Mark", body: "Actions stay drafts until a person validates them. Machine suggestions never score." },
  { icon: Sparkles, title: "Read", body: "Plain-language cards from validated touches. Charts stay blank until there is something to count." },
  { icon: ChartLine, title: "Train", body: "Drills are assembled from those numbers and the exercise library. No model invents a cue." },
];

export default function HomePage() {
  return (
    <main className="relative mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-10">
      <header className="flex items-center justify-between">
        <p className="text-sm font-semibold tracking-tight">Fencing Intelligence</p>
        <div className="flex gap-2">
          <Link href="/login" className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:text-text">
            Sign in
          </Link>
          <Link
            href="/register"
            className="rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-4 py-2 text-sm font-semibold text-[#04121a] shadow-[0_8px_32px_-8px_rgb(0_212_255/0.5)] transition-all hover:brightness-110 active:scale-[0.97]"
          >
            Create account
          </Link>
        </div>
      </header>

      <div className="fi-rise flex flex-1 flex-col justify-center gap-8 py-16">
        <p className="inline-flex w-fit items-center gap-2 rounded-full border border-white/10 bg-white/[0.05] px-3.5 py-1.5 text-[11px] font-semibold tracking-[0.18em] text-primary uppercase">
          Épée · Foil · Sabre — built for high-performance salles
        </p>
        <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-balance md:text-7xl">
          Olympic-honest fencing intelligence, <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">in the language of the piste.</span>
        </h1>
        <p className="max-w-2xl text-lg leading-relaxed text-muted">
          Embedded checks mark what might have happened. You validate. Then the reading speaks in phrases a fencer can act on — rates, runs, situations — never a fake number. Designed for clubs that want Olympic-level trust. Approval is a goal, not a claim.
        </p>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/login"
            className="rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-6 py-3.5 text-sm font-semibold text-[#04121a] shadow-[0_8px_32px_-8px_rgb(0_212_255/0.5)] transition-all duration-150 hover:brightness-110 active:scale-[0.97]"
          >
            Open the demo
          </Link>
          <Link
            href="/register"
            className="rounded-full border border-white/10 bg-white/[0.06] px-6 py-3.5 text-sm font-medium transition-all duration-150 hover:bg-white/[0.1] active:scale-[0.97]"
          >
            Create an account
          </Link>
        </div>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {steps.map((step, index) => (
            <li
              key={step.title}
              className="fi-rise rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-6"
              style={{ animationDelay: `${index * 90}ms` }}
            >
              <step.icon size={20} className="text-primary" />
              <p className="mt-4 text-xs font-semibold tracking-[0.16em] text-muted uppercase">0{index + 1}</p>
              <p className="mt-1 text-lg font-semibold">{step.title}</p>
              <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </main>
  );
}
