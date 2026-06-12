"use client";

import { Battery, BatteryLow } from "lucide-react";
import type { EnergyStatus } from "@/types";

interface Props {
  energyData: EnergyStatus[];
}

function batteryColor(pct: number) {
  if (pct < 20) return "text-red-400";
  if (pct < 50) return "text-[#f2c94c]";
  return "text-emerald-300";
}

export default function EnergyPanel({ energyData }: Props) {
  const avgBattery =
    energyData.length > 0
      ? energyData.reduce((s, e) => s + e.battery, 0) / energyData.length
      : 0;
  const lowBatteryCount = energyData.filter((e) => e.battery < 20).length;

  return (
    <section className="space-y-4 p-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded border border-emerald-400/20 bg-emerald-400/10 p-3">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-emerald-300">
            <Battery className="h-4 w-4" />
            Ø Akkustand
          </div>
          <div className="font-mono text-2xl font-bold text-white">{avgBattery.toFixed(0)} %</div>
        </div>
        <div className="rounded border border-red-400/25 bg-red-500/10 p-3">
          <div className="mb-1 flex items-center gap-2 text-xs font-medium text-red-300">
            <BatteryLow className="h-4 w-4" />
            Kritisch
          </div>
          <div className="font-mono text-2xl font-bold text-white">{lowBatteryCount}</div>
        </div>
      </div>

      <div className="space-y-2">
        <h3 className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">
          Pro Tonne
        </h3>
        {energyData.map((e) => (
          <div
            key={e.bin_id}
            className="flex items-center justify-between rounded border border-white/10 bg-[#202328] p-3"
          >
            <div>
              <p className="text-sm font-medium text-white">{e.name}</p>
              <p className={`text-xs ${batteryColor(e.battery)}`}>Akku {e.battery} %</p>
            </div>
            <span className={`font-mono text-sm ${batteryColor(e.battery)}`}>{e.battery} %</span>
          </div>
        ))}
      </div>
    </section>
  );
}
