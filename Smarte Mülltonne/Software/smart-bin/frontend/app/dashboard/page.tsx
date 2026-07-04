"use client";

import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import { Route as RouteIcon, Loader2, Gauge, Play, Pause, Radio, MessageSquare, Battery, Inbox, CircleHelp } from "lucide-react";
import { useLiveData } from "@/lib/useWebSocket";
import AlertBanner from "./components/AlertBanner";
import OperatorTour from "./components/OperatorTour";
import FleetPanel from "./components/FleetPanel";
import MapView from "./components/MapView";
import ChatInterface from "./components/ChatInterface";
import EnergyPanel from "./components/EnergyPanel";
import SecurityPanel from "./components/SecurityPanel";
import {
  resolveAlert,
  lockBin,
  planRoute,
  getCandidates,
  activateRoute,
  getLatestRoute,
  getPublicConfig,
  getSimSpeed,
  createBinCommand,
  setSimSpeed,
  setSimPaused,
  type PublicConfig,
  type BinCommandAction,
} from "@/lib/api";
import type { Route } from "@/types";

type Tab = "chat" | "energy" | "security";

export default function DashboardPage() {
  const live = useLiveData();
  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [activeRoute, setActiveRoute] = useState<Route | null>(null);
  const [candidates, setCandidates] = useState<Route[]>([]);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [planning, setPlanning] = useState(false);
  const [simSpeed, setSimSpeedState] = useState<number>(1);
  const [simPaused, setSimPausedState] = useState<boolean>(false);
  const [selectedBinId, setSelectedBinId] = useState<number | null>(null);
  const [tourOpen, setTourOpen] = useState(false);
  const [hardwareCommandPending, setHardwareCommandPending] = useState<{
    binId: number;
    action: BinCommandAction;
  } | null>(null);

  // Load current sim-state once
  useEffect(() => {
    getSimSpeed()
      .then((s) => {
        setSimSpeedState(s.speed);
        setSimPausedState(Boolean(s.paused));
      })
      .catch(() => {});
  }, []);

  async function applySpeed(v: number) {
    setSimSpeedState(v);
    try { await setSimSpeed(v); } catch { /* ignore */ }
  }

  async function togglePause() {
    const next = !simPaused;
    setSimPausedState(next);
    try { await setSimPaused(next); } catch { /* ignore */ }
  }

  // Load public config once
  useEffect(() => {
    getPublicConfig().then(setConfig).catch(() => {});
  }, []);

  // Aktive Route + Vorschläge pollen (3s): so erscheinen Auto-Replan-Trips zügig
  // und abgeschlossene Routen verschwinden schnell.
  useEffect(() => {
    const tick = () => {
      getLatestRoute().then(setActiveRoute).catch(() => {});
      getCandidates().then(setCandidates).catch(() => {});
    };
    tick();
    const id = setInterval(tick, 3_000);
    return () => clearInterval(id);
  }, []);

  const bins = live?.bins ?? [];
  const alerts = live?.alerts ?? [];
  const truck = live?.truck ?? null;

  async function handlePlan() {
    setPlanning(true);
    try {
      const cands = await planRoute();
      setCandidates(cands);
      setActiveRoute(cands.find((c) => c.active) ?? cands[0] ?? null);
    } finally {
      setPlanning(false);
    }
  }

  // Bediener wählt einen Vorschlag → wird die aktive (gefahrene) Route.
  async function handleSelectCandidate(id: number) {
    const chosen = candidates.find((c) => c.id === id);
    if (!chosen || chosen.active) return;
    // Optimistisch umschalten (Karte/Badge reagieren sofort)
    setActiveRoute(chosen);
    setCandidates((prev) => prev.map((c) => ({ ...c, active: c.id === id })));
    try {
      await activateRoute(id);
    } catch {
      // bei Fehler nächster Poll korrigiert den Zustand
    }
  }

  async function handleResolve(eventId: number) {
    await resolveAlert(eventId);
  }

  async function handleLock(binId: number) {
    const token = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "changeme";
    await lockBin(binId, token);
  }

  async function handleHardwareCommand(binId: number, action: BinCommandAction) {
    if (hardwareCommandPending) return;
    setHardwareCommandPending({ binId, action });
    try {
      await createBinCommand(binId, action);
    } finally {
      setHardwareCommandPending(null);
    }
  }

  const energyData = bins.map((b) => ({
    bin_id: b.id,
    name: b.name,
    battery: b.battery,
  }));

  const securityEvents = alerts.map((a) => ({ ...a, resolved: false as const }));

  const tabs: { id: Tab; label: string; icon: ComponentType<{ className?: string }> }[] = [
    { id: "chat", label: "Chat", icon: MessageSquare },
    { id: "energy", label: "Akku", icon: Battery },
    { id: "security", label: alerts.length ? `Meldungen ${alerts.length}` : "Meldungen", icon: Inbox },
  ];

  return (
    <div className="flex h-screen flex-col bg-[#151619] text-slate-100">
      <AlertBanner alerts={alerts} bins={bins} />

      <header
        data-tour="app-shell"
        className="flex min-h-16 flex-wrap items-center justify-between gap-3 border-b border-white/10 bg-[#1e2024] px-5 py-3 shadow-[0_12px_28px_rgba(0,0,0,0.22)]"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded bg-[#f2c94c] text-[#171717] shadow-[0_0_22px_rgba(242,201,76,0.22)]">
            <RouteIcon className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#f2c94c]">Leitstand</p>
            <h1 className="text-lg font-semibold tracking-tight text-white">Smarte Mülltonne 2.0</h1>
          </div>
        </div>

        <div className="flex max-w-full items-center gap-3 overflow-x-auto pb-1 lg:pb-0">
          <div
            data-tour="sim-controls"
            className="flex shrink-0 items-center gap-1 rounded border border-white/10 bg-[#111214] px-2 py-1.5"
          >
            <button
              onClick={togglePause}
              className={`flex h-8 w-8 items-center justify-center rounded transition ${
                simPaused
                  ? "bg-[#f2c94c] text-[#171717] hover:bg-[#ffd866]"
                  : "text-slate-300 hover:bg-white/10 hover:text-white"
              }`}
              title={simPaused ? "Simulation fortsetzen" : "Simulation pausieren"}
              aria-label={simPaused ? "Simulation fortsetzen" : "Simulation pausieren"}
            >
              {simPaused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            </button>
            <span className="mx-1 h-5 w-px bg-white/10" aria-hidden />
            <Gauge className="h-4 w-4 text-[#f2c94c]" />
            {[1, 5, 10, 20].map((v) => (
              <button
                key={v}
                onClick={() => applySpeed(v)}
                disabled={simPaused}
                className={`min-w-9 rounded px-2 py-1 text-xs font-semibold transition ${
                  simSpeed === v && !simPaused
                    ? "bg-[#f2c94c] text-[#171717]"
                    : "text-slate-400 hover:bg-white/10 hover:text-white disabled:opacity-35 disabled:hover:bg-transparent"
                }`}
                title={`Simulation auf ${v}× Geschwindigkeit`}
              >
                {v}×
              </button>
            ))}
          </div>
          {activeRoute && activeRoute.waypoints.length > 0 && (
            <div className="hidden items-center gap-2 rounded border border-white/10 bg-[#111214] px-3 py-2 md:flex">
              <span className="text-xs font-medium text-slate-300">
                Route #{activeRoute.id} · {activeRoute.waypoints.length} Tonnen · {(activeRoute.distance_m / 1000).toFixed(1)} km
                {activeRoute.duration_s ? ` · ${Math.round(activeRoute.duration_s / 60)} min` : ""}
              </span>
              {activeRoute.capacity_units && activeRoute.load_units != null && (() => {
                const cap = activeRoute.capacity_units!;
                const load = activeRoute.load_units!;
                const pct = Math.min(100, Math.round((load / cap) * 100));
                // Volle Tonnen, die nicht mehr in diese Fahrt passten (Schwelle 60 %)
                const fullBins = bins.filter((b) => !b.locked && b.fill_level >= 60).length;
                const skipped = Math.max(0, fullBins - activeRoute.waypoints.length);
                return (
                  <span
                    className="rounded-full bg-[#f2c94c]/15 px-2 py-0.5 text-[11px] font-medium text-[#f2c94c]"
                    title={`Beladung ${load} / ${cap} Einheiten${skipped ? ` · ${skipped} volle Tonnen erst in der nächsten Fahrt` : ""}`}
                  >
                    Auslastung {pct}%{skipped ? ` · +${skipped} übrig` : ""}
                  </span>
                );
              })()}
              {activeRoute.nn_distance_m && activeRoute.optimized_distance_m && activeRoute.nn_distance_m > activeRoute.optimized_distance_m && (() => {
                const nn = activeRoute.nn_distance_m!;
                const opt = activeRoute.optimized_distance_m!;
                const exact = activeRoute.exact_distance_m;
                const savedPct = Math.round((1 - opt / nn) * 100);
                const gapPct = exact ? ((opt / exact - 1) * 100) : null;
                const isOptimal = gapPct !== null && gapPct < 0.5;
                const tooltip = [
                  `NN-Baseline:  ${(nn / 1000).toFixed(2)} km`,
                  `2-opt:        ${(opt / 1000).toFixed(2)} km  (−${savedPct}%)`,
                  exact !== null
                    ? `Held-Karp:    ${(exact / 1000).toFixed(2)} km${isOptimal ? "  (= 2-opt ✓)" : `  (gap: +${gapPct!.toFixed(1)}%)`}`
                    : `Held-Karp:    n>15 → DP übersprungen`,
                ].join("\n");
                return (
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${
                      isOptimal
                        ? "bg-emerald-400/15 text-emerald-300"
                        : exact !== null
                          ? "bg-[#f2c94c]/15 text-[#f2c94c]"
                          : "bg-emerald-400/15 text-emerald-300"
                    }`}
                    title={tooltip}
                  >
                    2-opt: −{savedPct}%{isOptimal ? " ✓ optimal" : exact !== null ? ` (+${gapPct!.toFixed(1)}%)` : ""}
                  </span>
                );
              })()}
            </div>
          )}
          {candidates.filter((c) => c.waypoints.length > 0).length > 1 && (
            <div className="hidden items-center gap-1 rounded border border-white/10 bg-[#111214] px-1.5 py-1 lg:flex" title="Vorschlag wählen — wird gefahren">
              {candidates
                .filter((c) => c.waypoints.length > 0)
                .map((c) => {
                  const isActive = c.id === activeRoute?.id;
                  return (
                    <button
                      key={c.id}
                      onClick={() => handleSelectCandidate(c.id)}
                      className={`flex flex-col items-start rounded px-2 py-1 text-left text-[11px] leading-tight transition ${
                        isActive
                          ? "bg-[#f2c94c] text-[#171717]"
                          : "text-slate-400 hover:bg-white/10 hover:text-white"
                      }`}
                      title={`${c.variant_label ?? "Route"} · ${c.waypoints.length} Tonnen · ${(c.distance_m / 1000).toFixed(1)} km`}
                    >
                      <span className="font-semibold">
                        {c.variant_label ?? "Route"}{c.is_default ? " ★" : ""}
                      </span>
                      <span className={isActive ? "text-[#171717]/70" : "text-slate-500"}>
                        {(c.distance_m / 1000).toFixed(1)} km · {c.waypoints.length}
                      </span>
                    </button>
                  );
              })}
            </div>
          )}
          <button
            onClick={() => setTourOpen(true)}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded border border-white/10 bg-[#111214] text-slate-300 transition hover:border-[#f2c94c]/50 hover:text-[#f2c94c] sm:w-auto sm:px-3"
            title="Einführung öffnen"
            aria-label="Einführung öffnen"
          >
            <CircleHelp className="h-4 w-4" />
            <span className="hidden text-xs font-semibold sm:ml-2 sm:inline">Einführung</span>
          </button>
          <button
            data-tour="route-plan"
            onClick={handlePlan}
            disabled={planning}
            className="flex h-10 w-10 shrink-0 items-center justify-center gap-2 rounded bg-[#f2c94c] text-sm font-semibold text-[#171717] transition hover:bg-[#ffd866] disabled:bg-slate-600 disabled:text-slate-300 sm:w-auto sm:px-4"
            title="Route planen"
          >
            {planning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RouteIcon className="w-4 h-4" />}
            <span className="hidden sm:inline">Route planen</span>
          </button>
          <span
            data-tour="live-status"
            className={`hidden items-center gap-1.5 rounded border px-2.5 py-1.5 text-xs font-semibold sm:flex ${
              live ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300" : "border-white/10 bg-white/5 text-slate-400"
            }`}
          >
            <Radio className="h-3.5 w-3.5" />
            {live ? "Live" : "Verbinde..."}
          </span>
        </div>
      </header>

      <div className="flex flex-1 flex-col overflow-auto lg:flex-row lg:overflow-hidden">
        <div
          data-tour="fleet-panel"
          className="h-64 w-full shrink-0 overflow-y-auto border-b border-white/10 bg-[#1a1c20] lg:h-auto lg:w-[19rem] lg:border-r lg:border-b-0"
        >
          <FleetPanel
            bins={[...bins].sort((a, b) => b.fill_level - a.fill_level)}
            alerts={alerts}
            selectedBinId={selectedBinId}
            onSelectBin={setSelectedBinId}
            onHardwareCommand={handleHardwareCommand}
            hardwareCommandPending={hardwareCommandPending}
          />
        </div>

        <div
          data-tour="map"
          className="relative h-[28rem] shrink-0 bg-[#111214] lg:h-auto lg:flex-1 lg:shrink"
        >
          <MapView
            bins={bins}
            truck={truck}
            activeRoute={activeRoute}
            candidates={candidates}
            activeRouteId={activeRoute?.id ?? null}
            onSelectCandidate={handleSelectCandidate}
            depot={config?.depot ?? null}
            selectedBinId={selectedBinId}
            onSelectBin={setSelectedBinId}
            alerts={alerts}
          />
        </div>

        <div className="flex min-h-[36rem] w-full shrink-0 flex-col border-t border-white/10 bg-[#1a1c20] lg:min-h-0 lg:w-[25rem] lg:border-t-0 lg:border-l">
          <div data-tour="side-tabs" className="grid grid-cols-3 gap-1 border-b border-white/10 bg-[#151619] p-2">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex h-10 items-center justify-center gap-2 rounded text-xs font-semibold transition-colors ${
                  activeTab === tab.id
                    ? "bg-[#f2c94c] text-[#171717]"
                    : "text-slate-400 hover:bg-white/10 hover:text-white"
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
              );
            })}
          </div>

          <div className="flex-1 overflow-y-auto">
            {activeTab === "chat" && <ChatInterface onActionComplete={() => getLatestRoute().then(setActiveRoute)} />}
            {activeTab === "energy" && <EnergyPanel energyData={energyData} />}
            {activeTab === "security" && (
              <SecurityPanel events={securityEvents} onResolve={handleResolve} onLock={handleLock} />
            )}
          </div>
        </div>
      </div>

      <OperatorTour open={tourOpen} onOpenChange={setTourOpen} />
    </div>
  );
}
