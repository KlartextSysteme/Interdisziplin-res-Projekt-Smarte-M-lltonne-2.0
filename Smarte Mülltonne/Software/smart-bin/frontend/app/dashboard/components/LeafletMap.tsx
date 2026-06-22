"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Marker, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Crosshair, Lock, Truck, X } from "lucide-react";
import { binLocationLabel, binStatusLabel, eventTone, securityEventLabel, truckActionLabel } from "@/lib/labels";
import type { Bin, Route, TruckPosition } from "@/types";

// Soest Altstadt centroid (initial fallback)
const SOEST_CENTER: [number, number] = [51.5700, 8.1150];
const MARKER_TELEPORT_THRESHOLD = 0.01;

type AlertItem = { id: number; bin_id: number; event_type: string; timestamp: string };

function binCurrentPosition(bin: Bin): [number, number] {
  return [bin.current_lat ?? bin.lat, bin.current_lng ?? bin.lng];
}

function binHomePosition(bin: Bin): [number, number] | null {
  if (bin.home_lat == null || bin.home_lng == null) return null;
  return [bin.home_lat, bin.home_lng];
}

function binPickupPosition(bin: Bin): [number, number] | null {
  if (bin.pickup_lat == null || bin.pickup_lng == null) return null;
  return [bin.pickup_lat, bin.pickup_lng];
}

function isMovingBin(bin: Bin): boolean {
  return bin.location_state === "moving_to_pickup" || bin.location_state === "moving_home";
}

function FitToBins({ bins }: { bins: Bin[] }) {
  const map = useMap();
  useEffect(() => {
    if (bins.length === 0) return;
    const bounds = L.latLngBounds(bins.map(binCurrentPosition));
    map.fitBounds(bounds, { padding: [40, 40] });
  }, [map, bins.length]);
  return null;
}

function TruckFocusController({ truck, active }: { truck: TruckPosition | null; active: boolean }) {
  const map = useMap();
  useEffect(() => {
    if (!active || !truck) return;
    map.panTo([truck.lat, truck.lng], { animate: true, duration: 0.35, easeLinearity: 0.2 });
  }, [active, map, truck?.lat, truck?.lng]);
  return null;
}

// Pans/zooms to the selected bin whenever it changes
function BinFocusController({ bin }: { bin: Bin | null }) {
  const map = useMap();
  const lastIdRef = useRef<number | null>(null);
  useEffect(() => {
    if (!bin) return;
    if (bin.id === lastIdRef.current) return;
    lastIdRef.current = bin.id;
    const pos = binCurrentPosition(bin);
    map.flyTo(pos, Math.max(map.getZoom(), 16), { animate: true, duration: 0.7 });
  }, [map, bin?.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

function fillColor(pct: number): string {
  if (pct >= 80) return "#ef4444";
  if (pct >= 50) return "#f2c94c";
  return "#10b981";
}

function locationBadge(locationState?: string | null): string {
  const src =
    locationState === "truck" || locationState === "moving_to_pickup"
      ? "/icons/status-truck.svg"
      : "/icons/status-home.svg";
  return `<div style="position:absolute;right:-4px;bottom:1px;width:18px;height:18px;border-radius:9999px;background:#111214;border:2px solid #f2c94c;display:flex;align-items:center;justify-content:center;">
    <img src="${src}" alt="" style="width:12px;height:12px;object-fit:contain;display:block;" />
  </div>`;
}

function binIcon(bin: Bin, selected = false): L.DivIcon {
  const color = bin.locked ? "#6b7280" : fillColor(bin.fill_level);
  const pulse = bin.fill_level >= 80 && !bin.locked;
  const glow = selected
    ? `filter: drop-shadow(0 0 5px #f2c94c) drop-shadow(0 0 10px rgba(242,201,76,0.6));`
    : "";
  return L.divIcon({
    className: "",
    html: `
      <div style="position: relative; width: 32px; height: 40px; ${glow}">
        ${pulse ? `<div style="position:absolute;inset:-4px;border-radius:9999px;background:${color};opacity:0.3;animation:ping 1.5s cubic-bezier(0,0,0.2,1) infinite;"></div>` : ""}
        <svg viewBox="0 0 24 32" width="32" height="40" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.25));">
          <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 20 12 20s12-11 12-20c0-6.6-5.4-12-12-12z"
                fill="${color}" stroke="${selected ? "#f2c94c" : "white"}" stroke-width="${selected ? "2.5" : "1.5"}"/>
          <circle cx="12" cy="12" r="5" fill="white"/>
          <text x="12" y="15.5" text-anchor="middle" font-size="8" font-weight="700" fill="${color}">
            ${bin.fill_level}
          </text>
        </svg>
        ${locationBadge(bin.location_state)}
      </div>
    `,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -36],
  });
}

function animationDuration(updateGap: number): number {
  return Math.min(700, Math.max(240, updateGap * 0.9));
}

function AnimatedTruckMarker({ truck }: { truck: TruckPosition }) {
  const markerRef = useRef<L.Marker | null>(null);
  const initialPositionRef = useRef<[number, number]>([truck.lat, truck.lng]);
  const initialIconRef = useRef<L.DivIcon>(truckIcon(truck));
  const fromRef = useRef<[number, number]>([truck.lat, truck.lng]);
  const toRef = useRef<[number, number]>([truck.lat, truck.lng]);
  const startRef = useRef<number>(performance.now());
  const lastUpdateRef = useRef<number>(performance.now());
  const durationRef = useRef<number>(1200);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const m = markerRef.current;
    if (!m) return;
    m.setIcon(truckIcon(truck));
  }, [truck.load_percent]);

  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    const target: [number, number] = [truck.lat, truck.lng];
    const current = marker.getLatLng();
    const from: [number, number] = [current.lat, current.lng];
    const now = performance.now();
    const updateGap = now - lastUpdateRef.current;
    lastUpdateRef.current = now;
    fromRef.current = from;
    toRef.current = target;
    startRef.current = now;
    durationRef.current = animationDuration(updateGap);
    cancelAnimationFrame(rafRef.current);
    if (Math.abs(from[0] - target[0]) < 0.000001 && Math.abs(from[1] - target[1]) < 0.000001) {
      marker.setLatLng(target);
      return;
    }
    if (Math.abs(from[0] - target[0]) > MARKER_TELEPORT_THRESHOLD || Math.abs(from[1] - target[1]) > MARKER_TELEPORT_THRESHOLD) {
      marker.setLatLng(target);
      return;
    }
    const tick = (time: number) => {
      const m = markerRef.current;
      if (!m) return;
      const t = Math.min(1, (time - startRef.current) / durationRef.current);
      m.setLatLng([
        fromRef.current[0] + (toRef.current[0] - fromRef.current[0]) * t,
        fromRef.current[1] + (toRef.current[1] - fromRef.current[1]) * t,
      ]);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [truck.lat, truck.lng]);

  return (
    <Marker
      ref={(el) => { markerRef.current = el ?? null; }}
      position={initialPositionRef.current}
      icon={initialIconRef.current}
    />
  );
}

function AnimatedBinMarker({
  bin,
  position,
  selected,
  onSelect,
}: {
  bin: Bin;
  position: [number, number];
  selected: boolean;
  onSelect: () => void;
}) {
  const markerRef = useRef<L.Marker | null>(null);
  const initialPositionRef = useRef<[number, number]>(position);
  const initialIconRef = useRef<L.DivIcon>(binIcon(bin, selected));
  const fromRef = useRef<[number, number]>(position);
  const toRef = useRef<[number, number]>(position);
  const startRef = useRef<number>(performance.now());
  const lastUpdateRef = useRef<number>(performance.now());
  const durationRef = useRef<number>(350);
  const rafRef = useRef<number>(0);
  // Stable ref so click handler is set once and never gets unregistered on re-renders
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // Register click handler once on mount via the Leaflet instance directly
  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    const handler = () => onSelectRef.current();
    marker.on("click", handler);
    return () => { marker.off("click", handler); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    marker.setIcon(binIcon(bin, selected));
  }, [bin.fill_level, bin.locked, bin.location_state, selected]);

  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    const current = marker.getLatLng();
    const from: [number, number] = [current.lat, current.lng];
    const now = performance.now();
    const updateGap = now - lastUpdateRef.current;
    lastUpdateRef.current = now;
    fromRef.current = from;
    toRef.current = position;
    startRef.current = now;
    durationRef.current = animationDuration(updateGap);
    cancelAnimationFrame(rafRef.current);
    if (Math.abs(from[0] - position[0]) < 0.000001 && Math.abs(from[1] - position[1]) < 0.000001) {
      marker.setLatLng(position);
      return;
    }
    if (Math.abs(from[0] - position[0]) > MARKER_TELEPORT_THRESHOLD || Math.abs(from[1] - position[1]) > MARKER_TELEPORT_THRESHOLD) {
      marker.setLatLng(position);
      return;
    }
    const tick = (time: number) => {
      const m = markerRef.current;
      if (!m) return;
      const t = Math.min(1, (time - startRef.current) / durationRef.current);
      m.setLatLng([
        fromRef.current[0] + (toRef.current[0] - fromRef.current[0]) * t,
        fromRef.current[1] + (toRef.current[1] - fromRef.current[1]) * t,
      ]);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [position[0], position[1]]);

  return (
    <Marker
      ref={(el) => { markerRef.current = el ?? null; }}
      position={initialPositionRef.current}
      icon={initialIconRef.current}
    />
  );
}

function truckIcon(truck: TruckPosition): L.DivIcon {
  const loadPct = Math.max(0, Math.min(100, truck.load_percent ?? 0));
  const barColor = loadPct >= 90 ? "#dc2626" : loadPct >= 70 ? "#f2c94c" : "#10b981";
  return L.divIcon({
    className: "",
    html: `
      <div style="width:42px;height:42px;border-radius:9999px;background:#111214;box-shadow:0 4px 14px rgba(0,0,0,0.45);display:flex;align-items:center;justify-content:center;position:relative;border:1px solid rgba(242,201,76,0.55);">
        <div style="position:absolute;inset:2px;border-radius:9999px;background:conic-gradient(${barColor} ${loadPct * 3.6}deg,#31343a 0deg);"></div>
        <div style="width:34px;height:34px;border-radius:9999px;background:#f2c94c;border:3px solid #171717;display:flex;align-items:center;justify-content:center;position:relative;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#171717" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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

function depotIcon(): L.DivIcon {
  return L.divIcon({
    className: "",
    html: `
      <div style="width:30px;height:30px;border-radius:6px;background:#202328;border:2px solid #f2c94c;box-shadow:0 4px 12px rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f2c94c" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      </div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

// --- Bin-Detailkarte (overlay über der Karte) ---
function BinDetailCard({
  bin,
  alerts,
  onClose,
}: {
  bin: Bin;
  alerts: AlertItem[];
  onClose: () => void;
}) {
  const binAlerts = alerts.filter((a) => a.bin_id === bin.id);
  const latestAlert = binAlerts[binAlerts.length - 1];
  const alertTone = latestAlert ? eventTone(latestAlert.event_type) : null;
  const home = binHomePosition(bin);
  const pickup = binPickupPosition(bin);

  function fillBarColor(pct: number) {
    if (pct >= 80) return "bg-red-500";
    if (pct >= 50) return "bg-[#f2c94c]";
    return "bg-emerald-500";
  }

  return (
    <div className="absolute right-3 top-3 z-[2000] w-64 rounded-xl border border-white/15 bg-[#1a1c20]/95 shadow-2xl backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-start justify-between gap-2 border-b border-white/10 px-4 py-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{bin.name}</p>
          {bin.address && (
            <p className="truncate text-[11px] text-slate-400">{bin.address}</p>
          )}
        </div>
        <button
          onClick={onClose}
          className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded text-slate-500 hover:bg-white/10 hover:text-white"
          aria-label="Schließen"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="space-y-3 px-4 py-3">
        {/* Füllstand */}
        <div>
          <div className="mb-1 flex justify-between text-[11px]">
            <span className="text-slate-400">Füllstand</span>
            <span className="font-mono font-semibold text-white">{bin.fill_level}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-black/40">
            <div
              className={`h-full ${fillBarColor(bin.fill_level)} transition-all`}
              style={{ width: `${bin.fill_level}%` }}
            />
          </div>
        </div>

        {/* Akku */}
        <div>
          <div className="mb-1 flex justify-between text-[11px]">
            <span className="text-slate-400">Akku</span>
            <span className={`font-mono font-semibold ${bin.battery < 20 ? "text-red-400" : "text-white"}`}>
              {bin.battery}%
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-black/40">
            <div
              className={`h-full transition-all ${bin.battery < 20 ? "bg-red-500" : bin.battery < 50 ? "bg-[#f2c94c]" : "bg-emerald-500"}`}
              style={{ width: `${bin.battery}%` }}
            />
          </div>
        </div>

        {/* Status-Badges */}
        <div className="flex flex-wrap gap-1.5 text-[10px]">
          <span className="flex items-center gap-1 rounded bg-white/5 px-2 py-1 text-slate-300">
            <img
              src={
                bin.location_state === "truck" || bin.location_state === "moving_to_pickup"
                  ? "/icons/status-truck.svg"
                  : "/icons/status-home.svg"
              }
              alt=""
              className="h-3 w-3 object-contain"
            />
            {binLocationLabel(bin.location_state)}
          </span>
          <span className="rounded bg-white/5 px-2 py-1 text-slate-300">
            {binStatusLabel(bin.status, bin.locked)}
          </span>
          {bin.locked && (
            <span className="flex items-center gap-1 rounded bg-red-500/15 px-2 py-1 text-red-300">
              <Lock className="h-3 w-3" />
              Gesperrt
            </span>
          )}
        </div>

        {/* Aktive Meldung */}
        {latestAlert && (
          <div
            className={`rounded border px-3 py-2 text-[10px] ${
              alertTone === "amber"
                ? "border-[#f2c94c]/30 bg-[#f2c94c]/10 text-[#f2c94c]"
                : "border-red-400/30 bg-red-500/10 text-red-300"
            }`}
          >
            {securityEventLabel(latestAlert.event_type)}
          </div>
        )}

        {/* Home / Pickup Kontext */}
        {(home || pickup) && (
          <div className="space-y-1 border-t border-white/10 pt-2 text-[10px] text-slate-500">
            {home && (
              <div className="flex justify-between">
                <span>Zuhause</span>
                <span className="font-mono text-slate-400">
                  {home[0].toFixed(4)}, {home[1].toFixed(4)}
                </span>
              </div>
            )}
            {pickup && (
              <div className="flex justify-between">
                <span>Abholpos.</span>
                <span className="font-mono text-slate-400">
                  {pickup[0].toFixed(4)}, {pickup[1].toFixed(4)}
                </span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Routen-Geometrie: Truck-Position auf die Route projizieren ─────────────────
// Damit sich die Route sichtbar aufbaut (gefahren vs. kommend) und der nächste
// Streckenabschnitt bis zur nächsten Abholposition hervorgehoben werden kann.
// Abschnittsgrenzen sind die Abholpositionen der Tonnen, die exakt auf der Route
// liegen. Rein clientseitig aus dem vorhandenen Positionsstrom — kein Polling.

type LatLng = [number, number];

/** Projiziert Punkt p auf das Segment a–b, equirektangulär (lokal genau genug). */
function projectOnSegment(p: LatLng, a: LatLng, b: LatLng): { t: number; point: LatLng; d2: number } {
  const cos = Math.cos((a[0] * Math.PI) / 180);
  const ax = a[1] * cos, ay = a[0];
  const bx = b[1] * cos, by = b[0];
  const px = p[1] * cos, py = p[0];
  const dx = bx - ax, dy = by - ay;
  const len2 = dx * dx + dy * dy;
  let t = len2 > 0 ? ((px - ax) * dx + (py - ay) * dy) / len2 : 0;
  t = Math.max(0, Math.min(1, t));
  const point: LatLng = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  const ddx = p[1] * cos - point[1] * cos;
  const ddy = p[0] - point[0];
  return { t, point, d2: ddx * ddx + ddy * ddy };
}

/** Fortschritt eines Punktes entlang der Polylinie: Segmentindex + Projektion. */
function projectOnLine(p: LatLng, line: LatLng[]): { segIndex: number; point: LatLng } {
  let best = { segIndex: 0, point: line[0], d2: Infinity };
  for (let i = 0; i < line.length - 1; i++) {
    const r = projectOnSegment(p, line[i], line[i + 1]);
    if (r.d2 < best.d2) best = { segIndex: i, point: r.point, d2: r.d2 };
  }
  return { segIndex: best.segIndex, point: best.point };
}

/** Teil-Polylinie zwischen zwei Projektionen (a vor b auf derselben Linie). */
function subLine(line: LatLng[], aIdx: number, aPt: LatLng, bIdx: number, bPt: LatLng): LatLng[] {
  if (bIdx < aIdx) return [];
  if (aIdx === bIdx) return [aPt, bPt];
  return [aPt, ...line.slice(aIdx + 1, bIdx + 1), bPt];
}

interface Props {
  bins: Bin[];
  truck: TruckPosition | null;
  activeRoute: Route | null;
  candidates?: Route[];
  activeRouteId?: number | null;
  onSelectCandidate?: (id: number) => void;
  depot?: { lat: number; lng: number; name: string } | null;
  selectedBinId?: number | null;
  onSelectBin?: (id: number | null) => void;
  alerts?: AlertItem[];
}

export default function LeafletMap({ bins, truck, activeRoute, candidates = [], activeRouteId, onSelectCandidate, depot, selectedBinId, onSelectBin, alerts = [] }: Props) {
  const [truckFocusActive, setTruckFocusActive] = useState(false);
  const activeRouteBins = new Set(activeRoute?.waypoints ?? []);

  const selectedBin = bins.find((b) => b.id === selectedBinId) ?? null;

  const geometryLine: [number, number][] = activeRoute?.geometry
    ? activeRoute.geometry.coordinates.map(([lng, lat]) => [lat, lng])
    : [];

  const fallbackLine: [number, number][] = !activeRoute?.geometry
    ? (activeRoute?.waypoints
        .map((id) => bins.find((b) => b.id === id))
        .filter((b): b is Bin => !!b)
        .map((b) => binPickupPosition(b) ?? binCurrentPosition(b)) ?? [])
    : [];

  // Nicht-aktive Vorschläge als gedämpfte, klickbare Alternativlinien (Google-
  // Maps-Stil): Klick wählt den Kandidaten → wird gelb und gefahren.
  const currentRouteId = activeRouteId ?? activeRoute?.id ?? null;
  const candidateLines = candidates
    .filter((c) => c.id !== currentRouteId && c.geometry && c.waypoints.length > 0)
    .map((c) => ({
      id: c.id,
      line: c.geometry!.coordinates.map(([lng, lat]) => [lat, lng] as [number, number]),
    }));

  // Render nach Truck-Phase (robust gegen die Depot-Doppeldeutigkeit: das Depot
  // liegt am Anfang UND Ende der Geometrie, deshalb projizieren wir nur während
  // des Sammelns, wenn der Truck eindeutig zwischen den Tonnen ist):
  //   sammeln    → gefahren (grau) + kommend (gelb) + nächster Abschnitt
  //   Rückfahrt  → alles gedämpft (kein gelbes Neuzeichnen hinter dem Truck)
  //   Vorschau   → volle gelbe Linie (geplant, noch nicht gestartet)
  const truckPos: LatLng | null = truck ? [truck.lat, truck.lng] : null;
  const phase = truck?.action ?? "idle";
  const hasGeom = geometryLine.length > 1;
  const collecting = hasGeom && (phase === "en_route" || phase === "emptying" || phase === "paused");
  const returning = hasGeom && (phase === "returning" || phase === "returning_full" || phase === "unloading");

  let drivenLine: LatLng[] = [];
  let upcomingLine: LatLng[] = [];
  let nextSegment: LatLng[] = [];

  if (collecting && truckPos) {
    const proj = projectOnLine(truckPos, geometryLine);
    drivenLine = [...geometryLine.slice(0, proj.segIndex + 1), proj.point];
    upcomingLine = [proj.point, ...geometryLine.slice(proj.segIndex + 1)];

    // Nächster Abschnitt = bis zur Abholposition der aktuellen Zieltonne.
    const targetBin =
      truck?.current_bin_id != null ? bins.find((b) => b.id === truck.current_bin_id) : null;
    const targetPickup = (targetBin ? binPickupPosition(targetBin) : null) as LatLng | null;
    if (targetPickup) {
      const tp = projectOnLine(targetPickup, geometryLine);
      if (tp.segIndex >= proj.segIndex) {
        nextSegment = subLine(geometryLine, proj.segIndex, proj.point, tp.segIndex, tp.point);
      }
    }
  }

  function handleSelectBin(id: number) {
    // Bin-Selektion deaktiviert Truck-Fokus (Selektion hat Priorität)
    setTruckFocusActive(false);
    onSelectBin?.(selectedBinId === id ? null : id);
  }

  return (
    <div className="relative h-full w-full">
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
        <TruckFocusController truck={truck} active={truckFocusActive} />
        <BinFocusController bin={selectedBin} />

        {/* Nicht gewählte Vorschläge: nur in der Vorschau-Phase (vor Fahrtbeginn),
            damit während der Fahrt nur die eine befahrene Route sichtbar ist. */}
        {!collecting && !returning && candidateLines.map((c) => (
          <Polyline
            key={`cand-${c.id}`}
            positions={c.line}
            color="#94a3b8"
            weight={4}
            opacity={0.45}
            dashArray="2 7"
            eventHandlers={{ click: () => onSelectCandidate?.(c.id) }}
          />
        ))}

        {collecting ? (
          <>
            {drivenLine.length > 1 && (
              <Polyline positions={drivenLine} color="#6b7280" weight={4} opacity={0.4} />
            )}
            {upcomingLine.length > 1 && (
              <Polyline positions={upcomingLine} color="#f2c94c" weight={4} opacity={0.62} />
            )}
            {nextSegment.length > 1 && (
              <Polyline positions={nextSegment} color="#ffd866" weight={6} opacity={1} />
            )}
          </>
        ) : returning ? (
          // Rückfahrt zum Depot: gedämpft, kein gelbes Neuzeichnen hinter dem Truck
          hasGeom && (
            <Polyline positions={geometryLine} color="#6b7280" weight={4} opacity={0.35} />
          )
        ) : (
          // Vorschau (geplant, noch nicht gestartet)
          hasGeom && (
            <Polyline positions={geometryLine} color="#f2c94c" weight={5} opacity={0.86} />
          )
        )}
        {fallbackLine.length > 1 && (
          <Polyline positions={fallbackLine} color="#94a3b8" weight={3} opacity={0.5} dashArray="8 8" />
        )}

        {depot && (
          <Marker position={[depot.lat, depot.lng]} icon={depotIcon()} />
        )}

        {bins.map((bin) => {
          const current = binCurrentPosition(bin);
          const home = binHomePosition(bin);
          const pickup = binPickupPosition(bin);
          // Nur für noch nicht geleerte Tonnen, damit keine gestrichelten Reste
          // entlang der schon abgefahrenen Strecke kleben bleiben.
          const showMovementPath = Boolean(
            home && pickup && bin.fill_level > 0 && (activeRouteBins.has(bin.id) || isMovingBin(bin)),
          );

          return (
            <Fragment key={bin.id}>
              {showMovementPath && (
                <>
                  <Polyline
                    positions={[home!, pickup!]}
                    color="#f2c94c"
                    weight={2}
                    opacity={0.48}
                    dashArray="4 6"
                  />
                  <CircleMarker
                    center={pickup!}
                    radius={4}
                    pathOptions={{ color: "#f2c94c", weight: 2, fillColor: "#111214", fillOpacity: 0.85 }}
                  />
                </>
              )}
              <AnimatedBinMarker
                bin={bin}
                position={current}
                selected={selectedBinId === bin.id}
                onSelect={() => handleSelectBin(bin.id)}
              />
            </Fragment>
          );
        })}

        {truck && <AnimatedTruckMarker truck={truck} />}
      </MapContainer>

      {/* Bin-Detailkarte */}
      {selectedBin && (
        <BinDetailCard
          bin={selectedBin}
          alerts={alerts}
          onClose={() => onSelectBin?.(null)}
        />
      )}

      {/* Truck-Fokus-Button */}
      <button
        type="button"
        disabled={!truck}
        onClick={() => setTruckFocusActive((active) => !active)}
        title={truckFocusActive ? "Truck-Fokus deaktivieren" : "Truck fokussieren"}
        aria-label={truckFocusActive ? "Truck-Fokus deaktivieren" : "Truck fokussieren"}
        aria-pressed={truckFocusActive}
        className={[
          "absolute left-3 top-[86px] z-[1000] flex h-9 w-9 items-center justify-center rounded border shadow-lg transition",
          truckFocusActive
            ? "border-[#f2c94c] bg-[#f2c94c] text-[#111214] shadow-[#f2c94c]/20"
            : "border-[#3a3f46] bg-[#181b20] text-[#f2c94c] hover:border-[#f2c94c]/70",
          !truck ? "cursor-not-allowed opacity-45" : "",
        ].join(" ")}
      >
        {truckFocusActive ? <Truck size={18} strokeWidth={2.4} /> : <Crosshair size={18} strokeWidth={2.4} />}
      </button>

      {/* Truck-Infoleiste (unten links, nur wenn aktiv) */}
      {truck && truck.action && truck.action !== "idle" && (
        <div className="absolute bottom-6 left-3 z-[1000] flex items-center gap-2 rounded border border-white/10 bg-[#1a1c20]/90 px-3 py-1.5 text-xs backdrop-blur-sm">
          <Truck className="h-3.5 w-3.5 text-[#f2c94c]" />
          <span className="text-slate-300">{truckActionLabel(truck.action)}</span>
          {truck.load_percent !== undefined && (
            <span className="font-mono text-slate-400">{truck.load_percent}% Ladung</span>
          )}
        </div>
      )}
    </div>
  );
}
