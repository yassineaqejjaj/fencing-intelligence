import type { paths } from "./api-schema";

export type ApiPaths = paths;

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function csrfToken(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(/(?:^|; )fi_csrf=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const method = (init.method || "GET").toUpperCase();
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (method !== "GET" && method !== "HEAD") {
    const token = csrfToken();
    if (token) headers.set("X-CSRF-Token", token);
  }
  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: "include" });
  const contentType = response.headers.get("content-type") || "";
  const raw = await response.text();
  const payload = contentType.includes("application/json") && raw ? JSON.parse(raw) : raw;
  if (!response.ok) {
    const error = typeof payload === "object" && payload && "error" in payload ? payload.error : null;
    throw new ApiError(response.status, error?.code || "request_failed", error?.message || response.statusText);
  }
  return payload as T;
}

export type User = {
  id: string;
  email: string;
  display_name: string;
  locale: string;
  memberships: { organization_id: string; organization_name: string; role: string }[];
};

export type Athlete = {
  id: string;
  display_name: string;
  weapon: string;
  country: string;
  dominant_hand: string;
  experience_level: string;
  training_objectives: string;
  club_id: string | null;
  license_number: string;
  birth_year: number | null;
  category: string;
  is_minor: boolean;
  guardian_consent_granted: boolean | null;
};

export const CATEGORIES = ["u11", "u13", "u15", "u17", "u20", "senior", "veteran", "unspecified"] as const;

export type Competition = {
  id: string;
  name: string;
  weapon: string;
  country: string;
  location: string;
  category: string;
  start_date: string | null;
  end_date: string | null;
  source: string;
  external_id: string;
};

export type CompetitionBout = {
  id: string;
  weapon: string;
  status: string;
  competition_id: string | null;
  piste: string;
  score_limit: number;
  round: string;
  bracket_label: string;
  referee_user_id: string | null;
  started_on: string | null;
  notes: string;
  left: { athlete_id: string; score: number } | null;
  right: { athlete_id: string; score: number } | null;
};

export type Video = {
  id: string;
  title: string;
  weapon: string;
  status: string;
  visibility: string;
  bout_id: string | null;
  athlete_id: string | null;
  duration_seconds: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  error: string;
  has_playback: boolean;
  has_thumbnail: boolean;
  scoreboard_roi: { x: number; y: number; w: number; h: number } | null;
  calibration: Record<string, unknown>;
};

export type Annotation = {
  id: string;
  video_id: string;
  mode: string;
  status: string;
  source: string;
  action_type_code: string;
  start_ms: number;
  end_ms: number;
  actor_athlete_id: string | null;
  opponent_athlete_id: string | null;
  target_area: string | null;
  piste_position: number | null;
  outcome: string | null;
  notes: string;
  body: Record<string, unknown>;
};

export type Rate = { value: number | null; numerator: number; denominator: number; reason: string | null };

export type StatsBlock = {
  touches_scored: number;
  touches_conceded: number;
  offensive_attempts: number;
  offensive_success_rate: Rate;
  defensive_actions: number;
  riposte_success_rate: Rate;
  counter_attack_effectiveness: Rate;
  action_frequency: Record<string, number>;
  piste_position_distribution: { bins: { start: number; end: number; count: number }[]; missing_position_count: number };
  touch_target_distribution: { counts: Record<string, number>; missing_target_count: number };
  score_progression: { timestamp_ms: number; athlete_score?: number; opponent_score?: number; left_score?: number; right_score?: number }[];
  performance_over_time: { date: string; touches_scored: number; touches_conceded: number }[];
};

export type AthleteStats = {
  data_status: string;
  mixed_weapons: boolean;
  weapons_present: string[];
  combined: StatsBlock;
  athlete_names?: Record<string, string>;
};

export type InsightCard = {
  code: string;
  tone: "strength" | "weakness" | "neutral";
  title_en: string;
  text_en: string;
  title_fr: string;
  text_fr: string;
  evidence: { metric: string; value?: number | null; numerator?: number; denominator?: number; bout_id?: string; action_code?: string; target_area?: string };
  evidence_level: "low" | "moderate" | "high";
};

export type ActionReading = { action_code: string; attempts: number; successes: number; success_rate: Rate };

export type SituationState = { scored: number; conceded: number; touch_share: Rate };

export type BoutMomentumRow = {
  bout_id: string;
  date: string | null;
  longest_run_for: number;
  longest_run_against: number;
  lead_changes: number;
  max_deficit: number;
  final: { own: number; opponent: number };
  result: "win" | "loss" | "undecided";
  comeback: boolean;
};

export type Intelligence = {
  athlete_id: string;
  data_status: string;
  weapon_filter: string | null;
  formula_version: string;
  minimum_samples?: number;
  cards: InsightCard[];
  athlete_names?: Record<string, string>;
  profile?: {
    total_actions: number;
    by_category: Record<string, { attempts: number; successes: number; success_rate: Rate; share: Rate }>;
    by_action: Record<string, { attempts: number; successes: number; success_rate: Rate }>;
    strengths: ActionReading[];
    weaknesses: ActionReading[];
  };
  situations?: {
    states: { leading: SituationState; tied: SituationState; trailing: SituationState };
    first_touch_rate: Rate;
    last_touch_rate: Rate;
    bouts_counted: number;
  };
  momentum?: {
    bouts: BoutMomentumRow[];
    bouts_won: number;
    bouts_lost: number;
    bouts_undecided: number;
    win_rate: Rate;
    comebacks: number;
    longest_run_for: { length: number; bout_id: string } | null;
    longest_run_against: { length: number; bout_id: string } | null;
  };
  trend?: {
    points: { date: string; bout_id: string; touch_share: Rate; touches: number }[];
    direction: "improving" | "declining" | "stable" | null;
    delta: number | null;
    reason: string | null;
    undated_bouts: number;
    minimum_bouts: number;
  };
  opponents?: {
    opponent_id: string;
    bouts: number;
    scored: number;
    conceded: number;
    touch_share: Rate;
    trailing_touch_share: Rate;
    best_action: ActionReading | null;
  }[];
};

export type BoutSideReading = {
  athlete_id: string;
  scored: number;
  conceded: number;
  result: "win" | "loss" | "undecided";
  longest_run_for: number;
  longest_run_against: number;
  comeback: boolean;
  cards: InsightCard[];
};

export type BoutReading = {
  bout_id: string;
  data_status: string;
  basis?: "validated_video" | "validated_records";
  video_ids?: string[];
  athlete_names?: Record<string, string>;
  weapon?: string;
  minimum_samples?: number;
  left: BoutSideReading | null;
  right: BoutSideReading | null;
};

export type BoutMomentum = {
  bout_id: string;
  data_status: string;
  timeline: { timestamp_ms: number; left: number; right: number; scorer: "left" | "right" | "unknown"; run_length: number; target_area: string | null }[];
  left: { longest_run: number; score: number } | null;
  right: { longest_run: number; score: number } | null;
  lead_changes: number;
  left_athlete_id: string | null;
  right_athlete_id: string | null;
  athlete_names?: Record<string, string>;
};

export type ReviewItem = Annotation & {
  confidence: number | null;
  video_title: string;
  actor_name: string;
  opponent_name: string;
  action_label_en: string;
  action_label_fr: string;
  experimental: boolean;
};
