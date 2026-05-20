"use client";

import { Battery, BatteryLow, Sun, Lock, Trash2 } from "lucide-react";
import type { Bin } from "@/types";

interface Props {
  bins: Bin[];
}

function fillColor(pct: number) {
  if (pct >= 80) return "bg-red-500";
  if (pct >= 50) return "bg-amber-500";
  return "bg-emerald-500";
}

function batteryIcon(pct: number) {
  return pct < 20 ? (
    <BatteryLow className="w-3.5 h-3.5 text-red-500" />
  ) : (
    <Battery className="w-3.5 h-3.5 text-slate-500" />
  );
}

export default function FleetPanel({ bins }: Props) {
  return (
    <aside className="flex flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <Trash2 className="w-4 h-4 text-slate-600" />
        <h2 className="font-semibold text-sm uppercase tracking-wider text-slate-600">
          Flotte · {bins.length}
        </h2>
      </div>

      {bins.map((b) => (
        <div
          key={b.id}
          className={`rounded-xl border bg-white p-3 shadow-sm transition hover:shadow-md ${
            b.locked ? "border-red-300 ring-1 ring-red-200" : "border-slate-200"
          }`}
        >
          <div className="flex items-start justify-between mb-2 gap-2">
            <div className="min-w-0">
              <p className="font-semibold text-sm text-slate-900 truncate">{b.name}</p>
              <p className="text-xs text-slate-500 truncate">{b.address}</p>
            </div>
            {b.locked && <Lock className="w-3.5 h-3.5 text-red-500 shrink-0 mt-0.5" />}
          </div>

          {/* Fill-level progress bar */}
          <div className="mb-2">
            <div className="flex justify-between text-xs text-slate-500 mb-1">
              <span>Füllstand</span>
              <span className="font-medium text-slate-900">{b.fill_level}%</span>
            </div>
            <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div
                className={`h-full ${fillColor(b.fill_level)} transition-all`}
                style={{ width: `${b.fill_level}%` }}
              />
            </div>
          </div>

          {/* Battery + Solar row */}
          <div className="flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center gap-1">
              {batteryIcon(b.battery)}
              <span>{b.battery}%</span>
            </div>
            <div className="flex items-center gap-1">
              <Sun
                className={`w-3.5 h-3.5 ${b.is_charging ? "text-amber-500" : "text-slate-300"}`}
              />
              <span>{b.solar_output_w.toFixed(1)} W</span>
            </div>
          </div>
        </div>
      ))}
    </aside>
  );
}
