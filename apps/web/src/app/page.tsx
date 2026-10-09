"use client";

import Link from "next/link";
import { ChartLine, Clapperboard, ShieldCheck, Sparkles } from "lucide-react";
import { useI18n } from "@/lib/i18n";

const COPY = {
  en: {
    signIn: "Sign in",
    register: "Create account",
    eyebrow: "Épée · Foil · Sabre",
    title: "Read a bout from the marks a person validated.",
    lede: "Fencing Intelligence is a video notebook for a salle. You upload the bout, mark what happened, and keep only what someone confirmed. The reading, the season, and the drills are built from those records.",
    openDemo: "Open the demo club",
    create: "Create your club",
    demoNote: "Invented fencers. Not a real season.",
    stepsTitle: "From the picture to a sentence",
    steps: [
      { title: "Upload the bout", body: "The video stays private to the club. Playback uses a short-lived link." },
      { title: "Mark and validate", body: "Actions, touches, and targets. A machine hint stays a draft until a person confirms it." },
      { title: "Read the bout", body: "Strengths and weaknesses for each fencer: runs, targets, the action that landed, the action that missed." },
      { title: "Train from the count", body: "Drills come from the exercise library and the validated numbers. Nothing is invented to fill a gap." },
    ],
    readsTitle: "What the tool will and will not say",
    reads: [
      { title: "One bout", body: "Score rebuilt from validated touches, then the patterns of that fight only. A rate under the minimum stays a fraction of this bout, not a habit." },
      { title: "A season", body: "Wins, losses, comebacks, and where touches land — once there are enough validated samples. An empty chart stays empty." },
      { title: "A competition", body: "Poules, indicator, and direct elimination. A bye is a bye. A tied elimination bout does not pick a winner." },
      { title: "Three weapons", body: "Épée, foil, and sabre stay separate. A foil phrase is not mixed into an épée season." },
    ],
    honestTitle: "The limits are part of the product",
    honest: [
      "A scoreboard light is a candidate, not a referee decision.",
      "Pose and movement checks are experimental. They do not claim to recognize a fencing action.",
      "The same action is never both a strength and a weakness.",
      "Olympic-level trust is the standard we build toward. Approval is not claimed.",
    ],
    scenariosTitle: "What the demo club contains",
    scenariosLede: "Sign in as the demo coach and walk these invented situations. Every name is fictional.",
    scenarios: [
      { title: "Open de Lyon", body: "Six épée fencers, a full poule, standings by victories then indicator, and quarter-finals with a bye and a 15–8." },
      { title: "A season with a dip", body: "Inès Morel wins, loses, and comes back from two touches down. The reading names the run and the target, not a mood." },
      { title: "Foil and sabre", body: "Chloé Nguyen and Camille Rossi on foil. Kenji Sato and Sami Elbaz on sabre. Each weapon keeps its own bouts." },
      { title: "A minor", body: "Hugo Keller is under 18. The club holds a guardian consent record before his video can be used." },
      { title: "A bout, both sides", body: "Each completed fight has a sheet of validated actions: one action that scored, one that did not, for each fencer." },
      { title: "The coach’s next hour", body: "Training sessions, an assigned parry-riposte drill, and a PDF reading of the invented Open." },
    ],
    ctaTitle: "Walk the club before you bring your own video.",
    ctaBody: "The demo password is public because the fencers are not real. Your club’s videos stay in your organization.",
  },
  fr: {
    signIn: "Connexion",
    register: "Créer un compte",
    eyebrow: "Épée · Fleuret · Sabre",
    title: "Lire un combat à partir des marques qu’une personne a validées.",
    lede: "Fencing Intelligence est le carnet vidéo d’une salle. On importe le combat, on marque ce qui s’est passé, et on ne garde que ce qu’une personne a confirmé. La lecture, la saison et les exercices sortent de ces enregistrements.",
    openDemo: "Ouvrir le club démo",
    create: "Créer votre salle",
    demoNote: "Tireurs inventés. Pas une saison réelle.",
    stepsTitle: "De l’image à une phrase",
    steps: [
      { title: "Importer le combat", body: "La vidéo reste privée à la salle. La lecture passe par un lien de courte durée." },
      { title: "Marquer et valider", body: "Actions, touches et cibles. Une suggestion de la machine reste un brouillon tant qu’une personne ne l’a pas confirmée." },
      { title: "Lire le combat", body: "Points forts et points faibles de chaque tireur : séries, zones, l’action qui a marqué, celle qui a manqué." },
      { title: "Entraîner sur le compte", body: "Les exercices viennent de la bibliothèque et des chiffres validés. Rien n’est inventé pour combler un trou." },
    ],
    readsTitle: "Ce que l’outil dit, et ce qu’il se refuse à dire",
    reads: [
      { title: "Un combat", body: "Le score est reconstruit sur les touches validées, puis les motifs de ce seul assaut. Sous le minimum d’essais, un taux reste une fraction de ce combat, pas une habitude." },
      { title: "Une saison", body: "Victoires, défaites, retours, et où les touches arrivent — dès qu’il y a assez d’échantillons validés. Un graphique vide reste vide." },
      { title: "Une compétition", body: "Poules, indicateur, et élimination directe. Un exempt est un exempt. Un match nul en tableau ne désigne pas de vainqueur." },
      { title: "Trois armes", body: "Épée, fleuret et sabre restent séparés. Une phrase de fleuret n’entre pas dans une saison d’épée." },
    ],
    honestTitle: "Les limites font partie du produit",
    honest: [
      "Une lampe de tableau est une candidate, pas une décision d’arbitre.",
      "Les contrôles de pose et de déplacement sont expérimentaux. Ils ne prétendent pas reconnaître une action d’escrime.",
      "La même action n’est jamais à la fois un point fort et un point faible.",
      "La confiance du niveau olympique est le niveau visé. Une approbation n’est pas revendiquée.",
    ],
    scenariosTitle: "Ce que contient le club démo",
    scenariosLede: "Connectez-vous comme le maître démo et parcourez ces situations inventées. Tous les noms sont fictifs.",
    scenarios: [
      { title: "Open de Lyon", body: "Six épéistes, une poule complète, un classement aux victoires puis à l’indicateur, et des quarts avec un exempt et un 15–8." },
      { title: "Une saison avec un creux", body: "Inès Morel gagne, perd, et revient après deux touches de retard. La lecture nomme la série et la zone, pas une humeur." },
      { title: "Fleuret et sabre", body: "Chloé Nguyen et Camille Rossi au fleuret. Kenji Sato et Sami Elbaz au sabre. Chaque arme garde ses assauts." },
      { title: "Un mineur", body: "Hugo Keller a moins de 18 ans. La salle conserve un consentement du responsable légal avant d’utiliser sa vidéo." },
      { title: "Un combat, des deux côtés", body: "Chaque assaut terminé a une fiche d’actions validées : une action qui a marqué, une qui n’a pas marqué, pour chaque tireur." },
      { title: "L’heure suivante du maître", body: "Des séances, un exercice de parade-riposte assigné, et un PDF de lecture de l’Open inventé." },
    ],
    ctaTitle: "Parcourez la salle avant d’apporter votre vidéo.",
    ctaBody: "Le mot de passe démo est public parce que les tireurs ne sont pas réels. Les vidéos de votre salle restent dans votre organisation.",
  },
} as const;

export default function HomePage() {
  const { locale, setLocale } = useI18n();
  const copy = COPY[locale];
  return (
    <main className="relative mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8">
      <header className="flex items-center justify-between gap-4">
        <p className="text-sm font-semibold tracking-tight">Fencing Intelligence</p>
        <div className="flex items-center gap-2">
          <div className="flex rounded-full border border-white/10 p-0.5 text-xs font-semibold">
            <button type="button" className={`rounded-full px-2.5 py-1 ${locale === "fr" ? "bg-white/10 text-text" : "text-muted"}`} onClick={() => setLocale("fr")}>
              FR
            </button>
            <button type="button" className={`rounded-full px-2.5 py-1 ${locale === "en" ? "bg-white/10 text-text" : "text-muted"}`} onClick={() => setLocale("en")}>
              EN
            </button>
          </div>
          <Link href="/login" className="rounded-full px-4 py-2 text-sm text-muted transition-colors hover:text-text active:scale-[0.97]">
            {copy.signIn}
          </Link>
          <Link href="/register" className="rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-4 py-2 text-sm font-semibold text-[#04121a] active:scale-[0.97]">
            {copy.register}
          </Link>
        </div>
      </header>

      <section className="fi-rise grid gap-8 py-16 lg:grid-cols-[1.3fr_0.7fr] lg:items-end">
        <div>
          <p className="inline-flex w-fit rounded-full border border-white/10 bg-white/[0.05] px-3.5 py-1.5 text-[11px] font-semibold tracking-[0.18em] text-primary uppercase">
            {copy.eyebrow}
          </p>
          <h1 className="mt-5 max-w-3xl text-4xl font-semibold tracking-tight text-balance md:text-6xl">{copy.title}</h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-muted">{copy.lede}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/login" className="rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-6 py-3.5 text-sm font-semibold text-[#04121a] active:scale-[0.97]">
              {copy.openDemo}
            </Link>
            <Link href="/register" className="rounded-full border border-white/10 bg-white/[0.06] px-6 py-3.5 text-sm font-medium hover:bg-white/[0.1] active:scale-[0.97]">
              {copy.create}
            </Link>
          </div>
        </div>
        <aside className="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
          <p className="text-xs font-semibold tracking-[0.16em] text-primary uppercase">{locale === "fr" ? "Club démo" : "Demo club"}</p>
          <p className="mt-3 font-mono text-sm">demo@example.com</p>
          <p className="font-mono text-sm">DemoFence2026</p>
          <p className="mt-3 text-sm leading-relaxed text-muted">{copy.demoNote}</p>
        </aside>
      </section>

      <section className="grid gap-4 pb-16">
        <h2 className="text-2xl font-semibold">{copy.stepsTitle}</h2>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {copy.steps.map((step, index) => {
            const Icon = [Clapperboard, ShieldCheck, Sparkles, ChartLine][index];
            return (
              <li key={step.title} className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.055] to-white/[0.015] p-6">
                <Icon size={20} className="text-primary" />
                <p className="mt-4 text-xs font-semibold tracking-[0.16em] text-muted uppercase">0{index + 1}</p>
                <h3 className="mt-1 text-lg font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{step.body}</p>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="grid gap-4 pb-16">
        <h2 className="text-2xl font-semibold">{copy.readsTitle}</h2>
        <div className="grid gap-3 md:grid-cols-2">
          {copy.reads.map((item) => (
            <article key={item.title} className="rounded-3xl border border-white/10 p-6">
              <h3 className="text-lg font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="grid gap-4 pb-16 lg:grid-cols-[0.8fr_1.2fr]">
        <h2 className="text-2xl font-semibold">{copy.honestTitle}</h2>
        <ul className="grid gap-3">
          {copy.honest.map((line) => (
            <li key={line} className="rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-sm leading-relaxed">
              {line}
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-4 pb-16">
        <div>
          <h2 className="text-2xl font-semibold">{copy.scenariosTitle}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">{copy.scenariosLede}</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {copy.scenarios.map((item) => (
            <article key={item.title} className="rounded-3xl border border-white/10 p-6">
              <h3 className="font-semibold">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mb-10 flex flex-col gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-white/[0.06] to-transparent p-8 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="max-w-xl text-2xl font-semibold text-balance">{copy.ctaTitle}</h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">{copy.ctaBody}</p>
        </div>
        <Link href="/login" className="w-fit rounded-full bg-gradient-to-r from-primary to-[#5eead4] px-6 py-3.5 text-sm font-semibold text-[#04121a] active:scale-[0.97]">
          {copy.openDemo}
        </Link>
      </section>
    </main>
  );
}
