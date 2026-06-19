export interface Bin {
  id: number;
  name: string;
  address: string;
  lat: number;
  lng: number;
  home_lat?: number | null;
  home_lng?: number | null;
  pickup_lat?: number | null;
  pickup_lng?: number | null;
  current_lat?: number | null;
  current_lng?: number | null;
  fill_level: number;       // 0–100 %
  battery: number;          // 0–100 %
  solar_output_w?: number;
  is_charging?: boolean;
  status: "idle" | "en_route" | "emptied" | "locked";
  location_state?: "home" | "truck" | "docking" | "unknown" | "moving_to_pickup" | "moving_home" | string;
  movement_state?: "home" | "moving_to_pickup" | "pickup" | "moving_home" | string;
  locked: boolean;
  last_seen: string;        // ISO datetime
}

export interface GeoJSONLineString {
  type: "LineString";
  coordinates: [number, number][];   // [lng, lat] pairs (OSRM/GeoJSON spec)
}

export interface Route {
  id: number;
  created_at: string;
  waypoints: number[];                        // ordered bin IDs
  distance_m: number;
  duration_s: number | null;                  // OSRM estimated seconds
  geometry: GeoJSONLineString | null;         // real street path from OSRM
  completed: boolean;
  llm_reasoning: string | null;
  // TSP-Heuristik-Vergleich (planar, für die Optimierungs-Badge)
  nn_distance_m: number | null;                // Nearest-Neighbour Baseline
  optimized_distance_m: number | null;         // 2-opt Optimierung
  exact_distance_m: number | null;             // Held-Karp Exact (nur n ≤ 15)
}

export interface SecurityEvent {
  id: number;
  bin_id: number;
  event_type:
    | "tamper" | "theft_attempt" | "unauthorized_open"
    | "damage_report" | "hygiene_report"
    // Pico/Touchpanel-Events (Aufgabe 4)
    | "lock" | "unlock" | "lid_open" | "lid_close"
    | "goto_pickup" | "return_home" | "eco_mode" | "power_off"
    | string;
  timestamp: string;
  resolved: boolean;
}

export interface EnergyStatus {
  bin_id: number;
  name: string;
  battery: number;
}

export interface TruckPosition {
  lat: number;
  lng: number;
  action?: string;                // idle | en_route | emptying | returning | returning_full | unloading
  current_bin_id?: number | null;
  load_units?: number;
  capacity_units?: number;
  load_percent?: number;
}

// --- Chat / LLM agent ---
export interface ToolCall {
  name: string;
  input: Record<string, unknown>;
  output?: string;
  status: "pending" | "done" | "error";
}

export type ChatMessage =
  | { role: "user"; content: string }
  | { role: "assistant"; content: string; toolCalls?: ToolCall[] };

export interface LiveData {
  bins: Bin[];
  alerts: Pick<SecurityEvent, "id" | "bin_id" | "event_type" | "timestamp">[];
  truck: TruckPosition | null;
}
