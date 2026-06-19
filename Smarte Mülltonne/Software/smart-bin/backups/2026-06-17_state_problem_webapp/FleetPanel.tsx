"use client";

import { Battery, BatteryLow, Lock, Trash2 } from "lucide-react";
import { binStatusLabel } from "@/lib/labels";
import type { Bin } from "@/types";

interface Props {
  bins: Bin[];
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

export default function FleetPanel({ bins }: Props) {
  return (
    <aside className="flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <Trash2 className="h-4 w-4 text-[#f2c94c]" />
        <h2 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
          Flotte · {bins.length}
        </h2>
      </div>

      {bins.map((b) => (
        <div
          key={b.id}
          className={`rounded border p-3 transition hover:bg-white/[0.055] ${
            b.locked ? "border-red-400/50 bg-red-500/10" : "border-white/10 bg-[#202328]"
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
        </div>
      ))}
    </aside>
  );
}
