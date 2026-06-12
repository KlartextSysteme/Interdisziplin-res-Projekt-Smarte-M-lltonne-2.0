"use client";

import { AlertTriangle } from "lucide-react";
import { securityEventLabel } from "@/lib/labels";
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
    <div className="flex items-center gap-3 border-b border-red-400/30 bg-red-500/15 px-5 py-2.5 text-sm text-red-100">
      <AlertTriangle className="h-4 w-4 shrink-0 animate-pulse text-red-300" />
      <span className="font-medium">
        {alerts.length > 1 && `${alerts.length} Meldungen · `}
        {binName(latest.bin_id)}: {securityEventLabel(latest.event_type)}
      </span>
      <span className="ml-auto text-xs text-red-200">
        {new Date(latest.timestamp).toLocaleTimeString("de-DE")}
      </span>
    </div>
  );
}
