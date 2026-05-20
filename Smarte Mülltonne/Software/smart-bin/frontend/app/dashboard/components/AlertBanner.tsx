"use client";

import { AlertTriangle } from "lucide-react";
import type { LiveData } from "@/types";

interface Props {
  alerts: LiveData["alerts"];
  bins: LiveData["bins"];
}

export default function AlertBanner({ alerts, bins }: Props) {
  if (alerts.length === 0) return null;

  const binName = (id: number) => bins.find((b) => b.id === id)?.name ?? `Tonne ${id}`;
  const latest = alerts[alerts.length - 1];

  return (
    <div className="flex items-center gap-3 px-6 py-2.5 bg-gradient-to-r from-red-600 to-red-700 text-white text-sm shadow-md">
      <AlertTriangle className="w-4 h-4 shrink-0 animate-pulse" />
      <span className="font-medium">
        {alerts.length > 1 && `${alerts.length} Alerts · `}
        {binName(latest.bin_id)}: {latest.event_type}
      </span>
      <span className="text-red-100 text-xs ml-auto">
        {new Date(latest.timestamp).toLocaleTimeString("de-DE")}
      </span>
    </div>
  );
}
