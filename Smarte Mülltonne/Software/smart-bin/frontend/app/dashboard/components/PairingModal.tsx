"use client";

import { useState } from "react";
import { X, Search, CheckCircle2, Wifi, Radio, MapPin } from "lucide-react";

// --- Simulierte Device-Daten ---
// TODO: Ersetzen durch echten Discovery-Endpunkt (z.B. GET /bins/discover oder WS-Event)
const MOCK_DEVICE = {
  model: "SmartBin Pico W",
  tempId: "SB-PW-4A2F",
  signal: -62,
  lastContact: "gerade eben",
  firmware: "0.9.1-beta",
};

type Step = 1 | 2 | 3 | 4;

interface Props {
  onClose: () => void;
}

export default function PairingModal({ onClose }: Props) {
  // --- UI-Step-State ---
  const [step, setStep] = useState<Step>(1);
  const [scanning, setScanning] = useState(false);
  const [deviceFound, setDeviceFound] = useState(false);
  const [name, setName] = useState("Westfalenweg 36");
  const [address, setAddress] = useState("");

  function startScan() {
    setScanning(true);
    setDeviceFound(false);
    // Simulierter Scan mit 2,5 s Verzögerung
    // TODO: Ersetzen durch echten API-Call: GET /bins/discover (SSE oder Polling)
    setTimeout(() => {
      setScanning(false);
      setDeviceFound(true);
    }, 2500);
  }

  function handleConfirm() {
    // TODO: POST /bins  { name, address, device_id: MOCK_DEVICE.tempId }
    // TODO: POST /bins/{new_id}/command  { command: "pair" }
    setStep(4);
  }

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-sm rounded-xl border border-white/10 bg-[#1e2024] shadow-2xl">

        {/* Header */}
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#f2c94c]">
              Schritt {step} / 4
            </p>
            <h2 className="text-sm font-semibold text-white">Neue Tonne verbinden</h2>
          </div>
          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded text-slate-400 hover:bg-white/10 hover:text-white"
            aria-label="Schließen"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Schritt 1: Gerät in Pairing-Modus setzen */}
        {step === 1 && (
          <div className="p-5">
            <div className="mb-4 flex items-start gap-3 rounded-lg border border-white/10 bg-[#111214] p-3">
              <Radio className="mt-0.5 h-5 w-5 shrink-0 text-[#f2c94c]" />
              <div>
                <p className="text-xs font-semibold text-white">Gerät in Pairing-Modus setzen</p>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-400">
                  Pico/Touchpanel einschalten oder Setup-Modus per langem Druck auf BOOTSEL-Taste starten.
                  LED blinkt blau wenn bereit.
                </p>
              </div>
            </div>
            <p className="mb-4 text-[11px] text-slate-500">
              Gerät muss sich im selben Netzwerk wie der Backend-Server befinden. Empfohlener Weg: Vodafone 2,4 GHz oder Hotspot.
            </p>
            <div className="flex gap-2">
              <button
                onClick={onClose}
                className="flex-1 rounded border border-white/10 py-2 text-xs text-slate-400 hover:bg-white/5"
              >
                Abbrechen
              </button>
              <button
                onClick={() => { setStep(2); startScan(); }}
                className="flex-1 rounded bg-[#f2c94c] py-2 text-xs font-semibold text-[#171717] hover:bg-[#ffd866]"
              >
                Weiter → Suchen
              </button>
            </div>
          </div>
        )}

        {/* Schritt 2: Gerät suchen */}
        {step === 2 && (
          <div className="p-5">
            {scanning && (
              <div className="mb-4 flex flex-col items-center gap-3 py-2">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-[#f2c94c] border-t-transparent" />
                <p className="text-xs text-slate-400">Suche nach SmartBin-Geräten im Netzwerk…</p>
              </div>
            )}
            {!scanning && !deviceFound && (
              <div className="mb-4 flex flex-col items-center gap-2 py-2 text-center">
                <Search className="h-7 w-7 text-slate-500" />
                <p className="text-xs text-slate-400">Kein Gerät gefunden. Pairing-Modus prüfen und erneut suchen.</p>
              </div>
            )}
            {deviceFound && (
              <div className="mb-4 rounded-lg border border-[#f2c94c]/30 bg-[#111214] p-3">
                <div className="mb-2 flex items-center gap-2">
                  <Wifi className="h-4 w-4 text-[#f2c94c]" />
                  <p className="text-xs font-semibold text-white">{MOCK_DEVICE.model}</p>
                  <span className="ml-auto rounded-full bg-emerald-400/10 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                    Gefunden
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-y-1 text-[10px] text-slate-400">
                  <span>Geräte-ID:</span>
                  <span className="font-mono text-slate-300">{MOCK_DEVICE.tempId}</span>
                  <span>Signal:</span>
                  <span className="text-slate-300">{MOCK_DEVICE.signal} dBm</span>
                  <span>Letzter Kontakt:</span>
                  <span className="text-slate-300">{MOCK_DEVICE.lastContact}</span>
                  <span>Firmware:</span>
                  <span className="text-slate-300">{MOCK_DEVICE.firmware}</span>
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => setStep(1)}
                className="rounded border border-white/10 px-3 py-2 text-xs text-slate-400 hover:bg-white/5"
              >
                Zurück
              </button>
              {!deviceFound ? (
                <button
                  onClick={startScan}
                  disabled={scanning}
                  className="flex-1 rounded bg-[#f2c94c] py-2 text-xs font-semibold text-[#171717] hover:bg-[#ffd866] disabled:opacity-50"
                >
                  {scanning ? "Suche läuft…" : "Erneut suchen"}
                </button>
              ) : (
                <button
                  onClick={() => setStep(3)}
                  className="flex-1 rounded bg-[#f2c94c] py-2 text-xs font-semibold text-[#171717] hover:bg-[#ffd866]"
                >
                  Gerät auswählen
                </button>
              )}
            </div>
          </div>
        )}

        {/* Schritt 3: Gerät zuordnen */}
        {step === 3 && (
          <div className="p-5">
            <div className="mb-3 flex items-center gap-2">
              <MapPin className="h-4 w-4 text-[#f2c94c]" />
              <p className="text-xs font-semibold text-white">Gerät zuordnen</p>
            </div>
            <div className="mb-4 space-y-3">
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  Name / Bezeichnung
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full rounded border border-white/10 bg-[#111214] px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-[#f2c94c]/50 focus:outline-none"
                  placeholder="z.B. Westfalenweg 36"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wide text-slate-400">
                  Adresse (optional)
                </label>
                <input
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  className="w-full rounded border border-white/10 bg-[#111214] px-3 py-2 text-xs text-white placeholder-slate-500 focus:border-[#f2c94c]/50 focus:outline-none"
                  placeholder="z.B. Westfalenweg 36, 59494 Soest"
                />
              </div>
            </div>
            <p className="mb-4 text-[10px] text-slate-500">
              Home- und Abholposition können nach Verbindung auf der Karte gesetzt werden.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setStep(2)}
                className="rounded border border-white/10 px-3 py-2 text-xs text-slate-400 hover:bg-white/5"
              >
                Zurück
              </button>
              <button
                onClick={handleConfirm}
                disabled={!name.trim()}
                className="flex-1 rounded bg-[#f2c94c] py-2 text-xs font-semibold text-[#171717] hover:bg-[#ffd866] disabled:opacity-50"
              >
                Verbinden
              </button>
            </div>
          </div>
        )}

        {/* Schritt 4: Bestätigung */}
        {step === 4 && (
          <div className="p-5 text-center">
            <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-emerald-400" />
            <p className="mb-1 text-sm font-semibold text-white">Verbindung bestätigt</p>
            <p className="mb-4 text-[11px] text-slate-400">
              {name} wurde erfolgreich zugeordnet und steht in der Backend-Command-Queue bereit.
            </p>
            <div className="mb-4 rounded-lg border border-white/10 bg-[#111214] p-3 text-left">
              <div className="space-y-1 text-[10px]">
                <div className="flex justify-between">
                  <span className="text-slate-400">Gerät</span>
                  <span className="text-slate-300">{MOCK_DEVICE.model}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Geräte-ID</span>
                  <span className="font-mono text-slate-300">{MOCK_DEVICE.tempId}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Name</span>
                  <span className="text-slate-300">{name}</span>
                </div>
                {address && (
                  <div className="flex justify-between">
                    <span className="text-slate-400">Adresse</span>
                    <span className="text-slate-300">{address}</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-slate-400">Status</span>
                  <span className="text-emerald-300">Bereit für Command-Queue</span>
                </div>
              </div>
            </div>
            {/* TODO: Bins-Liste neu laden nach echtem POST /bins */}
            <button
              onClick={onClose}
              className="w-full rounded bg-[#f2c94c] py-2 text-xs font-semibold text-[#171717] hover:bg-[#ffd866]"
            >
              Fertig
            </button>
          </div>
        )}

        {/* Fortschritts-Dots */}
        <div className="flex items-center justify-center gap-1.5 pb-4">
          {([1, 2, 3, 4] as Step[]).map((s) => (
            <div
              key={s}
              className={`h-1.5 rounded-full transition-all ${
                s === step
                  ? "w-4 bg-[#f2c94c]"
                  : s < step
                    ? "w-1.5 bg-[#f2c94c]/40"
                    : "w-1.5 bg-white/20"
              }`}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
