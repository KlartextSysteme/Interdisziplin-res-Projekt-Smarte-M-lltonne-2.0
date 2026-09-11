"use client";

import type { Bin, LiveData, Route, TruckPosition } from "@/types";

export const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true";

const depot = {
  lat: 51.5583,
  lng: 8.1303,
  name: "Betriebshof Doyenweg",
};

const initialBins: Bin[] = [
  { id: 1, name: "FH Campus", address: "Lübecker Ring 2, 59494 Soest", lat: 51.5607, lng: 8.1148, fill_level: 92, battery: 71, solar_output_w: 8.4, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 2, name: "Siegener Str. 18", address: "Siegener Straße 18, 59494 Soest", lat: 51.5583, lng: 8.1124, fill_level: 88, battery: 64, solar_output_w: 6.9, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 3, name: "Danziger Ring", address: "Danziger Ring 5, 59494 Soest", lat: 51.5784, lng: 8.1265, fill_level: 91, battery: 22, solar_output_w: 0, is_charging: false, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 4, name: "Riga-Ring", address: "Riga-Ring 20, 59494 Soest", lat: 51.568, lng: 8.1284, fill_level: 78, battery: 82, solar_output_w: 9.1, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 5, name: "Siegener Str. 8", address: "Siegener Straße 8, 59494 Soest", lat: 51.5585, lng: 8.1132, fill_level: 74, battery: 77, solar_output_w: 7.5, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 6, name: "Troyesweg", address: "Troyesweg 4, 59494 Soest", lat: 51.5644, lng: 8.1162, fill_level: 81, battery: 68, solar_output_w: 5.8, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 7, name: "Paderborner Str.", address: "Paderborner Straße 25, 59494 Soest", lat: 51.5745, lng: 8.1394, fill_level: 76, battery: 85, solar_output_w: 10.2, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 8, name: "Senator-Schwartz", address: "Senator-Schwartz-Ring 15, 59494 Soest", lat: 51.5638, lng: 8.0811, fill_level: 55, battery: 18, solar_output_w: 0, is_charging: false, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 9, name: "Hiddingser Weg", address: "Hiddingser Weg 14, 59494 Soest", lat: 51.5648, lng: 8.1092, fill_level: 48, battery: 91, solar_output_w: 11.3, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
  { id: 10, name: "Steingraben", address: "Steingraben 12, 59494 Soest", lat: 51.571, lng: 8.1021, fill_level: 62, battery: 74, solar_output_w: 7.2, is_charging: true, status: "idle", locked: false, last_seen: new Date().toISOString() },
];

let bins = initialBins.map((bin) => ({ ...bin }));
let route: Route | null = null;
let startedAt = 0;
let pausedAt: number | null = null;
let simSpeed = 1;
let routeSerial = 1;
let lockedBins = new Set<number>();
let resolvedAlertBins = new Set<number>();

function distance(a: { lat: number; lng: number }, b: { lat: number; lng: number }) {
  const dLat = (b.lat - a.lat) * 111_000;
  const dLng = (b.lng - a.lng) * 71_000;
  return Math.hypot(dLat, dLng);
}

function interpolate(a: [number, number], b: [number, number], t: number): [number, number] {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

function routeCoordinates(activeRoute: Route): [number, number][] {
  const points: [number, number][] = [[depot.lat, depot.lng]];
  for (const id of activeRoute.waypoints) {
    const bin = bins.find((b) => b.id === id);
    if (bin) points.push([bin.lat, bin.lng]);
  }
  points.push([depot.lat, depot.lng]);
  return points;
}

function updateBinsForDemo() {
  const now = Date.now();
  const date = new Date(now);
  const hour = date.getHours() + date.getMinutes() / 60;
  const solarBase = Math.max(0, Math.sin((hour - 6) * Math.PI / 12) * 12);

  bins = bins.map((bin, index) => {
    const phase = (now / 10_000 + index) % 20;
    const solar = Math.max(0, solarBase + Math.sin(phase) * 1.5);
    const battery = Math.max(8, Math.min(100, bin.battery + (solar > 2 ? 0.02 : -0.015) * simSpeed));
    return {
      ...bin,
      battery: Math.round(battery),
      solar_output_w: Math.round(solar * 10) / 10,
      is_charging: solar > 2,
      locked: lockedBins.has(bin.id),
      status: lockedBins.has(bin.id) ? "locked" : bin.status,
      last_seen: new Date().toISOString(),
    };
  });
}

function elapsedRouteSeconds() {
  if (!startedAt) return 0;
  const end = pausedAt ?? Date.now();
  return ((end - startedAt) / 1000) * simSpeed;
}

function updateTruck(): TruckPosition | null {
  if (!route || !startedAt) return null;

  const coords = routeCoordinates(route);
  const elapsed = elapsedRouteSeconds();
  const segmentSeconds = 4;
  const totalSegments = coords.length - 1;
  const totalSeconds = totalSegments * segmentSeconds;
  const clamped = Math.min(elapsed, totalSeconds);
  const segment = Math.min(totalSegments - 1, Math.floor(clamped / segmentSeconds));
  const segmentT = (clamped - segment * segmentSeconds) / segmentSeconds;
  const pos = interpolate(coords[segment], coords[segment + 1], segmentT);

  let loadUnits = 0;
  route.waypoints.forEach((id, index) => {
    if (elapsed >= (index + 1) * segmentSeconds) {
      const before = bins.find((bin) => bin.id === id)?.fill_level ?? 0;
      loadUnits += before;
      bins = bins.map((bin) => bin.id === id ? { ...bin, fill_level: 0, status: "emptied" } : bin);
    }
  });

  if (elapsed >= totalSeconds) {
    route = { ...route, completed: true };
    return { lat: depot.lat, lng: depot.lng, action: "idle", current_bin_id: null, load_units: 0, capacity_units: 600, load_percent: 0 };
  }

  const capacityUnits = 600;
  const loadPercent = Math.min(100, Math.round((loadUnits / capacityUnits) * 100));

  return {
    lat: pos[0],
    lng: pos[1],
    action: pausedAt ? "pause" : segment >= route.waypoints.length ? "returning" : "en_route",
    current_bin_id: route.waypoints[segment] ?? null,
    load_units: loadUnits,
    capacity_units: capacityUnits,
    load_percent: loadPercent,
  };
}

export function getDemoLiveData(): LiveData {
  updateBinsForDemo();
  const truck = updateTruck();
  const alerts = bins
    .filter((bin) => bin.battery < 20 && !resolvedAlertBins.has(bin.id))
    .map((bin) => ({
      id: 10_000 + bin.id,
      bin_id: bin.id,
      event_type: "theft_attempt" as const,
      timestamp: new Date().toISOString(),
    }));

  return { bins, alerts, truck };
}

export function getDemoPublicConfig() {
  return { depot };
}

export function getDemoSimSpeed() {
  return { speed: simSpeed, paused: pausedAt !== null, min: 0.5, max: 20 };
}

export function setDemoSimSpeed(speed: number) {
  simSpeed = speed;
  return getDemoSimSpeed();
}

export function setDemoSimPaused(paused: boolean) {
  if (paused && pausedAt === null) pausedAt = Date.now();
  if (!paused && pausedAt !== null) {
    startedAt += Date.now() - pausedAt;
    pausedAt = null;
  }
  return getDemoSimSpeed();
}

export function getDemoLatestRoute() {
  return route;
}

export function planDemoRoute(): Route {
  const candidates = bins
    .filter((bin) => !lockedBins.has(bin.id) && bin.fill_level >= 60)
    .sort((a, b) => b.fill_level - a.fill_level)
    .slice(0, 7);

  const coords: [number, number][] = [[depot.lat, depot.lng], ...candidates.map((bin) => [bin.lat, bin.lng] as [number, number]), [depot.lat, depot.lng]];
  const distanceM = coords.reduce((sum, point, index) => {
    if (index === 0) return sum;
    return sum + distance({ lat: coords[index - 1][0], lng: coords[index - 1][1] }, { lat: point[0], lng: point[1] });
  }, 0);

  route = {
    id: routeSerial++,
    created_at: new Date().toISOString(),
    waypoints: candidates.map((bin) => bin.id),
    distance_m: Math.round(distanceM),
    duration_s: candidates.length * 4,
    geometry: {
      type: "LineString",
      coordinates: coords.map(([lat, lng]) => [lng, lat]),
    },
    completed: false,
    llm_reasoning: "Demo-Route nach Füllstand priorisiert.",
    nn_distance_m: Math.round(distanceM * 1.14),
    optimized_distance_m: Math.round(distanceM),
    exact_distance_m: Math.round(distanceM * 0.98),
  };
  startedAt = Date.now();
  pausedAt = null;
  return route;
}

export function resolveDemoAlerts(binId: number) {
  resolvedAlertBins.add(binId);
  return { bin_id: binId, resolved: true };
}

export function lockDemoBin(binId: number) {
  lockedBins.add(binId);
  bins = bins.map((bin) => bin.id === binId ? { ...bin, locked: true, status: "locked" } : bin);
  return { bin_id: binId, locked: true, command_id: Date.now() };
}

export function unlockDemoBin(binId: number) {
  lockedBins.delete(binId);
  bins = bins.map((bin) => bin.id === binId ? { ...bin, locked: false, status: "idle" } : bin);
  return { bin_id: binId, locked: false, command_id: Date.now() };
}
