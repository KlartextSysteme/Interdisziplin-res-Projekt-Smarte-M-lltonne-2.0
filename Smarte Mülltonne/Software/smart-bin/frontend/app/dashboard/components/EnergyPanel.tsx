"use client";

import { Sun, Zap, Battery } from "lucide-react";
import type { EnergyStatus } from "@/types";

interface Props {
  energyData: EnergyStatus[];
}

function batteryColor(pct: number) {
  if (pct < 20) return "text-red-600";
  if (pct < 50) return "text-amber-600";
  return "text-emerald-600";
}

export default function EnergyPanel({ energyData }: Props) {
  const totalSolar = energyData.reduce((s, e) => s + e.solar_output_w, 0);
  const avgBattery =
    energyData.length > 0
      ? energyData.reduce((s, e) => s + e.battery, 0) / energyData.length
      : 0;

  return (
    <section className="p-4 space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-gradient-to-br from-amber-50 to-amber-100 border border-amber-200 p-3">
          <div className="flex items-center gap-2 text-amber-700 text-xs font-medium mb-1">
            <Sun className="w-4 h-4" />
            Solar gesamt
          </div>
          <div className="text-2xl font-bold text-amber-900">{totalSolar.toFixed(1)} W</div>
        </div>
        <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100 border border-emerald-200 p-3">
          <div className="flex items-center gap-2 text-emerald-700 text-xs font-medium mb-1">
            <Battery className="w-4 h-4" />
            Ø Akkustand
          </div>
          <div className="text-2xl font-bold text-emerald-900">{avgBattery.toFixed(0)} %</div>
        </div>
      </div>

      {/* Per-bin breakdown */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
          Pro Tonne
        </h3>
        {energyData.map((e) => (
          <div
            key={e.bin_id}
            className="rounded-lg border border-slate-200 bg-white p-3 flex items-center justify-between"
          >
            <div>
              <p className="font-medium text-sm text-slate-900">{e.name}</p>
              <p className={`text-xs ${batteryColor(e.battery)}`}>Akku {e.battery} %</p>
            </div>
            <div className="flex items-center gap-1.5 text-sm">
              {e.is_charging && <Zap className="w-4 h-4 text-amber-500" />}
              <span className="font-mono text-slate-700">{e.solar_output_w.toFixed(1)} W</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
