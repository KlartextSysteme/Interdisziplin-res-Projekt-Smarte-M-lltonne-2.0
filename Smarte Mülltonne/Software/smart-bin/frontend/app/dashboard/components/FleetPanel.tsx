"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Battery,
  BatteryLow,
  Home,
  Loader2,
  Lock,
  LockOpen,
  MapPin,
  Plus,
  Sparkles,
  Square,
  Trash2,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { binLocationLabel, binStatusLabel, eventTone, securityEventLabel } from "@/lib/labels";
import type { BinCommandAction } from "@/lib/api";
import type { Bin, LiveData } from "@/types";
import PairingModal from "./PairingModal";

interface Props {
  bins: Bin[];
  alerts?: LiveData["alerts"];
  selectedBinId?: number | null;
  onSelectBin?: (id: number | null) => void;
  onHardwareCommand?: (binId: number, action: BinCommandAction) => void | Promise<void>;
  hardwareCommandPending?: { binId: number; action: BinCommandAction } | null;
  onLock?: (binId: number) => void | Promise<void>;
  onUnlock?: (binId: number) => void | Promise<void>;
}

function fillColor(pct: number) {
  if (pct >= 80) return "bg-red-500";
  if (pct >= 50) return "bg-[#f2c94c]";
  return "bg-emerald-500";
}

function batteryIcon(pct: number) {
  return pct < 20 ? (
    <BatteryLow className="h-3.5 w-3.5 text-red-400" />
  ) : (
    <Battery className="h-3.5 w-3.5 text-slate-400" />
  );
}

function locationIcon(locationState?: string | null) {
  const src =
    locationState === "truck" || locationState === "moving_to_pickup"
      ? "/icons/status-truck.svg"
      : "/icons/status-home.svg";
  return <img src={src} alt="" className="h-3.5 w-3.5 object-contain" />;
}

function reportIcon(eventType: string) {
  if (eventType === "damage_report") return <Wrench className="h-3 w-3" />;
  if (eventType === "hygiene_report") return <Sparkles className="h-3 w-3" />;
  return <AlertTriangle className="h-3 w-3" />;
}

export default function FleetPanel({
  bins,
  alerts = [],
  selectedBinId,
  onSelectBin,
  onHardwareCommand,
  hardwareCommandPending,
  onLock,
  onUnlock,
}: Props) {
  const [pairingOpen, setPairingOpen] = useState(false);

  // Refs auf die Flotten-Kacheln (nach Bin-ID), damit eine von aussen (z.B.
  // per Klick auf die Karte) getroffene Auswahl im Panel sichtbar wird.
  const itemRefs = useRef<Map<number, HTMLDivElement | null>>(new Map());

  useEffect(() => {
    if (selectedBinId == null) return;
    const el = itemRefs.current.get(selectedBinId);
    el?.scrollIntoView({ behavior: "auto", block: "nearest" });
  }, [selectedBinId]);

  const hardwareActions: { action: BinCommandAction; label: string; icon: LucideIcon }[] = [
    { action: "goto_street", label: "Abholung", icon: MapPin },
    { action: "return_home", label: "Heim", icon: Home },
    { action: "stop", label: "Stopp", icon: Square },
  ];

  return (
    <>
      <aside className="flex flex-col gap-3 p-4">
        {/* Header mit Pairing-Button */}
        <div className="flex items-center gap-2">
          <Trash2 className="h-4 w-4 text-[#f2c94c]" />
          <h2 className="flex-1 text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
            Flotte · {bins.length}
          </h2>
          <button
            onClick={() => setPairingOpen(true)}
            title="Neue Tonne verbinden"
            className="flex items-center gap-1 rounded border border-[#f2c94c]/30 bg-[#f2c94c]/10 px-2 py-1 text-[10px] font-semibold text-[#f2c94c] transition hover:bg-[#f2c94c]/20"
          >
            <Plus className="h-3 w-3" />
            Verbinden
          </button>
        </div>

        {bins.map((b) => {
          const binAlerts = alerts.filter((a) => a.bin_id === b.id);
          const latestAlert = binAlerts[binAlerts.length - 1];
          const tone = latestAlert ? eventTone(latestAlert.event_type) : null;
          const isSelected = selectedBinId === b.id;

          return (
            <div
              key={b.id}
              ref={(el) => {
                itemRefs.current.set(b.id, el);
              }}
              role="button"
              tabIndex={0}
              onClick={() => onSelectBin?.(isSelected ? null : b.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelectBin?.(isSelected ? null : b.id);
              }}
              className={`cursor-pointer rounded border p-3 transition hover:bg-white/[0.055] focus:outline-none focus:ring-1 focus:ring-[#f2c94c]/50 ${
                isSelected
                  ? "border-[#f2c94c]/70 bg-[#f2c94c]/10 ring-1 ring-[#f2c94c]/30"
                  : b.locked
                    ? "border-red-400/50 bg-red-500/10"
                    : latestAlert
                      ? tone === "amber"
                        ? "border-[#f2c94c]/45 bg-[#f2c94c]/10"
                        : "border-red-400/50 bg-red-500/10"
                      : "border-white/10 bg-[#202328]"
              }`}
            >
              <div className="mb-3 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">{b.name}</p>
                  <p className="truncate text-xs text-slate-400">{b.address}</p>
                </div>
                {b.locked ? (
                  <Lock className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
                ) : (
                  <span className="rounded bg-emerald-400/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-emerald-300">
                    aktiv
                  </span>
                )}
              </div>

              <div className="mb-2">
                <div className="mb-1 flex justify-between text-xs text-slate-400">
                  <span>Füllstand</span>
                  <span className="font-mono font-semibold text-white">{b.fill_level}%</span>
                </div>
                <div className="h-2.5 overflow-hidden rounded-full bg-black/35">
                  <div
                    className={`h-full ${fillColor(b.fill_level)} transition-all`}
                    style={{ width: `${b.fill_level}%` }}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-1">
                  {batteryIcon(b.battery)}
                  <span>Akku {b.battery}%</span>
                </div>
                <span className="rounded bg-white/5 px-2 py-0.5 text-slate-300">
                  {binStatusLabel(b.status, b.locked)}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap items-center gap-1.5 text-[11px]">
                <span className="flex items-center gap-1 rounded bg-white/5 px-2 py-0.5 text-slate-300">
                  {locationIcon(b.location_state)}
                  {binLocationLabel(b.location_state)}
                </span>
                {latestAlert && (
                  <span
                    className={`flex items-center gap-1 rounded px-2 py-0.5 font-medium ${
                      tone === "amber"
                        ? "bg-[#f2c94c]/15 text-[#f2c94c]"
                        : "bg-red-400/15 text-red-300"
                    }`}
                  >
                    {reportIcon(latestAlert.event_type)}
                    {securityEventLabel(latestAlert.event_type)}
                  </span>
                )}
              </div>

              {isSelected && (onHardwareCommand || onLock || onUnlock) && (
                <div className="mt-3 border-t border-white/10 pt-3">
                  {onHardwareCommand && (
                    <div data-tour="hardware-actions" className="grid grid-cols-3 gap-1.5">
                      {hardwareActions.map(({ action, label, icon: Icon }) => {
                        const isPending =
                          hardwareCommandPending?.binId === b.id &&
                          hardwareCommandPending.action === action;
                        // Fahrbefehle sind bei gesperrter Tonne blockiert (Backend lehnt
                        // sie mit 409 ab); Stopp bleibt erlaubt.
                        const isDrive = action === "goto_street" || action === "return_home";
                        const blocked = Boolean(b.locked) && isDrive;
                        return (
                          <button
                            key={action}
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              onHardwareCommand(b.id, action);
                            }}
                            disabled={Boolean(hardwareCommandPending) || blocked}
                            title={blocked ? "Tonne gesperrt – erst entsperren" : `Hardware-Befehl: ${label}`}
                            className="flex min-h-8 items-center justify-center gap-1 rounded border border-white/10 bg-[#111214] px-2 text-[11px] font-semibold text-slate-300 transition hover:border-[#f2c94c]/50 hover:text-[#f2c94c] disabled:cursor-not-allowed disabled:opacity-45"
                          >
                            {isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Icon className="h-3.5 w-3.5" />}
                            <span className="truncate">{label}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {(onLock || onUnlock) && (
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        if (b.locked) onUnlock?.(b.id);
                        else onLock?.(b.id);
                      }}
                      title={b.locked ? "Tonne entsperren (Admin)" : "Tonne sperren (Sicherheit)"}
                      className={`mt-1.5 flex min-h-8 w-full items-center justify-center gap-1.5 rounded border px-2 text-[11px] font-semibold transition ${
                        b.locked
                          ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20"
                          : "border-red-400/40 bg-red-500/10 text-red-300 hover:bg-red-500/20"
                      }`}
                    >
                      {b.locked ? <LockOpen className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
                      <span className="truncate">{b.locked ? "Entsperren" : "Sperren"}</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </aside>

      {pairingOpen && <PairingModal onClose={() => setPairingOpen(false)} />}
    </>
  );
}
