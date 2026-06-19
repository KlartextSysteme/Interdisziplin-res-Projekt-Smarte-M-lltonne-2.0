export function binStatusLabel(status: string, locked?: boolean): string {
  if (locked) return "Gesperrt";

  const labels: Record<string, string> = {
    idle: "Bereit",
    en_route: "Unterwegs",
    emptied: "Geleert",
    locked: "Gesperrt",
  };
  return labels[status] ?? status;
}

export function truckActionLabel(action?: string | null): string {
  const labels: Record<string, string> = {
    idle: "Bereit",
    en_route: "Auf Tour",
    emptying: "Leert Tonne",
    returning: "Zurück zur Route",
    returning_full: "Zum Betriebshof",
    unloading: "Entlädt am Betriebshof",
    paused: "Pausiert",
    pause: "Pausiert",
  };
  return labels[action ?? "idle"] ?? action ?? "Bereit";
}

export function securityEventLabel(eventType: string): string {
  const labels: Record<string, string> = {
    tamper: "Manipulationsalarm",
    theft_attempt: "Diebstahlversuch",
    unauthorized_open: "Unbefugtes Öffnen",
    damage_report: "Beschädigung gemeldet",
    hygiene_report: "Hygieneproblem gemeldet",
  };
  return labels[eventType] ?? eventType;
}

export function binLocationLabel(locationState?: string | null): string {
  const labels: Record<string, string> = {
    home: "Am Haus",
    truck: "Abholposition",
    moving_to_pickup: "Fährt zur Abholposition",
    moving_home: "Fährt nach Hause",
    docking: "Dockingstation",
    unknown: "Position unbekannt",
  };
  return labels[locationState ?? "unknown"] ?? locationState ?? "Position unbekannt";
}

export function eventTone(eventType: string): "red" | "amber" {
  return eventType === "damage_report" || eventType === "hygiene_report" ? "amber" : "red";
}
