"use client";

import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { Bin, Route, TruckPosition } from "@/types";

// Soest Altstadt centroid (initial fallback)
const SOEST_CENTER: [number, number] = [51.5700, 8.1150];

function FitToBins({ bins }: { bins: Bin[] }) {
  const map = useMap();
  useEffect(() => {
    if (bins.length === 0) return;
    const bounds = L.latLngBounds(bins.map((b) => [b.lat, b.lng] as [number, number]));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [map, bins.length]);
  return null;
}

function fillColor(pct: number): string {
  if (pct >= 80) return "#ef4444"; // red-500
  if (pct >= 50) return "#f59e0b"; // amber-500
  return "#10b981";                 // emerald-500
}

function binIcon(bin: Bin): L.DivIcon {
  const color = bin.locked ? "#6b7280" : fillColor(bin.fill_level);
  const pulse = bin.fill_level >= 80 && !bin.locked;
  return L.divIcon({
    className: "",
    html: `
      <div style="position: relative; width: 32px; height: 40px;">
        ${pulse ? `<div style="position:absolute;inset:-4px;border-radius:9999px;background:${color};opacity:0.3;animation:ping 1.5s cubic-bezier(0,0,0.2,1) infinite;"></div>` : ""}
        <svg viewBox="0 0 24 32" width="32" height="40" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25));">
          <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20s12-11 12-20c0-6.6-5.4-12-12-12z"
                fill="${color}" stroke="white" stroke-width="1.5"/>
          <circle cx="12" cy="12" r="5" fill="white"/>
          <text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="700" fill="${color}">
            ${bin.fill_level}
          </text>
        </svg>
      </div>
    `,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -36],
  });
}

/**
 * Smooth marker that interpolates between WS position updates via
 * requestAnimationFrame. Eliminates the visible "teleport" jumps when
 * positions arrive at 1–2 s intervals.
 */
function AnimatedTruckMarker({ truck }: { truck: TruckPosition }) {
  const markerRef = useRef<L.Marker | null>(null);
  const fromRef = useRef<[number, number]>([truck.lat, truck.lng]);
  const toRef = useRef<[number, number]>([truck.lat, truck.lng]);
  const startRef = useRef<number>(performance.now());
  const ANIM_MS = 1500;

  useEffect(() => {
    const m = markerRef.current;
    if (m) {
      const cur = m.getLatLng();
      fromRef.current = [cur.lat, cur.lng];
    }
    toRef.current = [truck.lat, truck.lng];
    startRef.current = performance.now();

    let raf = 0;
    const tick = () => {
      const m2 = markerRef.current;
      if (!m2) return;
      const t = Math.min(1, (performance.now() - startRef.current) / ANIM_MS);
      const lat = fromRef.current[0] + (toRef.current[0] - fromRef.current[0]) * t;
      const lng = fromRef.current[1] + (toRef.current[1] - fromRef.current[1]) * t;
      m2.setLatLng([lat, lng]);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [truck.lat, truck.lng]);

  return (
    <Marker
      ref={(el) => {
        markerRef.current = el ?? null;
      }}
      position={[truck.lat, truck.lng]}
      icon={truckIcon(truck)}
    >
      <Popup>
        <div className="space-y-1">
          <p className="font-semibold text-slate-900">Müllfahrzeug</p>
          <p className="text-xs text-slate-500">Status: {truck.action ?? "idle"}</p>
          {truck.current_bin_id && (
            <p className="text-xs">Aktuelle Tonne: {truck.current_bin_id}</p>
          )}
          {truck.load_percent !== undefined && (
            <p className="text-xs">
              Ladung: <span className="font-medium">{truck.load_percent}%</span>
              {truck.load_units !== undefined && truck.capacity_units !== undefined
                ? ` (${truck.load_units.toFixed(0)} / ${truck.capacity_units.toFixed(0)})`
                : ""}
            </p>
          )}
        </div>
      </Popup>
    </Marker>
  );
}

function truckIcon(truck: TruckPosition): L.DivIcon {
  const loadPct = Math.max(0, Math.min(100, truck.load_percent ?? 0));
  const barColor = loadPct >= 90 ? "#dc2626" : loadPct >= 70 ? "#f59e0b" : "#10b981";
  return L.divIcon({
    className: "",
    html: `
      <div style="width:42px;height:42px;border-radius:9999px;background:white;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;position:relative;">
        <div style="position:absolute;inset:2px;border-radius:9999px;background:conic-gradient(${barColor} ${loadPct * 3.6}deg,#e2e8f0 0deg);"></div>
        <div style="width:34px;height:34px;border-radius:9999px;background:#2563eb;border:3px solid white;display:flex;align-items:center;justify-content:center;position:relative;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 18H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v12"/>
          <path d="M15 18H9"/>
          <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H15"/>
          <circle cx="7" cy="18" r="2"/>
          <circle cx="17" cy="18" r="2"/>
        </svg>
        </div>
      </div>`,
    iconSize: [42, 42],
    iconAnchor: [21, 21],
  });
}

interface Props {
  bins: Bin[];
  truck: TruckPosition | null;
  activeRoute: Route | null;
  depot?: { lat: number; lng: number; name: string } | null;
}

function depotIcon(): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `
      <div style="width:28px;height:28px;border-radius:6px;background:#1e293b;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);display:flex;align-items:center;justify-content:center;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

export default function LeafletMap({ bins, truck, activeRoute, depot }: Props) {
  // Prefer OSRM geometry (real streets) over straight-line fallback
  const geometryLine: [number, number][] = activeRoute?.geometry
    ? activeRoute.geometry.coordinates.map(([lng, lat]) => [lat, lng])
    : [];

  // Fallback: straight lines between waypoints (dashed) when no OSRM geometry
  const fallbackLine: [number, number][] = !activeRoute?.geometry
    ? (activeRoute?.waypoints
        .map((id) => bins.find((b) => b.id === id))
        .filter((b): b is Bin => !!b)
        .map((b) => [b.lat, b.lng] as [number, number]) ?? [])
    : [];

  return (
    <MapContainer
      center={SOEST_CENTER}
      zoom={14}
      scrollWheelZoom
      className="h-full w-full"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToBins bins={bins} />

      {/* Real OSRM route — solid blue line following actual streets */}
      {geometryLine.length > 1 && (
        <Polyline positions={geometryLine} color="#2563eb" weight={5} opacity={0.8} />
      )}

      {/* Fallback straight line when OSRM unavailable */}
      {fallbackLine.length > 1 && (
        <Polyline positions={fallbackLine} color="#94a3b8" weight={3} opacity={0.5} dashArray="8 8" />
      )}

      {depot && (
        <Marker position={[depot.lat, depot.lng]} icon={depotIcon()}>
          <Popup>
            <p className="font-semibold">{depot.name}</p>
            <p className="text-xs text-slate-500">Betriebshof</p>
          </Popup>
        </Marker>
      )}

      {bins.map((bin) => (
        <Marker key={bin.id} position={[bin.lat, bin.lng]} icon={binIcon(bin)}>
          <Popup>
            <div className="space-y-1">
              <p className="font-semibold text-slate-900">{bin.name}</p>
              <p className="text-xs text-slate-500">{bin.address}</p>
              <p className="text-xs">Füllstand: <span className="font-medium">{bin.fill_level}%</span></p>
              <p className="text-xs">Akku: {bin.battery}%</p>
              <p className="text-xs text-slate-500">Status: {bin.status}{bin.locked ? " · gesperrt" : ""}</p>
            </div>
          </Popup>
        </Marker>
      ))}

      {truck && <AnimatedTruckMarker truck={truck} />}
    </MapContainer>
  );
}
