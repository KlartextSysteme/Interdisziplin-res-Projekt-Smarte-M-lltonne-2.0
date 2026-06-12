"use client";

import dynamic from "next/dynamic";
import type { Bin, Route, TruckPosition } from "@/types";

// Leaflet depends on window — must load client-side only
const LeafletMap = dynamic(() => import("./LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-[#111214] text-sm text-slate-400">
      Karte wird geladen...
    </div>
  ),
});

interface Props {
  bins: Bin[];
  truck: TruckPosition | null;
  activeRoute: Route | null;
  depot?: { lat: number; lng: number; name: string } | null;
}

export default function MapView(props: Props) {
  return <LeafletMap {...props} />;
}
