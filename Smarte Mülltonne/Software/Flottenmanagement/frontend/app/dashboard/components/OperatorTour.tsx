"use client";

import { useCallback, useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";

interface OperatorTourProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

interface TourStep {
  title: string;
  body: string;
  target?: string;
}

interface TargetRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const STORAGE_KEY = "smart-bin-operator-tour-v1";

const TOUR_STEPS: TourStep[] = [
  {
    title: "Dein Leitstand",
    body: "Diese Ansicht bündelt das, was während einer Schicht zählt: Füllstände, Route, Fahrzeugposition und offene Meldungen. Ziel ist nicht möglichst viel Oberfläche, sondern ein schneller, belastbarer Überblick, wenn nebenbei noch ein Fahrzeug, Funk und Zeitdruck mitlaufen.",
    target: '[data-tour="app-shell"]',
  },
  {
    title: "Route planen",
    body: "Mit der Routenplanung werden die relevanten Tonnen zu einer fahrbaren Tour verdichtet. Hohe Füllstände, gesperrte Tonnen und die Fahrzeugkapazität bestimmen, was zuerst sinnvoll ist. Du musst nicht jede Tonne einzeln bewerten.",
    target: '[data-tour="route-plan"]',
  },
  {
    title: "Flotte prüfen",
    body: "Links stehen die Tonnen nach Dringlichkeit sortiert. Ein Blick reicht für die Lage: voll, kritisch, gesperrt oder unauffällig. Wählst du eine Tonne aus, werden die Aktionen für genau diesen Behälter sichtbar.",
    target: '[data-tour="fleet-panel"]',
  },
  {
    title: "Tonne anfordern",
    body: "Die Befehle Abholung, Heim und Stopp wirken auf die ausgewählte Tonne. Nutze sie bewusst: Abholung ruft die Tonne zur Straße, Heim schickt sie zurück, Stopp hält sie in einer unsicheren Situation an.",
    target: '[data-tour="hardware-actions"], [data-tour="fleet-panel"]',
  },
  {
    title: "Karte lesen",
    body: "Die Karte zeigt, wo Tonnen, Fahrzeug und Route räumlich zusammenkommen. Sie hilft dir, die nächste Entscheidung nicht nur nach Liste, sondern nach echter Lage im Revier zu treffen.",
    target: '[data-tour="map"]',
  },
  {
    title: "Details ohne Umwege",
    body: "Rechts findest du Chat, Akku und Meldungen. Der Chat ist der schnelle Weg für natürliche Anweisungen, Akku zeigt drohende Ausfälle, Meldungen bündeln alles, was deine Aufmerksamkeit vor Ort braucht.",
    target: '[data-tour="side-tabs"]',
  },
  {
    title: "Live bleiben",
    body: "Der Live-Status zeigt, ob der Leitstand aktuelle Zustände empfängt. Wenn er aktiv ist, siehst du Statuswechsel zeitnah: geplante Route, bewegte Tonne, quittierte Aktion oder neue Sicherheitsmeldung.",
    target: '[data-tour="live-status"]',
  },
];

function readTargetRect(selector?: string): TargetRect | null {
  if (!selector || typeof document === "undefined") return null;
  const target = document.querySelector<HTMLElement>(selector);
  if (!target) return null;
  const rect = target.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return null;
  return {
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
  };
}

export default function OperatorTour({ open, onOpenChange }: OperatorTourProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const step = TOUR_STEPS[stepIndex];
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === TOUR_STEPS.length - 1;

  const updateTarget = useCallback(() => {
    setTargetRect(readTargetRect(step.target));
  }, [step.target]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (window.localStorage.getItem(STORAGE_KEY)) return;

    const id = window.setTimeout(() => onOpenChange(true), 700);
    return () => window.clearTimeout(id);
  }, [onOpenChange]);

  useEffect(() => {
    if (!open) return;

    const target = step.target ? document.querySelector<HTMLElement>(step.target) : null;
    target?.scrollIntoView({ block: "center", inline: "center", behavior: "smooth" });

    updateTarget();
    const settleTimer = window.setTimeout(updateTarget, 280);

    window.addEventListener("resize", updateTarget);
    window.addEventListener("scroll", updateTarget, true);
    return () => {
      window.clearTimeout(settleTimer);
      window.removeEventListener("resize", updateTarget);
      window.removeEventListener("scroll", updateTarget, true);
    };
  }, [open, step.target, updateTarget]);

  useEffect(() => {
    if (!open) setStepIndex(0);
  }, [open]);

  if (!open) return null;

  function finish() {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, "done");
    }
    onOpenChange(false);
  }

  const rootStyle: CSSProperties = {
    zIndex: 2147483000,
  };

  const panelStyle: CSSProperties = {
    bottom: 16,
    left: 16,
    right: 16,
    marginLeft: "auto",
    marginRight: "auto",
    maxWidth: 420,
    zIndex: 2147483647,
  };

  return (
    <div className="fixed inset-0" style={rootStyle}>
      <div className="fixed inset-0 bg-black/62" style={{ zIndex: 2147483000 }} />

      {targetRect ? (
        <div
          className="pointer-events-none fixed rounded border-2 border-[#f2c94c] shadow-[0_0_24px_rgba(242,201,76,0.36)] transition-all duration-200"
          style={{
            top: targetRect.top - 6,
            left: targetRect.left - 6,
            width: targetRect.width + 12,
            height: targetRect.height + 12,
            zIndex: 2147483100,
          }}
        />
      ) : null}

      <section
        data-tour-panel="true"
        role="dialog"
        aria-modal="true"
        aria-label="Leitstand-Einführung"
        className="fixed rounded border border-white/15 bg-[#1e2024] p-4 text-slate-100 shadow-2xl"
        style={panelStyle}
        aria-live="polite"
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#f2c94c]">
              Einführung {stepIndex + 1}/{TOUR_STEPS.length}
            </p>
            <h2 className="mt-1 text-base font-semibold text-white">{step.title}</h2>
          </div>
          <button
            type="button"
            onClick={finish}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded text-slate-400 transition hover:bg-white/10 hover:text-white"
            title="Einführung schließen"
            aria-label="Einführung schließen"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="text-sm leading-6 text-slate-300">{step.body}</p>

        <div className="mt-4 flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={finish}
            className="rounded px-2 py-1 text-xs font-semibold text-slate-400 transition hover:bg-white/10 hover:text-white"
          >
            Fertig
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setStepIndex((idx) => Math.max(0, idx - 1))}
              disabled={isFirst}
              className="flex h-9 w-9 items-center justify-center rounded border border-white/10 text-slate-300 transition hover:border-[#f2c94c]/50 hover:text-[#f2c94c] disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:border-white/10 disabled:hover:text-slate-300"
              title="Vorheriger Schritt"
              aria-label="Vorheriger Schritt"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
            type="button"
            onClick={() => (isLast ? finish() : setStepIndex((idx) => Math.min(TOUR_STEPS.length - 1, idx + 1)))}
            className="flex h-9 items-center gap-1.5 rounded bg-[#f2c94c] px-3 text-xs font-semibold text-[#171717] transition hover:bg-[#ffd866]"
          >
              {isLast ? "Abschließen" : "Weiter"}
              {!isLast && <ChevronRight className="h-4 w-4" />}
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
