"use client";

import { ShieldCheck, AlertTriangle, Lock, Check } from "lucide-react";
import type { SecurityEvent } from "@/types";

interface Props {
  events: SecurityEvent[];
  onResolve: (binId: number) => void;
  onLock: (binId: number) => void;
}

export default function SecurityPanel({ events, onResolve, onLock }: Props) {
  if (events.length === 0) {
    return (
      <div className="p-8 flex flex-col items-center justify-center text-center gap-2">
        <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center">
          <ShieldCheck className="w-6 h-6 text-emerald-600" />
        </div>
        <p className="font-medium text-slate-900">Alles in Ordnung</p>
        <p className="text-sm text-slate-500">Keine offenen Sicherheitsereignisse.</p>
      </div>
    );
  }

  return (
    <section className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-red-600" />
        <h3 className="font-semibold text-red-600 text-sm uppercase tracking-wider">
          {events.length} offene{events.length !== 1 ? "" : "s"} Ereignis{events.length !== 1 ? "se" : ""}
        </h3>
      </div>

      {events.map((e) => (
        <div
          key={e.id}
          className="rounded-xl border border-red-200 bg-red-50 p-3 space-y-2 shadow-sm"
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="font-semibold text-sm text-red-900">Tonne {e.bin_id}</p>
              <p className="text-xs text-red-700">{e.event_type}</p>
              <p className="text-xs text-slate-500 mt-1">
                {new Date(e.timestamp).toLocaleString("de-DE")}
              </p>
            </div>
            <AlertTriangle className="w-5 h-5 text-red-500 shrink-0" />
          </div>

          <div className="flex gap-2 pt-1">
            <button
              onClick={() => onLock(e.bin_id)}
              className="flex items-center gap-1 rounded-lg bg-red-600 hover:bg-red-700 text-white px-2.5 py-1 text-xs font-medium transition"
            >
              <Lock className="w-3 h-3" /> Sperren
            </button>
            <button
              onClick={() => onResolve(e.bin_id)}
              className="flex items-center gap-1 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 px-2.5 py-1 text-xs font-medium transition"
            >
              <Check className="w-3 h-3" /> Quittieren
            </button>
          </div>
        </div>
      ))}
    </section>
  );
}
