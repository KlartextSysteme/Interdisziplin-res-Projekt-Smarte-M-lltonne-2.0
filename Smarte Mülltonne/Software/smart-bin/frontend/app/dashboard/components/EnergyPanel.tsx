"use client";

import { Battery, BatteryLow } from "lucide-react";
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
  const avgBattery =
    energyData.length > 0
      ? energyData.reduce((s, e) => s + e.battery, 0) / energyData.length
      : 0;
  const lowBatteryCount = energyData.filter((e) => e.battery < 20).length;

  return (
    <section className="p-4 space-y-4">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100 border border-emerald-200 p-3">
          <div className="flex items-center gap-2 text-emerald-700 text-xs font-medium mb-1">
            <Battery className="w-4 h-4" />
            Ø Akkustand
          </div>
          <div className="text-2xl font-bold text-emerald-900">{avgBattery.toFixed(0)} %</div>
        </div>
        <div className="rounded-xl bg-gradient-to-br from-red-50 to-red-100 border border-red-200 p-3">
          <div className="flex items-center gap-2 text-red-700 text-xs font-medium mb-1">
            <BatteryLow className="w-4 h-4" />
            Kritisch
          </div>
          <div className="text-2xl font-bold text-red-900">{lowBatteryCount}</div>
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
            <span className={`font-mono text-sm ${batteryColor(e.battery)}`}>{e.battery} %</span>
          </div>
        ))}
      </div>
    </section>
  );
}
