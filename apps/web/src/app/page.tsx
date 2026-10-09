"use client";

import Link from "next/link";
import { useI18n } from "@/lib/i18n";

const COPY = {
  en: {
    features: "Features",
    how: "How it works",
    clubs: "For clubs",
    data: "Data",
    signIn: "Sign in",
    tryDemo: "Try the demo",
    kicker: "En garde — ready? Fence!",
    title: "Every touch, explained.",
    lede: "Upload a bout. Fencing Intelligence ties actions to the touches a person validated, then says in plain language what scores — and what does not.",
    import: "Upload a bout",
    seeDemo: "See the demo",
    demoFine: "Demo without an account form · invented demonstration data",
    weaponsTitle: "Built around the rules of each weapon",
    epee: "Épée — the whole body",
    foil: "Foil — priority, the torso",
    sabre: "Sabre — priority, above the waist",
    featuresTitle: "What the coach sees, counted.",
    featuresLede: "From the raw video to the lesson plan, every screen rests on touches you validated.",
    featureItems: [
      { title: "Frame-by-frame video", body: "Each phrase is cut, named, and placed on a strip. A click returns you to that frame." },
      { title: "Today’s reading", body: "Plain sentences. Each one shows the numbers that carry it. Nothing is invented." },
      { title: "Athletes", body: "A profile per weapon and hand, bout after bout, with the coach’s notes." },
      { title: "Poules and tableaux", body: "Enter a poule or a direct-elimination tableau and find each filmed bout." },
      { title: "Private by default", body: "Video and data stay in your club. You decide who sees what, athlete by athlete." },
    ],
    howTitle: "From the video to the lesson.",
    steps: [
      { kicker: "En garde", title: "Upload the bout", body: "A video from a phone or the salle camera. Name the weapon and the two fencers." },
      { kicker: "Ready?", title: "Validate the touches", body: "A check may propose an action. The coach confirms or corrects it. Only validated touches count." },
      { kicker: "Fence!", title: "Read and train", body: "Strengths, actions to work, and a drill from the library. The next lesson is ready." },
    ],
    whoTitle: "Coaches, clubs, athletes.",
    who: [
      { title: "Coach", body: "Prepare the individual lesson from the week’s bouts." },
      { title: "Club", body: "Keep videos, competitions, and reports in one salle." },
      { title: "Athlete", body: "Rewatch your touches and follow the objective between competitions." },
    ],
    principle: "Our principle",
    principleBody: "Every sentence on screen shows the numbers that carry it.",
    sampleKicker: "To work · enough of a sample",
    sampleTitle: "An action that rarely scores",
    sampleBody: "Attack: 0 successes out of 5 in this bout. Finish it, or choose it less often.",
    ctaTitle: "Your next bout deserves a real reading.",
    ctaBody: "Open the demo: an invented club, a full épée poule, foil and sabre bouts, already marked.",
    openDemo: "Open the demo",
    footer: "Video analysis for fencing salles. Épée, foil, and sabre.",
    privacy: "Privacy",
    code: "Source",
  },
  fr: {
    features: "Fonctionnalités",
    how: "Comment ça marche",
    clubs: "Pour les clubs",
    data: "Données",
    signIn: "Se connecter",
    tryDemo: "Essayer la démo",
    kicker: "En garde — prêts ? Allez !",
    title: "Chaque touche, expliquée.",
    lede: "Importez une vidéo d’assaut. Fencing Intelligence relie les actions aux touches qu’une personne a validées, et dit en clair ce qui marque — et ce qui ne marque pas.",
    import: "Importer un assaut",
    seeDemo: "Voir la démo",
    demoFine: "Démo sans inscription · données de démonstration fictives",
    weaponsTitle: "Conçu avec les règles de chaque arme",
    epee: "Épée — corps entier",
    foil: "Fleuret — priorité, tronc",
    sabre: "Sabre — priorité, au-dessus de la taille",
    featuresTitle: "Ce que le maître voit, chiffré.",
    featuresLede: "De la vidéo brute au plan d’entraînement, chaque écran s’appuie sur des touches que vous avez validées.",
    featureItems: [
      { title: "Analyse vidéo image par image", body: "Chaque phrase d’armes est découpée, nommée et placée sur une frise. Un clic vous ramène à l’image." },
      { title: "Lecture du jour", body: "Des phrases en langage simple. Chacune affiche les chiffres qui la portent. Rien n’est inventé." },
      { title: "Suivi des athlètes", body: "Profil par arme et par main, progression assaut après assaut, notes du maître." },
      { title: "Poules et tableaux", body: "Saisissez une poule ou un tableau d’élimination directe et retrouvez chaque match filmé." },
      { title: "Privé par défaut", body: "Vidéos et données restent dans votre club. Vous décidez qui voit quoi, athlète par athlète." },
    ],
    howTitle: "De la vidéo à la leçon.",
    steps: [
      { kicker: "En garde", title: "Importez l’assaut", body: "Une vidéo depuis votre téléphone ou la caméra de la salle. Indiquez l’arme et les deux tireurs." },
      { kicker: "Prêts ?", title: "Validez les touches", body: "Un contrôle peut proposer une action. Le maître confirme ou corrige. Seules les touches validées comptent." },
      { kicker: "Allez !", title: "Lisez et entraînez", body: "Points forts, actions à travailler, exercice proposé : la prochaine leçon est prête." },
    ],
    whoTitle: "Maîtres, clubs, athlètes.",
    who: [
      { title: "Maître d’armes", body: "Préparez la leçon individuelle à partir des assauts de la semaine." },
      { title: "Club", body: "Centralisez vidéos, compétitions et rapports pour toute la salle." },
      { title: "Athlète", body: "Revoyez vos touches et suivez vos objectifs entre deux compétitions." },
    ],
    principle: "Notre principe",
    principleBody: "Chaque phrase affichée montre les chiffres qui la portent.",
    sampleKicker: "À travailler · échantillon du combat",
    sampleTitle: "Une action qui marque peu",
    sampleBody: "Attaque : 0 réussite sur 5 dans ce combat. Travaillez la conclusion, ou choisissez-la moins souvent.",
    ctaTitle: "Votre prochain assaut mérite une vraie lecture.",
    ctaBody: "Ouvrez la démo : un club inventé, une poule d’épée complète, du fleuret et du sabre, déjà marqués.",
    openDemo: "Ouvrir la démo",
    footer: "L’analyse vidéo pour les salles d’armes. Épée, fleuret et sabre.",
    privacy: "Confidentialité",
    code: "Code",
  },
} as const;

export default function HomePage() {
  const { locale, setLocale } = useI18n();
  const copy = COPY[locale];
  return (
    <div className="min-h-screen bg-tenue text-mask">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-5">
        <p className="text-sm font-bold tracking-tight uppercase">Fencing Intelligence</p>
        <nav className="hidden items-center gap-5 text-sm text-muted md:flex">
          <a href="#features" className="hover:text-mask">{copy.features}</a>
          <a href="#how" className="hover:text-mask">{copy.how}</a>
          <a href="#clubs" className="hover:text-mask">{copy.clubs}</a>
          <a href="#data" className="hover:text-mask">{copy.data}</a>
        </nav>
        <div className="flex items-center gap-2">
          <div className="flex rounded border border-line bg-surface p-0.5 font-mono text-[11px]">
            <button type="button" className={`rounded px-2 py-1 ${locale === "fr" ? "bg-mask text-tenue" : "text-muted"}`} onClick={() => setLocale("fr")}>FR</button>
            <button type="button" className={`rounded px-2 py-1 ${locale === "en" ? "bg-mask text-tenue" : "text-muted"}`} onClick={() => setLocale("en")}>EN</button>
          </div>
          <Link href="/login" className="px-3 py-2 text-sm text-muted hover:text-mask">{copy.signIn}</Link>
          <Link href="/login" className="fi-btn bg-mask px-4 py-2 text-sm font-semibold text-tenue">{copy.tryDemo}</Link>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl gap-20 px-6 pt-12 pb-20">
        <section className="grid items-end gap-10 lg:grid-cols-[1.15fr_0.85fr]">
          <div>
            <p className="font-mono text-[12px] tracking-[0.16em] text-muted uppercase">{copy.kicker}</p>
            <h1 className="mt-4 max-w-3xl text-5xl text-balance md:text-7xl">{copy.title}</h1>
            <p className="mt-6 max-w-xl text-muted">{copy.lede}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/register" className="fi-btn bg-mask px-5 py-3 text-sm font-semibold text-tenue">{copy.import}</Link>
              <Link href="/login" className="fi-btn border border-line bg-surface px-5 py-3 text-sm font-semibold">{copy.seeDemo}</Link>
            </div>
            <p className="mt-4 font-mono text-[12px] text-muted">{copy.demoFine}</p>
          </div>
          <aside className="rounded-2xl bg-mask p-6 text-tenue shadow-[var(--shadow-float)]">
            <div className="flex items-end justify-between gap-4">
              <p className="font-mono text-sm">
                <span className="text-lamp-red">K. Sato</span>
                <span className="mx-2 text-2xl">4:2</span>
                <span className="text-lamp-green">S. Elbaz</span>
              </p>
              <p className="font-mono text-[11px] tracking-wider text-tenue/70">SABRE · 02:14</p>
            </div>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg bg-white/5 p-4">
                <p className="font-mono text-[10px] tracking-[0.14em] text-voyant">POINT FORT</p>
                <p className="mt-2 font-mono text-lg">Riposte · 5/5</p>
              </div>
              <div className="rounded-lg bg-white/5 p-4">
                <p className="font-mono text-[10px] tracking-[0.14em] text-warning">À TRAVAILLER</p>
                <p className="mt-2 font-mono text-lg">Attaque · 0/5</p>
              </div>
            </div>
            <p className="mt-4 text-xs text-tenue/60">{locale === "fr" ? "Exemple de lecture. Les noms sont fictifs. Rouge = gauche, vert = droite." : "A sample reading. The names are fictional. Red = left, green = right."}</p>
          </aside>
        </section>

        <section aria-label={copy.weaponsTitle} className="grid gap-3 border-y border-line py-6 md:grid-cols-3">
          {[
            ["É", copy.epee],
            ["F", copy.foil],
            ["S", copy.sabre],
          ].map(([mark, label]) => (
            <p key={mark} className="flex items-center gap-3 text-sm">
              <span className="flex h-7 w-7 items-center justify-center rounded border border-line bg-surface font-mono text-xs">{mark}</span>
              {label}
            </p>
          ))}
        </section>

        <section id="features" className="grid gap-8">
          <div>
            <p className="font-mono text-[12px] tracking-[0.16em] text-muted">01 — {copy.features}</p>
            <h2 className="mt-2 max-w-xl text-4xl">{copy.featuresTitle}</h2>
            <p className="mt-3 max-w-2xl text-muted">{copy.featuresLede}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {copy.featureItems.map((item) => (
              <article key={item.title} className="rounded-xl border border-line bg-surface p-6">
                <h3 className="text-lg font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm text-muted">{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="how" className="grid gap-8">
          <div>
            <p className="font-mono text-[12px] tracking-[0.16em] text-muted">02 — {copy.how}</p>
            <h2 className="mt-2 text-4xl">{copy.howTitle}</h2>
          </div>
          <ol className="grid gap-3 md:grid-cols-3">
            {copy.steps.map((step) => (
              <li key={step.title} className="rounded-xl border border-line bg-surface p-6">
                <p className="font-mono text-[12px] tracking-[0.14em] text-muted uppercase">{step.kicker}</p>
                <h3 className="mt-3 text-xl font-semibold">{step.title}</h3>
                <p className="mt-2 text-sm text-muted">{step.body}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="clubs" className="grid gap-8 lg:grid-cols-[1fr_1fr]">
          <div>
            <p className="font-mono text-[12px] tracking-[0.16em] text-muted">03 — {copy.clubs}</p>
            <h2 className="mt-2 text-4xl">{copy.whoTitle}</h2>
            <ul className="mt-6 grid gap-4">
              {copy.who.map((item) => (
                <li key={item.title}>
                  <p className="font-semibold">{item.title}</p>
                  <p className="text-sm text-muted">{item.body}</p>
                </li>
              ))}
            </ul>
          </div>
          <aside id="data" className="rounded-2xl bg-mask p-7 text-tenue">
            <p className="font-mono text-[11px] tracking-[0.16em] text-voyant uppercase">{copy.principle}</p>
            <p className="mt-4 text-2xl leading-snug font-semibold uppercase" style={{ fontStretch: "112%" }}>{copy.principleBody}</p>
            <div className="mt-8 rounded-xl bg-white/5 p-5">
              <p className="font-mono text-[10px] tracking-[0.14em] text-warning">{copy.sampleKicker}</p>
              <h3 className="mt-2 text-lg font-semibold normal-case">{copy.sampleTitle}</h3>
              <p className="mt-2 text-sm text-tenue/80">{copy.sampleBody}</p>
              <p className="mt-3 font-mono text-xs text-tenue/60">réussite 0/5 · attaque</p>
            </div>
          </aside>
        </section>

        <section className="flex flex-col items-start justify-between gap-6 rounded-2xl border border-line bg-surface p-8 md:flex-row md:items-end">
          <div>
            <h2 className="max-w-xl text-4xl">{copy.ctaTitle}</h2>
            <p className="mt-3 max-w-xl text-muted">{copy.ctaBody}</p>
            <p className="mt-3 font-mono text-sm">demo@example.com · DemoFence2026</p>
          </div>
          <Link href="/login" className="fi-btn bg-mask px-5 py-3 text-sm font-semibold text-tenue">{copy.openDemo}</Link>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto grid max-w-6xl gap-6 px-6 py-10 text-sm md:grid-cols-[1.4fr_1fr_1fr]">
          <div>
            <p className="font-bold tracking-tight uppercase">Fencing Intelligence</p>
            <p className="mt-2 max-w-sm text-muted">{copy.footer}</p>
          </div>
          <div className="grid content-start gap-2">
            <a href="#features" className="text-muted hover:text-mask">{copy.features}</a>
            <a href="#how" className="text-muted hover:text-mask">{copy.how}</a>
            <Link href="/login" className="text-muted hover:text-mask">{copy.tryDemo}</Link>
          </div>
          <div className="grid content-start gap-2">
            <Link href="/privacy" className="text-muted hover:text-mask">{copy.privacy}</Link>
            <a href="https://github.com/yassineaqejjaj/fencing-intelligence" className="text-muted hover:text-mask">{copy.code}</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
