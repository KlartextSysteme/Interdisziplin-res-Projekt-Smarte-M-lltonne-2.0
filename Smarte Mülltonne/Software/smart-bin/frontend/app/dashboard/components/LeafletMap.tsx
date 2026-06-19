"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import { CircleMarker, MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Crosshair, Truck } from "lucide-react";
import { binLocationLabel, binStatusLabel, truckActionLabel } from "@/lib/labels";
import type { Bin, Route, TruckPosition } from "@/types";

// Soest Altstadt centroid (initial fallback)
const SOEST_CENTER: [number, number] = [51.5700, 8.1150];
const MARKER_TELEPORT_THRESHOLD = 0.01;

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

    map.panTo([truck.lat, truck.lng], {
      animate: true,
      duration: 0.35,
      easeLinearity: 0.2,
    });
  }, [active, map, truck?.lat, truck?.lng]);

  return null;
}

function fillColor(pct: number): string {
  if (pct >= 80) return "#ef4444"; // red-500
  if (pct >= 50) return "#f2c94c";
  return "#10b981";                 // emerald-500
}

function locationBadge(locationState?: string | null): string {
  const src = locationState === "truck" || locationState === "moving_to_pickup"
    ? "/icons/status-truck.svg"
    : "/icons/status-home.svg";

  return `
    <div style="position:absolute;right:-4px;bottom:1px;width:18px;height:18px;border-radius:9999px;background:#111214;border:2px solid #f2c94c;display:flex;align-items:center;justify-content:center;">
      <img src="${src}" alt="" style="width:12px;height:12px;object-fit:contain;display:block;" />
    </div>`;
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

/**
 * Smooth marker that interpolates between WS position updates via
 * requestAnimationFrame. Eliminates the visible "teleport" jumps when
 * positions arrive at 1–2 s intervals.
 */
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
      const lat = fromRef.current[0] + (toRef.current[0] - fromRef.current[0]) * t;
      const lng = fromRef.current[1] + (toRef.current[1] - fromRef.current[1]) * t;
      m.setLatLng([lat, lng]);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [truck.lat, truck.lng]);

  return (
    <Marker
      ref={(el) => {
        markerRef.current = el ?? null;
      }}
      position={initialPositionRef.current}
      icon={initialIconRef.current}
    >
      <Popup>
        <div className="space-y-1">
          <p className="font-semibold text-white">Müllfahrzeug</p>
          <p className="text-xs text-slate-300">Status: {truckActionLabel(truck.action)}</p>
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

function AnimatedBinMarker({ bin, position }: { bin: Bin; position: [number, number] }) {
  const markerRef = useRef<L.Marker | null>(null);
  const initialPositionRef = useRef<[number, number]>(position);
  const initialIconRef = useRef<L.DivIcon>(binIcon(bin));
  const fromRef = useRef<[number, number]>(position);
  const toRef = useRef<[number, number]>(position);
  const startRef = useRef<number>(performance.now());
  const lastUpdateRef = useRef<number>(performance.now());
  const durationRef = useRef<number>(350);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    marker.setIcon(binIcon(bin));
  }, [bin.fill_level, bin.locked, bin.location_state]);

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
      const lat = fromRef.current[0] + (toRef.current[0] - fromRef.current[0]) * t;
      const lng = fromRef.current[1] + (toRef.current[1] - fromRef.current[1]) * t;
      m.setLatLng([lat, lng]);
      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [position[0], position[1]]);

  return (
    <Marker
      ref={(el) => {
        markerRef.current = el ?? null;
      }}
      position={initialPositionRef.current}
      icon={initialIconRef.current}
    >
      <Popup>
        <div className="space-y-1">
          <p className="font-semibold text-white">{bin.name}</p>
          <p className="text-xs text-slate-300">{bin.address}</p>
          <p className="text-xs">Füllstand: <span className="font-medium">{bin.fill_level}%</span></p>
          <p className="text-xs">Akku: {bin.battery}%</p>
          <p className="text-xs text-slate-300">Position: {binLocationLabel(bin.location_state)}</p>
          <p className="text-xs text-slate-300">Status: {binStatusLabel(bin.status, bin.locked)}</p>
        </div>
      </Popup>
    </Marker>
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

export default function LeafletMap({ bins, truck, activeRoute, depot }: Props) {
  const [truckFocusActive, setTruckFocusActive] = useState(false);
  const activeRouteBins = new Set(activeRoute?.waypoints ?? []);

  // Prefer OSRM geometry (real streets) over straight-line fallback
  const geometryLine: [number, number][] = activeRoute?.geometry
    ? activeRoute.geometry.coordinates.map(([lng, lat]) => [lat, lng])
    : [];

  // Fallback: straight lines between waypoints (dashed) when no OSRM geometry
  const fallbackLine: [number, number][] = !activeRoute?.geometry
    ? (activeRoute?.waypoints
        .map((id) => bins.find((b) => b.id === id))
        .filter((b): b is Bin => !!b)
        .map((b) => binPickupPosition(b) ?? binCurrentPosition(b)) ?? [])
    : [];

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

        {/* Real OSRM route — solid blue line following actual streets */}
        {geometryLine.length > 1 && (
          <Polyline positions={geometryLine} color="#f2c94c" weight={5} opacity={0.86} />
        )}

        {/* Fallback straight line when OSRM unavailable */}
        {fallbackLine.length > 1 && (
          <Polyline positions={fallbackLine} color="#94a3b8" weight={3} opacity={0.5} dashArray="8 8" />
        )}

        {depot && (
          <Marker position={[depot.lat, depot.lng]} icon={depotIcon()}>
            <Popup>
              <p className="font-semibold text-white">{depot.name}</p>
              <p className="text-xs text-slate-300">Betriebshof</p>
            </Popup>
          </Marker>
        )}

        {bins.map((bin) => {
          const current = binCurrentPosition(bin);
          const home = binHomePosition(bin);
          const pickup = binPickupPosition(bin);
          const showMovementPath = Boolean(
            home && pickup && (activeRouteBins.has(bin.id) || isMovingBin(bin) || bin.location_state === "truck"),
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
                    pathOptions={{
                      color: "#f2c94c",
                      weight: 2,
                      fillColor: "#111214",
                      fillOpacity: 0.85,
                    }}
                  />
                </>
              )}
              <AnimatedBinMarker bin={bin} position={current} />
            </Fragment>
          );
        })}

        {truck && <AnimatedTruckMarker truck={truck} />}
      </MapContainer>

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
    </div>
  );
}
