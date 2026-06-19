"use client";

import { ShieldCheck, AlertTriangle, Lock, Check, Sparkles, Wrench } from "lucide-react";
import { eventTone, securityEventLabel } from "@/lib/labels";
import type { SecurityEvent } from "@/types";

interface Props {
  events: SecurityEvent[];
  onResolve: (binId: number) => void;
  onLock: (binId: number) => void;
}

export default function SecurityPanel({ events, onResolve, onLock }: Props) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 p-8 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded border border-emerald-400/25 bg-emerald-400/10">
          <ShieldCheck className="h-6 w-6 text-emerald-300" />
        </div>
        <p className="font-medium text-white">Alles in Ordnung</p>
        <p className="text-sm text-slate-400">Keine offenen Meldungen.</p>
      </div>
    );
  }

  return (
    <section className="space-y-3 p-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-[#f2c94c]" />
        <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-[#f2c94c]">
          {events.length} offene Meldung{events.length !== 1 ? "en" : ""}
        </h3>
      </div>

      {events.map((e) => {
        const tone = eventTone(e.event_type);
        const isAmber = tone === "amber";
        const Icon = e.event_type === "damage_report"
          ? Wrench
          : e.event_type === "hygiene_report"
            ? Sparkles
            : AlertTriangle;

        return (
          <div
            key={e.id}
            className={`space-y-3 rounded border p-3 ${
              isAmber
                ? "border-[#f2c94c]/35 bg-[#f2c94c]/10"
                : "border-red-400/35 bg-red-500/10"
            }`}
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm font-semibold text-white">Tonne {e.bin_id}</p>
                <p className={`text-xs ${isAmber ? "text-[#f2c94c]" : "text-red-300"}`}>
                  {securityEventLabel(e.event_type)}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {new Date(e.timestamp).toLocaleString("de-DE")}
                </p>
              </div>
              <Icon className={`h-5 w-5 shrink-0 ${isAmber ? "text-[#f2c94c]" : "text-red-400"}`} />
            </div>

            <div className="flex gap-2">
              {!isAmber && (
                <button
                  onClick={() => onLock(e.bin_id)}
                  className="flex h-8 items-center gap-1 rounded bg-red-500 px-2.5 text-xs font-semibold text-white transition hover:bg-red-400"
                >
                  <Lock className="h-3 w-3" /> Sperren
                </button>
              )}
              <button
                onClick={() => onResolve(e.bin_id)}
                className="flex h-8 items-center gap-1 rounded border border-white/10 bg-white/[0.055] px-2.5 text-xs font-semibold text-slate-200 transition hover:border-[#f2c94c]/40 hover:text-[#f2c94c]"
              >
                <Check className="h-3 w-3" /> Quittieren
              </button>
            </div>
          </div>
        );
      })}
    </section>
  );
}
