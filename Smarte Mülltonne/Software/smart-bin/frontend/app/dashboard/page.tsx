"use client";

import { useEffect, useState } from "react";
import { Route as RouteIcon, Loader2, Gauge, Play, Pause } from "lucide-react";
import { useLiveData } from "@/lib/useWebSocket";
import AlertBanner from "./components/AlertBanner";
import FleetPanel from "./components/FleetPanel";
import MapView from "./components/MapView";
import ChatInterface from "./components/ChatInterface";
import EnergyPanel from "./components/EnergyPanel";
import SecurityPanel from "./components/SecurityPanel";
import {
  resolveAlerts,
  lockBin,
  planRoute,
  getLatestRoute,
  getPublicConfig,
  getSimSpeed,
  setSimSpeed,
  setSimPaused,
  type PublicConfig,
} from "@/lib/api";
import type { Route } from "@/types";

type Tab = "chat" | "energy" | "security";

export default function DashboardPage() {
  const live = useLiveData();
  const [activeTab, setActiveTab] = useState<Tab>("chat");
  const [activeRoute, setActiveRoute] = useState<Route | null>(null);
  const [config, setConfig] = useState<PublicConfig | null>(null);
  const [planning, setPlanning] = useState(false);
  const [simSpeed, setSimSpeedState] = useState<number>(1);
  const [simPaused, setSimPausedState] = useState<boolean>(false);

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

  // Fetch latest route on mount and every 10s (lightweight polling)
  useEffect(() => {
    const fetchRoute = () => getLatestRoute().then(setActiveRoute).catch(() => {});
    fetchRoute();
    const id = setInterval(fetchRoute, 10_000);
    return () => clearInterval(id);
  }, []);

  const bins = live?.bins ?? [];
  const alerts = live?.alerts ?? [];
  const truck = live?.truck ?? null;

  async function handlePlan() {
    setPlanning(true);
    try {
      const route = await planRoute();
      setActiveRoute(route);
    } finally {
      setPlanning(false);
    }
  }

  async function handleResolve(binId: number) {
    await resolveAlerts(binId);
  }

  async function handleLock(binId: number) {
    const token = process.env.NEXT_PUBLIC_ADMIN_TOKEN ?? "changeme";
    await lockBin(binId, token);
  }

  const energyData = bins.map((b) => ({
    bin_id: b.id,
    name: b.name,
    battery: b.battery,
    solar_output_w: b.solar_output_w,
    is_charging: b.is_charging,
  }));

  const securityEvents = alerts.map((a) => ({ ...a, resolved: false as const }));

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <AlertBanner alerts={alerts} bins={bins} />

      <header className="flex items-center justify-between px-6 py-3 bg-white border-b shadow-sm">
        <h1 className="text-xl font-bold tracking-tight">Smarte Mülltonne 2.0</h1>
        <div className="flex items-center gap-3">
          {/* Sim-Controls: Play/Pause + Speed-Regler */}
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg px-2 py-1">
            <button
              onClick={togglePause}
              className={`flex items-center justify-center w-6 h-6 rounded transition ${
                simPaused
                  ? "bg-amber-500 text-white hover:bg-amber-600"
                  : "text-slate-600 hover:bg-slate-200"
              }`}
              title={simPaused ? "Simulation fortsetzen" : "Simulation pausieren"}
              aria-label={simPaused ? "Simulation fortsetzen" : "Simulation pausieren"}
            >
              {simPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            </button>
            <span className="w-px h-4 bg-slate-300 mx-1" aria-hidden />
            <Gauge className="w-3.5 h-3.5 text-slate-500" />
            <span className="text-xs text-slate-500 mr-1">Sim</span>
            {[1, 5, 10, 20].map((v) => (
              <button
                key={v}
                onClick={() => applySpeed(v)}
                disabled={simPaused}
                className={`text-xs font-mono px-2 py-0.5 rounded transition ${
                  simSpeed === v && !simPaused
                    ? "bg-blue-600 text-white"
                    : "text-slate-600 hover:bg-slate-200 disabled:opacity-40 disabled:hover:bg-transparent"
                }`}
                title={`Simulation auf ${v}× Geschwindigkeit`}
              >
                {v}×
              </button>
            ))}
          </div>
          {activeRoute && activeRoute.waypoints.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">
                Route #{activeRoute.id} · {(activeRoute.distance_m / 1000).toFixed(1)} km
                {activeRoute.duration_s ? ` · ${Math.round(activeRoute.duration_s / 60)} min` : ""}
              </span>
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
                        ? "bg-emerald-100 text-emerald-700"
                        : exact !== null
                          ? "bg-amber-100 text-amber-700"
                          : "bg-emerald-100 text-emerald-700"
                    }`}
                    title={tooltip}
                  >
                    2-opt: −{savedPct}%{isOptimal ? " ✓ optimal" : exact !== null ? ` (+${gapPct!.toFixed(1)}%)` : ""}
                  </span>
                );
              })()}
            </div>
          )}
          <button
            onClick={handlePlan}
            disabled={planning}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 text-white px-3 py-1.5 text-sm font-medium transition"
          >
            {planning ? <Loader2 className="w-4 h-4 animate-spin" /> : <RouteIcon className="w-4 h-4" />}
            Route planen
          </button>
          <span
            className={`text-xs px-2 py-1 rounded-full ${
              live ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-500"
            }`}
          >
            {live ? "Live" : "Verbinde..."}
          </span>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-72 border-r bg-white overflow-y-auto shrink-0">
          <FleetPanel bins={[...bins].sort((a, b) => b.fill_level - a.fill_level)} />
        </div>

        <div className="flex-1 relative">
          <MapView bins={bins} truck={truck} activeRoute={activeRoute} depot={config?.depot ?? null} />
        </div>

        <div className="w-96 border-l bg-white flex flex-col shrink-0">
          <div className="flex border-b">
            {(["chat", "energy", "security"] as Tab[]).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 text-sm font-medium capitalize transition-colors ${
                  activeTab === tab
                    ? "border-b-2 border-blue-600 text-blue-600"
                    : "text-slate-500 hover:text-slate-700"
                }`}
              >
                {tab === "chat"
                  ? "Chat"
                  : tab === "energy"
                  ? "Energie"
                  : `Sicherheit${alerts.length ? ` (${alerts.length})` : ""}`}
              </button>
            ))}
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
    </div>
  );
}
