"use client";

import { AlertTriangle } from "lucide-react";
import { eventTone, securityEventLabel } from "@/lib/labels";
import type { LiveData } from "@/types";

interface Props {
  alerts: LiveData["alerts"];
  bins: LiveData["bins"];
}

export default function AlertBanner({ alerts, bins }: Props) {
  if (alerts.length === 0) return null;

  const binName = (id: number) => bins.find((b) => b.id === id)?.name ?? `Tonne ${id}`;
  const latest = alerts[alerts.length - 1];
  const tone = eventTone(latest.event_type);
  const isAmber = tone === "amber";

  return (
    <div
      className={`flex items-center gap-3 border-b px-5 py-2.5 text-sm ${
        isAmber
          ? "border-[#f2c94c]/30 bg-[#f2c94c]/15 text-[#fff0b8]"
          : "border-red-400/30 bg-red-500/15 text-red-100"
      }`}
    >
      <AlertTriangle
        className={`h-4 w-4 shrink-0 animate-pulse ${isAmber ? "text-[#f2c94c]" : "text-red-300"}`}
      />
      <span className="font-medium">
        {alerts.length > 1 && `${alerts.length} Meldungen · `}
        {binName(latest.bin_id)}: {securityEventLabel(latest.event_type)}
      </span>
      <span className={`ml-auto text-xs ${isAmber ? "text-[#f8dda0]" : "text-red-200"}`}>
        {new Date(latest.timestamp).toLocaleTimeString("de-DE")}
      </span>
    </div>
  );
}
