import type { Bin, Route, SecurityEvent, EnergyStatus, ChatMessage } from "@/types";
import { getApiBaseUrl } from "@/lib/runtimeConfig";

async function get<T>(path: string): Promise<T> {
  const BASE = getApiBaseUrl();
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`GET ${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown, headers?: HeadersInit): Promise<T> {
  const BASE = getApiBaseUrl();
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`POST ${path} → ${res.status}`);
  return res.json();
}

// --- Bins ---
export const getBins = () => get<Bin[]>("/bins");
export const getBin = (id: number) => get<Bin>(`/bins/${id}`);

// --- Routes ---
// Planung liefert mehrere Kandidaten (Default ist active + is_default).
export const planRoute = () => post<Route[]>("/routes/plan");
export const getCandidates = () => get<Route[]>("/routes/candidates");
export const activateRoute = (id: number) => post<Route>(`/routes/${id}/activate`);
export const getLatestRoute = () => get<Route | null>("/routes/latest");

// --- Config ---
export interface PublicConfig {
  depot: { lat: number; lng: number; name: string };
}
export const getPublicConfig = () => get<PublicConfig>("/config/public");

// --- Sim controls (demo-speed multiplier + pause) ---
export interface SimSpeed {
  speed: number;
  paused?: boolean;
  min?: number;
  max?: number;
}
export const getSimSpeed = () => get<SimSpeed>("/sim/speed");

async function putSim(body: { speed?: number; paused?: boolean }): Promise<SimSpeed> {
  const BASE = getApiBaseUrl();
  const res = await fetch(`${BASE}/sim/speed`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`PUT /sim/speed → ${res.status}`);
  return res.json();
}

export const setSimSpeed = (speed: number) => putSim({ speed });
export const setSimPaused = (paused: boolean) => putSim({ paused });

// --- Security ---
export const getSecurityEvents = () => get<SecurityEvent[]>("/security/events");
export const createSecurityEvent = (binId: number, eventType: string) =>
  post("/security/events", { bin_id: binId, event_type: eventType });
export const lockBin = (binId: number, token: string) =>
  post(`/security/${binId}/lock`, undefined, { "X-Admin-Token": token });
export const unlockBin = (binId: number, token: string) =>
  post(`/security/${binId}/unlock`, undefined, { "X-Admin-Token": token });
export const resolveAlerts = (binId: number) =>
  post(`/security/${binId}/resolve`);
export const createProblemReport = (binId: number, reportType: "damage_report" | "hygiene_report") =>
  post(`/bins/${binId}/report`, { report_type: reportType, source: "webapp" });

// --- Energy ---
export const getEnergy = () => get<EnergyStatus[]>("/energy");

// --- Agent / Chat (SSE streaming) ---
export type ChatStreamEvent =
  | { type: "token"; content: string }
  | { type: "tool_call"; tool: string; input: Record<string, unknown> }
  | { type: "tool_result"; tool: string; output: string }
  | { type: "done" }
  | { type: "error"; message: string };

/**
 * POST /agent/chat with SSE streaming. Calls `onEvent` for each frame.
 * Returns a promise that resolves when the stream ends.
 */
export async function streamChat(
  message: string,
  history: ChatMessage[],
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const BASE = getApiBaseUrl();
  const resp = await fetch(`${BASE}/agent/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      message,
      history: history.map((m) => ({ role: m.role, content: m.content })),
    }),
    signal,
  });
  if (!resp.ok || !resp.body) {
    throw new Error(`streamChat failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // Split buffer into SSE frames (separated by blank line)
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const parsed = parseSseFrame(frame);
      if (parsed) onEvent(parsed);
    }
  }
}

function parseSseFrame(frame: string): ChatStreamEvent | null {
  const lines = frame.split("\n");
  let event = "message";
  let data = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  try {
    const payload = JSON.parse(data);
    if (event === "token") return { type: "token", content: payload.content };
    if (event === "tool_call") return { type: "tool_call", tool: payload.tool, input: payload.input ?? {} };
    if (event === "tool_result") return { type: "tool_result", tool: payload.tool, output: payload.output ?? "" };
    if (event === "done") return { type: "done" };
    if (event === "error") return { type: "error", message: payload.message ?? "unknown error" };
  } catch {
    return null;
  }
  return null;
}
