"use client";

import dynamic from "next/dynamic";
import type { Bin, Route, TruckPosition } from "@/types";

// Leaflet depends on window — must load client-side only
const LeafletMap = dynamic(() => import("./LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center bg-slate-100 text-slate-500 text-sm">
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
