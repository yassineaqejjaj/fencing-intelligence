"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

const messages = {
  en: {
    product: "Fencing Intelligence",
    tagline: "Review fencing video, validate what happened, and read intelligence built from those records.",
    signIn: "Sign in",
    register: "Create account",
    dashboard: "Dashboard",
    videos: "Videos",
    bouts: "Bouts",
    competitions: "Competitions",
    athletes: "Athletes",
    performance: "Reading",
    coach: "Coach",
    clubs: "Clubs",
    training: "Training",
    reports: "Reports",
    datasets: "Datasets",
    models: "Models",
    settings: "Settings",
    privacy: "Privacy",
    logout: "Log out",
    loading: "Loading",
    error: "Something went wrong",
    empty: "Nothing here yet",
    save: "Save",
    weapons: "Épée, foil, and sabre",
  },
  fr: {
    product: "Fencing Intelligence",
    tagline: "Revoir la vidéo, valider ce qui s'est passé, et lire une intelligence construite à partir de ces enregistrements.",
    signIn: "Connexion",
    register: "Créer un compte",
    dashboard: "Tableau de bord",
    videos: "Vidéos",
    bouts: "Assauts",
    competitions: "Compétitions",
    athletes: "Athlètes",
    performance: "Lecture",
    coach: "Maître",
    clubs: "Clubs",
    training: "Entraînement",
    reports: "Rapports",
    datasets: "Jeux de données",
    models: "Modèles",
    settings: "Réglages",
    privacy: "Confidentialité",
    logout: "Déconnexion",
    loading: "Chargement",
    error: "Une erreur est survenue",
    empty: "Rien pour le moment",
    save: "Enregistrer",
    weapons: "Épée, fleuret et sabre",
  },
} as const;

type Locale = keyof typeof messages;
type Copy = { [Key in keyof (typeof messages)["en"]]: string };

const LocaleContext = createContext<{ locale: Locale; setLocale: (locale: Locale) => void; t: Copy }>({
  locale: "en",
  setLocale: () => undefined,
  t: messages.en,
});

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  useEffect(() => {
    const stored = window.localStorage.getItem("fi-locale");
    if (stored === "fr" || stored === "en") setLocaleState(stored);
  }, []);
  const setLocale = (next: Locale) => {
    setLocaleState(next);
    window.localStorage.setItem("fi-locale", next);
    document.documentElement.lang = next;
  };
  const value = useMemo(() => ({ locale, setLocale, t: messages[locale] }), [locale]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useI18n() {
  return useContext(LocaleContext);
}
