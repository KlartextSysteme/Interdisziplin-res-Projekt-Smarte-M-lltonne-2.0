"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowLeft,
  Battery,
  CheckCircle2,
  Loader2,
  RotateCcw,
  Shuffle,
  SlidersHorizontal,
  Trash2,
} from "lucide-react";
import {
  getDemoStatus,
  resetDemoScenario,
  type DemoProfile,
  type DemoStatus,
} from "@/lib/api";

interface Scenario {
  profile: DemoProfile;
  title: string;
  detail: string;
  icon: typeof RotateCcw;
}

const scenarios: Scenario[] = [
  {
    profile: "realistic_shift",
    title: "Schichtbeginn",
    detail: "gemischte Füllstände, einige dringende Tonnen, einzelne Meldungen",
    icon: RotateCcw,
  },
  {
    profile: "hardware_focus",
    title: "FH-Fokus",
    detail: "FH-Campus-Tonne voll, Umfeld plausibel, ideal für Hardwaretests",
    icon: Trash2,
  },
  {
    profile: "high_load",
    title: "Hohe Auslastung",
    detail: "viele volle Tonnen, Kapazität und Routenpriorisierung werden sichtbar",
    icon: AlertTriangle,
  },
  {
    profile: "quiet_day",
    title: "Ruhiger Tag",
    detail: "wenige Abholungen, niedriger Druck, gute Ausgangslage für Basischecks",
    icon: Battery,
  },
  {
    profile: "random",
    title: "Zufallswerte",
    detail: "alle Tonnen neu würfeln, nützlich für wiederholte Tests",
    icon: Shuffle,
  },
];

function nextSeed() {
  return Math.floor(Date.now() / 1000);
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-white/10 bg-[#202328] p-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-1 font-mono text-2xl font-bold text-white">{value}</p>
    </div>
  );
}

export default function AdminPage() {
  const [status, setStatus] = useState<DemoStatus | null>(null);
  const [seed, setSeed] = useState<number>(nextSeed());
  const [clearHistory, setClearHistory] = useState(true);
  const [includeAlerts, setIncludeAlerts] = useState(true);
  const [simPaused, setSimPaused] = useState(false);
  const [simSpeed, setSimSpeed] = useState(1);
  const [pendingProfile, setPendingProfile] = useState<DemoProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  const lastResetLabel = useMemo(() => {
    const scenario = scenarios.find((item) => item.profile === status?.profile);
    if (!scenario) return "kein Reset in dieser Sitzung";
    return `${scenario.title} · Seed ${status?.seed ?? "?"}`;
  }, [status?.profile, status?.seed]);

  useEffect(() => {
    getDemoStatus()
      .then(setStatus)
      .catch((err) => setError(err instanceof Error ? err.message : "Status konnte nicht geladen werden"));
  }, []);

  async function applyScenario(profile: DemoProfile) {
    setPendingProfile(profile);
    setError(null);
    try {
      const result = await resetDemoScenario({
        profile,
        seed,
        fh_bin_id: 22,
        clear_history: clearHistory,
        include_alerts: includeAlerts,
        sim_speed: simSpeed,
        sim_paused: simPaused,
      }, process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "changeme");
      setStatus(result);
      setSeed(nextSeed());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Szenario konnte nicht gesetzt werden");
    } finally {
      setPendingProfile(null);
    }
  }

  return (
    <main className="min-h-screen bg-[#151619] text-slate-100">
      <header className="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-[#1e2024] px-5 py-3 shadow-[0_12px_28px_rgba(0,0,0,0.22)]">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-[#f2c94c] text-[#171717]">
            <SlidersHorizontal className="h-5 w-5" />
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#f2c94c]">Admin</p>
            <h1 className="text-lg font-semibold tracking-tight text-white">Demo-Zustand zurücksetzen</h1>
          </div>
        </div>

        <Link
          href="/dashboard"
          className="flex h-10 items-center gap-2 rounded border border-white/10 bg-[#111214] px-3 text-sm font-semibold text-slate-300 transition hover:border-[#f2c94c]/50 hover:text-[#f2c94c]"
        >
          <ArrowLeft className="h-4 w-4" />
          Leitstand
        </Link>
      </header>

      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-5 py-5">
        {error && (
          <div className="rounded border border-red-400/35 bg-red-500/10 px-4 py-3 text-sm font-medium text-red-200">
            {error}
          </div>
        )}

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Abholbereit" value={status?.collectable_bins ?? "–"} />
          <Stat label="Kritisch voll" value={status?.critical_bins ?? "–"} />
          <Stat label="Offene Meldungen" value={status?.open_alerts ?? "–"} />
          <Stat label="FH-Füllstand" value={status?.fh_fill_level != null ? `${status.fh_fill_level}%` : "–"} />
        </section>

        <section className="rounded border border-white/10 bg-[#1a1c20] p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">Szenario wählen</h2>
              <p className="mt-1 text-sm text-slate-400">Letzter Zustand: {lastResetLabel}</p>
            </div>
            {status?.profile && (
              <span className="flex items-center gap-1.5 rounded border border-emerald-400/25 bg-emerald-400/10 px-2.5 py-1.5 text-xs font-semibold text-emerald-300">
                <CheckCircle2 className="h-3.5 w-3.5" />
                gesetzt
              </span>
            )}
          </div>

          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {scenarios.map((scenario) => {
              const Icon = scenario.icon;
              const pending = pendingProfile === scenario.profile;
              return (
                <button
                  key={scenario.profile}
                  type="button"
                  onClick={() => applyScenario(scenario.profile)}
                  disabled={Boolean(pendingProfile)}
                  className="flex min-h-36 flex-col items-start justify-between rounded border border-white/10 bg-[#202328] p-3 text-left transition hover:border-[#f2c94c]/55 hover:bg-[#252930] disabled:cursor-wait disabled:opacity-55"
                >
                  <span className="flex h-9 w-9 items-center justify-center rounded bg-[#f2c94c]/12 text-[#f2c94c]">
                    {pending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                  </span>
                  <span>
                    <span className="block text-sm font-semibold text-white">{scenario.title}</span>
                    <span className="mt-1 block text-xs leading-5 text-slate-400">{scenario.detail}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        <section className="grid gap-3 rounded border border-white/10 bg-[#1a1c20] p-4 md:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Seed</span>
            <input
              type="number"
              value={seed}
              onChange={(event) => setSeed(Number(event.target.value) || nextSeed())}
              className="h-10 rounded border border-white/10 bg-[#202328] px-3 font-mono text-sm text-white outline-none focus:border-[#f2c94c]/70"
            />
          </label>

          <label className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Simulation</span>
            <select
              value={simSpeed}
              onChange={(event) => setSimSpeed(Number(event.target.value))}
              className="h-10 rounded border border-white/10 bg-[#202328] px-3 text-sm text-white outline-none focus:border-[#f2c94c]/70"
            >
              {[1, 5, 10, 20].map((value) => (
                <option key={value} value={value}>{value}× Geschwindigkeit</option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 rounded border border-white/10 bg-[#202328] px-3 py-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={clearHistory}
              onChange={(event) => setClearHistory(event.target.checked)}
              className="h-4 w-4 accent-[#f2c94c]"
            />
            Routen, Meldungen und Befehle löschen
          </label>

          <div className="grid gap-2">
            <label className="flex items-center gap-2 rounded border border-white/10 bg-[#202328] px-3 py-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={includeAlerts}
                onChange={(event) => setIncludeAlerts(event.target.checked)}
                className="h-4 w-4 accent-[#f2c94c]"
              />
              Meldungen im Szenario
            </label>
            <label className="flex items-center gap-2 rounded border border-white/10 bg-[#202328] px-3 py-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={simPaused}
                onChange={(event) => setSimPaused(event.target.checked)}
                className="h-4 w-4 accent-[#f2c94c]"
              />
              Simulation pausiert starten
            </label>
          </div>
        </section>
      </div>
    </main>
  );
}
