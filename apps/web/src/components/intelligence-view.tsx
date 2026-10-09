"use client";

import Link from "next/link";
import { Area, AreaChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Flame, Lightbulb, ShieldAlert, Sparkles, TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { ActionReading, BoutMomentum, BoutReading, InsightCard, Intelligence, Rate } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { formatRate } from "@/lib/format";
import { Empty } from "./states";
import { Badge, Card } from "./ui";

const AXIS = "#64748b";
const GRID = "rgba(148,163,184,0.12)";

const COPY = {
  en: {
    empty: "No validated actions or touches yet. Insight appears once a coach or the athlete validates what happened on the piste.",
    noCards: "Not enough validated samples for a reading yet. Each insight needs at least {n} validated actions or touches behind it.",
    cardsTitle: "What the validated data says",
    cardsSub: "Plain-language readings. Every sentence shows the numbers behind it.",
    evidence: "Evidence",
    samples: "samples",
    profile: "Tactical profile",
    profileSub: "Validated actions by family and how often each one ends in a touch.",
    attempts: "attempts",
    situations: "Score situations",
    situationsSub: "Share of exchanges won depending on the score before the touch.",
    leading: "Leading",
    tied: "Tied",
    trailing: "Trailing",
    exchanges: "exchanges",
    firstTouch: "First touch",
    lastTouch: "Last touch",
    bouts: "bouts",
    momentum: "Momentum",
    momentumSub: "Scoring runs and lead changes rebuilt from validated touches.",
    won: "Won",
    lost: "Lost",
    comebacks: "Comebacks",
    longestFor: "Longest run for",
    longestAgainst: "Longest run against",
    trend: "Trend across bouts",
    trendSub: "Touch share per dated bout. A direction is only named from {n} dated bouts.",
    trendInsufficient: "Only {k} dated bouts so far. The trend line is drawn, but no direction is claimed before {n}.",
    improving: "Improving",
    declining: "Declining",
    stable: "Stable",
    opponents: "Head to head",
    opponentsSub: "Touch share per opponent, and the action that scores most against them.",
    opponent: "Opponent",
    share: "Touch share",
    whenTrailing: "When trailing",
    bestAction: "Best action",
    scored: "scored",
    conceded: "conceded",
    openBout: "Open bout",
    minimum: "Below the {n}-sample minimum readings stay blank. A blank is honest, a zero would be a lie.",
    level: { low: "small sample", moderate: "fair sample", high: "solid sample" },
  },
  fr: {
    empty: "Pas encore d'actions ni de touches validées. L'intelligence apparaît dès qu'un maître ou l'athlète valide ce qui s'est passé sur la piste.",
    noCards: "Pas encore assez d'échantillons validés pour une lecture. Chaque insight repose sur au moins {n} actions ou touches validées.",
    cardsTitle: "Ce que disent les données validées",
    cardsSub: "Lectures en langage simple. Chaque phrase montre les chiffres qui la portent.",
    evidence: "Preuve",
    samples: "échantillons",
    profile: "Profil tactique",
    profileSub: "Actions validées par famille et fréquence à laquelle chacune finit en touche.",
    attempts: "tentatives",
    situations: "Situations de score",
    situationsSub: "Part des échanges gagnés selon le score avant la touche.",
    leading: "En tête",
    tied: "Égalité",
    trailing: "Mené",
    exchanges: "échanges",
    firstTouch: "Première touche",
    lastTouch: "Dernière touche",
    bouts: "assauts",
    momentum: "Momentum",
    momentumSub: "Séries et renversements reconstruits à partir des touches validées.",
    won: "Gagnés",
    lost: "Perdus",
    comebacks: "Retours",
    longestFor: "Plus longue série pour",
    longestAgainst: "Plus longue série contre",
    trend: "Tendance sur les assauts",
    trendSub: "Part de touches par assaut daté. Une direction n'est nommée qu'à partir de {n} assauts datés.",
    trendInsufficient: "Seulement {k} assauts datés pour l'instant. La courbe est tracée, mais aucune direction n'est affirmée avant {n}.",
    improving: "En progression",
    declining: "En recul",
    stable: "Stable",
    opponents: "Face à face",
    opponentsSub: "Part de touches par adversaire, et l'action qui marque le plus contre chacun.",
    opponent: "Adversaire",
    share: "Part de touches",
    whenTrailing: "Quand mené",
    bestAction: "Meilleure action",
    scored: "marquées",
    conceded: "concédées",
    openBout: "Ouvrir l'assaut",
    minimum: "Sous le minimum de {n} échantillons, les lectures restent vides. Un vide est honnête, un zéro serait un mensonge.",
    level: { low: "petit échantillon", moderate: "échantillon correct", high: "échantillon solide" },
  },
} as const;

type Copy = {
  [K in keyof (typeof COPY)["en"]]: (typeof COPY)["en"][K] extends string
    ? string
    : { [P in keyof (typeof COPY)["en"][K]]: string };
};

function fill(template: string, values: Record<string, string | number>) {
  return template.replace(/\{(\w+)\}/g, (_, key) => String(values[key] ?? ""));
}

function pretty(code: string) {
  return code.replace(/_/g, " ");
}

export function IntelligenceView({ data, compact = false, athleteHref }: { data: Intelligence; compact?: boolean; athleteHref?: string }) {
  const { locale } = useI18n();
  const copy: Copy = COPY[locale];
  if (data.data_status !== "ok") {
    return <Empty>{copy.empty}</Empty>;
  }
  const minimum = data.minimum_samples ?? 5;
  return (
    <div className="grid gap-4">
      <Cards cards={data.cards} copy={copy} locale={locale} minimum={minimum} athleteHref={athleteHref} />
      {compact ? null : (
        <>
          {data.situations ? <Situations data={data} copy={copy} minimum={minimum} /> : null}
          <div className="grid gap-4 lg:grid-cols-2">
            {data.profile ? <Profile profile={data.profile} copy={copy} locale={locale} minimum={minimum} /> : null}
            {data.momentum ? <Momentum data={data} copy={copy} /> : null}
          </div>
          {data.trend ? <Trend data={data} copy={copy} /> : null}
          {data.opponents?.length ? <Opponents data={data} copy={copy} /> : null}
          <p className="px-1 text-xs text-muted">{fill(copy.minimum, { n: minimum })}</p>
        </>
      )}
    </div>
  );
}

const TONE: Record<InsightCard["tone"], { ring: string; glow: string; icon: typeof Sparkles; label: { en: string; fr: string } }> = {
  strength: { ring: "border-success/30", glow: "from-success/15", icon: Sparkles, label: { en: "Strength", fr: "Point fort" } },
  weakness: { ring: "border-warning/30", glow: "from-warning/15", icon: ShieldAlert, label: { en: "To work on", fr: "À travailler" } },
  neutral: { ring: "border-primary/30", glow: "from-primary/15", icon: Lightbulb, label: { en: "Reading", fr: "Lecture" } },
};

function Cards({ cards, copy, locale, minimum, athleteHref, heading, subheading }: { cards: InsightCard[]; copy: Copy; locale: "en" | "fr"; minimum: number; athleteHref?: string; heading?: string; subheading?: string }) {
  const title = heading ?? copy.cardsTitle;
  return (
    <section aria-label={title}>
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h3 className="font-semibold">{title}</h3>
          <p className="text-xs text-muted">{subheading ?? copy.cardsSub}</p>
        </div>
        {athleteHref ? <Link href={athleteHref} className="text-xs font-semibold text-primary hover:underline">{locale === "fr" ? "Analyse complète →" : "Full analysis →"}</Link> : null}
      </div>
      {cards.length === 0 ? (
        <Empty>{fill(copy.noCards, { n: minimum })}</Empty>
      ) : (
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {cards.map((card) => {
            const tone = TONE[card.tone];
            const Icon = tone.icon;
            const title = locale === "fr" ? card.title_fr : card.title_en;
            const text = locale === "fr" ? card.text_fr : card.text_en;
            const evidence = card.evidence;
            return (
              <li key={card.code} className={`relative overflow-hidden rounded-3xl border ${tone.ring} bg-gradient-to-b ${tone.glow} to-surface p-5`}>
                <div className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.14em] text-muted uppercase">
                    <Icon size={13} className={card.tone === "strength" ? "text-success" : card.tone === "weakness" ? "text-warning" : "text-primary"} />
                    {tone.label[locale]}
                  </span>
                  <span className="text-[11px] text-muted">{copy.level[card.evidence_level]}</span>
                </div>
                <h4 className="mt-3 text-base leading-tight font-semibold tracking-tight">{title}</h4>
                <p className="mt-1.5 text-sm leading-relaxed text-text/90">{text}</p>
                <p className="mt-3 flex flex-wrap items-center gap-x-2 text-[11px] text-muted tabular-nums">
                  <span className="font-semibold tracking-wide uppercase">{copy.evidence}</span>
                  <span>{pretty(evidence.metric)}</span>
                  {evidence.numerator !== undefined && evidence.denominator !== undefined ? <span>· {evidence.numerator}/{evidence.denominator}</span> : null}
                  {evidence.bout_id ? (
                    <Link href={`/bouts/${evidence.bout_id}`} className="text-primary hover:underline">· {copy.openBout}</Link>
                  ) : null}
                  {evidence.action_code ? <span>· {pretty(evidence.action_code)}</span> : null}
                  {evidence.target_area ? <span>· {pretty(evidence.target_area)}</span> : null}
                </p>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function RateBar({ rate, accent = "bg-primary" }: { rate: Rate; accent?: string }) {
  const value = rate.value;
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface">
      {value === null ? null : <div className={`h-full rounded-full ${accent} transition-[width] duration-500 ease-out motion-reduce:transition-none`} style={{ width: `${Math.round(value * 100)}%` }} />}
    </div>
  );
}

function shownRate(rate: Rate, minimum: number) {
  return rate.denominator < minimum ? "—" : formatRate(rate);
}

function Situations({ data, copy, minimum }: { data: Intelligence; copy: Copy; minimum: number }) {
  const situations = data.situations!;
  const states: { key: "leading" | "tied" | "trailing"; label: string; accent: string }[] = [
    { key: "leading", label: copy.leading, accent: "bg-success" },
    { key: "tied", label: copy.tied, accent: "bg-primary" },
    { key: "trailing", label: copy.trailing, accent: "bg-warning" },
  ];
  return (
    <Card>
      <h3 className="font-semibold">{copy.situations}</h3>
      <p className="text-xs text-muted">{copy.situationsSub}</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {states.map(({ key, label, accent }) => {
          const state = situations.states[key];
          const ready = state.touch_share.denominator >= minimum;
          return (
            <div key={key} className="rounded-2xl border border-line bg-surface p-4">
              <p className="text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">{label}</p>
              <p className={`mt-2 text-[1.7rem] leading-none font-semibold tracking-tight tabular-nums ${ready ? "" : "text-muted"}`}>{shownRate(state.touch_share, minimum)}</p>
              <div className="mt-3"><RateBar rate={ready ? state.touch_share : { ...state.touch_share, value: null }} accent={accent} /></div>
              <p className="mt-2 text-xs text-muted tabular-nums">
                {state.scored} {copy.scored} · {state.conceded} {copy.conceded} · {state.touch_share.denominator} {copy.exchanges}
              </p>
            </div>
          );
        })}
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="flex items-center justify-between rounded-2xl border border-line px-4 py-3">
          <dt className="text-muted">{copy.firstTouch}</dt>
          <dd className="font-semibold tabular-nums">{shownRate(situations.first_touch_rate, minimum)} <span className="text-xs font-normal text-muted">· {situations.first_touch_rate.denominator} {copy.bouts}</span></dd>
        </div>
        <div className="flex items-center justify-between rounded-2xl border border-line px-4 py-3">
          <dt className="text-muted">{copy.lastTouch}</dt>
          <dd className="font-semibold tabular-nums">{shownRate(situations.last_touch_rate, minimum)} <span className="text-xs font-normal text-muted">· {situations.last_touch_rate.denominator} {copy.bouts}</span></dd>
        </div>
      </dl>
    </Card>
  );
}

function Profile({ profile, copy, locale, minimum }: { profile: NonNullable<Intelligence["profile"]>; copy: Copy; locale: "en" | "fr"; minimum: number }) {
  const categories = Object.entries(profile.by_category).filter(([, value]) => value.attempts > 0).sort((a, b) => b[1].attempts - a[1].attempts);
  const actions = Object.entries(profile.by_action).sort((a, b) => b[1].attempts - a[1].attempts).slice(0, 8);
  return (
    <Card>
      <h3 className="font-semibold">{copy.profile}</h3>
      <p className="text-xs text-muted">{copy.profileSub}</p>
      {categories.length === 0 ? <div className="mt-3"><Empty>{fill(copy.noCards, { n: minimum })}</Empty></div> : null}
      <ul className="mt-4 grid gap-3">
        {categories.map(([name, value]) => (
          <li key={name} className="grid gap-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="capitalize">{pretty(name)}</span>
              <span className="text-xs text-muted tabular-nums">{value.attempts} {copy.attempts} · {shownRate(value.success_rate, minimum)}</span>
            </div>
            <RateBar rate={value.share} accent="bg-mask" />
          </li>
        ))}
      </ul>
      {actions.length ? (
        <ul className="mt-5 grid gap-2 border-t border-line pt-4">
          {actions.map(([code, value]) => (
            <li key={code} className="flex items-center justify-between gap-3 text-sm">
              <span className="flex items-center gap-2">
                <span className="capitalize">{pretty(code)}</span>
                {value.attempts < minimum ? <Badge tone="neutral">{locale === "fr" ? "n faible" : "low n"}</Badge> : null}
              </span>
              <span className="flex items-center gap-3 tabular-nums">
                <span className="text-xs text-muted">{value.successes}/{value.attempts}</span>
                <span className={`w-14 text-right font-semibold ${value.attempts < minimum ? "text-muted" : ""}`}>{value.attempts < minimum ? "—" : formatRate(value.success_rate)}</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
      <ActionBadges strengths={profile.strengths} weaknesses={profile.weaknesses} locale={locale} />
    </Card>
  );
}

function ActionBadges({ strengths, weaknesses, locale }: { strengths: ActionReading[]; weaknesses: ActionReading[]; locale: "en" | "fr" }) {
  if (!strengths.length && !weaknesses.length) return null;
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {strengths.map((row) => (
        <Badge key={`s-${row.action_code}`} tone="success">
          {pretty(row.action_code)} · {formatRate(row.success_rate)}
        </Badge>
      ))}
      {weaknesses.map((row) => (
        <Badge key={`w-${row.action_code}`} tone="warning">
          {pretty(row.action_code)} · {formatRate(row.success_rate)} · {locale === "fr" ? "à travailler" : "to work on"}
        </Badge>
      ))}
    </div>
  );
}

function Momentum({ data, copy }: { data: Intelligence; copy: Copy }) {
  const momentum = data.momentum!;
  return (
    <Card>
      <h3 className="font-semibold">{copy.momentum}</h3>
      <p className="text-xs text-muted">{copy.momentumSub}</p>
      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Mini label={copy.won} value={String(momentum.bouts_won)} accent="text-success" />
        <Mini label={copy.lost} value={String(momentum.bouts_lost)} accent="text-warning" />
        <Mini label={copy.comebacks} value={String(momentum.comebacks)} icon={Flame} />
        <Mini label={copy.longestFor} value={momentum.longest_run_for ? String(momentum.longest_run_for.length) : "—"} href={momentum.longest_run_for ? `/bouts/${momentum.longest_run_for.bout_id}` : undefined} />
        <Mini label={copy.longestAgainst} value={momentum.longest_run_against ? String(momentum.longest_run_against.length) : "—"} href={momentum.longest_run_against ? `/bouts/${momentum.longest_run_against.bout_id}` : undefined} />
        <Mini label="Win rate" value={formatRate(momentum.win_rate)} />
      </dl>
      {momentum.bouts.length ? (
        <ul className="mt-4 grid gap-1.5 border-t border-line pt-4 text-sm">
          {momentum.bouts.slice(-6).reverse().map((bout) => (
            <li key={bout.bout_id} className="flex items-center justify-between gap-3">
              <Link href={`/bouts/${bout.bout_id}`} className="truncate text-muted hover:text-text">{bout.date ?? "—"}</Link>
              <span className="flex items-center gap-2 tabular-nums">
                <span className="font-semibold">{bout.final.own}–{bout.final.opponent}</span>
                <Badge tone={bout.result === "win" ? "success" : bout.result === "loss" ? "warning" : "neutral"}>{bout.result}</Badge>
                {bout.comeback ? <Flame size={14} className="text-warning" aria-label="comeback" /> : null}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </Card>
  );
}

function Mini({ label, value, accent = "text-text", icon: Icon, href }: { label: string; value: string; accent?: string; icon?: typeof Flame; href?: string }) {
  const body = (
    <>
      <dt className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">
        {Icon ? <Icon size={12} className="text-warning" /> : null}
        {label}
      </dt>
      <dd className={`mt-1.5 text-xl leading-none font-semibold tabular-nums ${accent}`}>{value}</dd>
    </>
  );
  const className = "rounded-2xl border border-line bg-surface p-3";
  return href ? <Link href={href} className={`${className} block hover:bg-surface`}>{body}</Link> : <div className={className}>{body}</div>;
}

function Trend({ data, copy }: { data: Intelligence; copy: Copy }) {
  const trend = data.trend!;
  const points = trend.points.map((point) => ({ date: point.date, share: point.touch_share.value === null ? null : Math.round(point.touch_share.value * 100), touches: point.touches }));
  const Icon = trend.direction === "improving" ? TrendingUp : trend.direction === "declining" ? TrendingDown : Minus;
  return (
    <Card>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold">{copy.trend}</h3>
          <p className="text-xs text-muted">{fill(copy.trendSub, { n: trend.minimum_bouts })}</p>
        </div>
        {trend.direction ? (
          <Badge tone={trend.direction === "improving" ? "success" : trend.direction === "declining" ? "warning" : "neutral"}>
            <Icon size={13} /> {copy[trend.direction]}
          </Badge>
        ) : null}
      </div>
      {points.length === 0 ? (
        <div className="mt-3"><Empty>{fill(copy.trendInsufficient, { k: 0, n: trend.minimum_bouts })}</Empty></div>
      ) : (
        <>
          {!trend.direction ? <p className="mt-3 rounded-2xl border border-line bg-surface px-4 py-2.5 text-xs text-muted">{fill(copy.trendInsufficient, { k: points.length, n: trend.minimum_bouts })}</p> : null}
          <div className="mt-3 h-52">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                <defs>
                  <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00d4ff" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="date" stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 100]} stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} unit="%" />
                <Tooltip formatter={(value) => [`${value}%`, copy.share]} />
                <ReferenceLine y={50} stroke="rgba(148,163,184,0.4)" strokeDasharray="4 4" />
                <Area type="monotone" dataKey="share" stroke="#00d4ff" strokeWidth={2.5} fill="url(#trendFill)" connectNulls dot={{ r: 3, fill: "#00d4ff", strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </Card>
  );
}

function Opponents({ data, copy }: { data: Intelligence; copy: Copy }) {
  const names = data.athlete_names ?? {};
  return (
    <Card>
      <h3 className="font-semibold">{copy.opponents}</h3>
      <p className="text-xs text-muted">{copy.opponentsSub}</p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">
              <th className="py-2 pr-3 font-semibold">{copy.opponent}</th>
              <th className="py-2 pr-3 font-semibold">{copy.bouts}</th>
              <th className="py-2 pr-3 font-semibold">{copy.share}</th>
              <th className="py-2 pr-3 font-semibold">{copy.whenTrailing}</th>
              <th className="py-2 font-semibold">{copy.bestAction}</th>
            </tr>
          </thead>
          <tbody>
            {data.opponents!.map((row) => (
              <tr key={row.opponent_id} className="border-t border-line">
                <td className="py-2.5 pr-3">
                  <Link href={`/athletes/${row.opponent_id}`} className="font-medium hover:underline">{names[row.opponent_id] ?? row.opponent_id.slice(0, 8)}</Link>
                </td>
                <td className="py-2.5 pr-3 tabular-nums">{row.bouts}</td>
                <td className="py-2.5 pr-3">
                  <div className="flex items-center gap-2 tabular-nums">
                    <span className="w-14 font-semibold">{formatRate(row.touch_share)}</span>
                    <span className="text-xs text-muted">{row.scored}–{row.conceded}</span>
                  </div>
                </td>
                <td className="py-2.5 pr-3 tabular-nums">{formatRate(row.trailing_touch_share)}</td>
                <td className="py-2.5">
                  {row.best_action ? <Badge tone="success">{pretty(row.best_action.action_code)} · {formatRate(row.best_action.success_rate)}</Badge> : <span className="text-xs text-muted">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export function BoutReadingView({ data }: { data: BoutReading }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const names = data.athlete_names ?? {};
  if (data.data_status !== "ok" || (!data.left && !data.right)) {
    return (
      <Empty>
        {locale === "fr"
          ? "Pas encore de lecture pour ce combat. Importez la vidéo, validez les marques et les touches : les points forts et les points faibles apparaissent alors. Un brouillon proposé par la machine ne compte pas."
          : "No reading for this bout yet. Upload the video, then validate the marks and touches. Strengths and weaknesses appear from those records. A machine draft does not count."}
      </Empty>
    );
  }
  const basis = data.basis === "validated_video"
    ? locale === "fr"
      ? "Lu sur les marques validées de la vidéo de ce combat. Une suggestion non validée ne change rien."
      : "Read from the validated marks on this bout's video. An unvalidated suggestion changes nothing."
    : locale === "fr"
      ? "Lu sur les touches validées de ce combat. En production, importez la vidéo : la même lecture se remplit à partir des marques validées sur l'image."
      : "Read from this bout's validated touches. In production, upload the video: the same reading fills in from the marks validated on the picture.";
  const sides = [data.left, data.right].filter((side) => side && (side.cards.length > 0 || side.scored + side.conceded > 0));
  return (
    <div className="grid gap-4">
      <div>
        <h3 className="font-semibold">{locale === "fr" ? "Lecture du combat" : "Bout reading"}</h3>
        <p className="text-xs text-muted">{basis}</p>
      </div>
      <div className={`grid gap-4 ${sides.length > 1 ? "lg:grid-cols-2" : ""}`}>
        {sides.map((side) => {
          if (!side) return null;
          const name = names[side.athlete_id] ?? side.athlete_id.slice(0, 8);
          const result = locale === "fr"
            ? side.result === "win" ? "gagné" : side.result === "loss" ? "perdu" : "non décidé"
            : side.result;
          const subheading = `${side.scored}–${side.conceded} · ${result}`;
          if (side.cards.length === 0) {
            return (
              <Card key={side.athlete_id}>
                <h3 className="font-semibold">{name}</h3>
                <p className="text-xs text-muted">{subheading}</p>
                <p className="mt-3 text-sm text-muted">
                  {locale === "fr"
                    ? "Les touches sont là, mais aucune série, zone ou action ne se détache encore dans ce combat."
                    : "The touches are recorded, but no run, target, or action stands out in this bout yet."}
                </p>
              </Card>
            );
          }
          return (
            <Cards
              key={side.athlete_id}
              cards={side.cards}
              copy={copy}
              locale={locale}
              minimum={data.minimum_samples ?? 5}
              heading={name}
              subheading={subheading}
            />
          );
        })}
      </div>
      {data.video_ids && data.video_ids.length > 0 ? (
        <p className="text-xs text-muted">
          <Link href={`/videos/${data.video_ids[0]}`} className="font-semibold text-primary hover:underline">
            {locale === "fr" ? "Ouvrir la vidéo du combat" : "Open the bout video"}
          </Link>
        </p>
      ) : null}
    </div>
  );
}

export function BoutStory({ data }: { data: BoutMomentum }) {
  const { locale } = useI18n();
  const copy = COPY[locale];
  const names = data.athlete_names ?? {};
  const leftName = (data.left_athlete_id && names[data.left_athlete_id]) || (locale === "fr" ? "Gauche" : "Left");
  const rightName = (data.right_athlete_id && names[data.right_athlete_id]) || (locale === "fr" ? "Droite" : "Right");
  if (data.data_status !== "ok" || data.timeline.length === 0) {
    return <Empty>{locale === "fr" ? "Pas encore de touches validées dans cet assaut. Le récit se construit touche par touche." : "No validated touches in this bout yet. The story is built touch by touch."}</Empty>;
  }
  const last = data.timeline[data.timeline.length - 1];
  const chart = data.timeline.map((row, index) => ({ n: index + 1, left: row.left, right: row.right }));
  return (
    <Card>
      <h3 className="font-semibold">{locale === "fr" ? "Récit de l'assaut" : "Bout story"}</h3>
      <p className="text-xs text-muted">
        {locale === "fr"
          ? "Score reconstruit uniquement à partir des touches validées. Ce n'est pas une décision d'arbitre."
          : "Score rebuilt only from validated touches. This is not a referee decision."}
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Mini label={leftName} value={`${data.left?.score ?? last.left}`} accent="text-lamp-red" />
        <Mini label={rightName} value={`${data.right?.score ?? last.right}`} accent="text-lamp-green" />
        <Mini label={locale === "fr" ? "Changements de tête" : "Lead changes"} value={String(data.lead_changes)} />
        <Mini label={locale === "fr" ? "Plus longue série" : "Longest run"} value={String(Math.max(data.left?.longest_run ?? 0, data.right?.longest_run ?? 0))} icon={Flame} />
      </dl>
      <ol className="mt-4 flex flex-wrap gap-1.5" aria-label={locale === "fr" ? "Touches dans l'ordre" : "Touches in order"}>
        {data.timeline.map((row, index) => {
          const mine = row.scorer === "left";
          const hot = row.run_length >= 2;
          return (
            <li key={`${row.timestamp_ms}-${index}`}>
              <span
                className={`inline-flex min-w-8 items-center justify-center rounded-full px-2 py-1 text-[11px] font-semibold tabular-nums ${
                  row.scorer === "unknown"
                    ? "bg-tenue text-muted"
                    : mine
                      ? "bg-lamp-red/15 text-lamp-red"
                      : "bg-lamp-green/15 text-lamp-green"
                } ${hot ? "ring-1 ring-warning/60" : ""}`}
                title={`${row.left}–${row.right}${hot ? ` · ${row.run_length}` : ""}`}
              >
                {index + 1}
              </span>
            </li>
          );
        })}
      </ol>
      <div className="mt-4 h-44">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chart} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="n" stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
            <Tooltip />
            <Area type="stepAfter" dataKey="left" name={leftName} stroke="#00d4ff" fill="rgba(0,212,255,0.12)" strokeWidth={2} />
            <Area type="stepAfter" dataKey="right" name={rightName} stroke="#8b5cf6" fill="rgba(139,92,246,0.12)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-2 text-xs text-muted">{copy.momentumSub}</p>
    </Card>
  );
}
