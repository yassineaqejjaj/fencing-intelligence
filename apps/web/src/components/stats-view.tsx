"use client";

import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Crosshair, Medal, Target } from "lucide-react";
import type { AthleteStats } from "@/lib/api";
import { formatRate } from "@/lib/format";
import { Empty } from "./states";
import { Card } from "./ui";

const AXIS = "#64748b";
const GRID = "rgba(148,163,184,0.12)";

export function StatsView({ stats }: { stats: AthleteStats }) {
  if (stats.data_status !== "ok") {
    return <Empty>No validated annotations or touches. Statistics will appear after you validate an action or record a touch.</Empty>;
  }
  const block = stats.combined;
  const actions = Object.entries(block.action_frequency).map(([name, count]) => ({ name: prettify(name), count }));
  const targets = Object.entries(block.touch_target_distribution.counts).map(([name, count]) => ({ name: prettify(name), count }));
  const piste = block.piste_position_distribution.bins.filter((bin) => bin.count > 0);
  return (
    <div className="grid gap-4">
      {stats.mixed_weapons ? (
        <p className="rounded-2xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm">These figures mix weapons. Open a weapon-specific view before comparing priority weapons with épée.</p>
      ) : null}
      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-3">
        <Stat icon={Medal} label="Touches scored" value={String(block.touches_scored)} accent="text-success" />
        <Stat icon={Crosshair} label="Touches conceded" value={String(block.touches_conceded)} accent="text-warning" />
        <Stat icon={Target} label="Offensive success" value={formatRate(block.offensive_success_rate)} />
        <Stat label="Riposte success" value={formatRate(block.riposte_success_rate)} />
        <Stat label="Counter-attack" value={formatRate(block.counter_attack_effectiveness)} />
        <Stat label="Defensive actions" value={String(block.defensive_actions)} />
      </dl>
      {actions.length ? <Chart title="Actions" subtitle="Validated action frequency" data={actions} /> : <Empty>No validated action frequency yet.</Empty>}
      {targets.length ? <Chart title="Touch targets" subtitle="Where validated touches landed" data={targets} /> : null}
      {piste.length ? <Chart title="Piste position" subtitle="Where the actor stood, 0–1" data={piste.map((bin) => ({ name: `${bin.start}`, count: bin.count }))} /> : null}
      {block.performance_over_time.length ? (
        <Card>
          <h3 className="font-semibold">Touches over time</h3>
          <p className="text-xs text-muted">Scored vs conceded per bout date</p>
          <div className="mt-3 h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={block.performance_over_time} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="date" stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke={AXIS} fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip />
                <Line dataKey="touches_scored" stroke="#00d4ff" strokeWidth={2.5} dot={false} />
                <Line dataKey="touches_conceded" stroke="#f59e0b" strokeWidth={2.5} dot={false} strokeDasharray="6 4" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      ) : null}
    </div>
  );
}

function prettify(name: string) {
  return name.replace(/_/g, " ");
}

function Stat({ label, value, icon: Icon, accent = "text-text" }: { label: string; value: string; icon?: typeof Medal; accent?: string }) {
  return (
    <div className="rounded-3xl border border-line bg-gradient-to-b from-surface to-surface p-4">
      <dt className="flex items-center gap-1.5 text-[11px] font-semibold tracking-[0.12em] text-muted uppercase">
        {Icon ? <Icon size={13} className="text-primary" /> : null}
        {label}
      </dt>
      <dd className={`mt-2 text-[1.7rem] leading-none font-semibold tracking-tight tabular-nums ${accent}`}>{value}</dd>
    </div>
  );
}

const BARS = ["#00d4ff", "#8b5cf6", "#22c55e", "#f59e0b", "#f472b6", "#94a3b8"];

function Chart({ title, subtitle, data }: { title: string; subtitle: string; data: { name: string; count: number }[] }) {
  return (
    <Card>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-xs text-muted">{subtitle}</p>
      <div className="mt-3 h-56">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
            <CartesianGrid stroke={GRID} vertical={false} />
            <XAxis dataKey="name" stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} interval={0} angle={data.length > 5 ? -18 : 0} height={data.length > 5 ? 48 : 28} dy={data.length > 5 ? 8 : 4} />
            <YAxis stroke={AXIS} fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} />
            <Tooltip cursor={{ fill: "rgba(148,163,184,0.08)" }} />
            <Bar dataKey="count" radius={[8, 8, 4, 4]}>
              {data.map((_, index) => (
                <Cell key={index} fill={BARS[index % BARS.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
