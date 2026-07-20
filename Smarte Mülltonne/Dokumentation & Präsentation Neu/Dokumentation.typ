// ============================================================
//  SEMESTERPROJEKTDOKUMENTATION
//  Smarte Muelltonne 2.0
//  Stand: 06. Mai 2026
// ============================================================

#set document(
  title: "Smarte Mülltonne 2.0",
  author: "Projektgruppe Digitale Technologien",
)

#set page(
  paper: "a4",
  margin: (top: 2.7cm, bottom: 2.7cm, left: 2.8cm, right: 2.5cm),
  numbering: "1",
  header: context {
    set text(size: 8pt, fill: luma(150))
    set par(justify: false)
    align(left)[Smarte Mülltonne 2.0 · Semesterprojektdokumentation]
    v(-0.35em)
    line(length: 100%, stroke: 0.35pt + luma(205))
  },
  footer: context {
    line(length: 100%, stroke: 0.35pt + luma(205))
    v(4pt)
    set text(size: 8pt, fill: luma(150))
    align(right)[Seite #counter(page).display()]
  },
)

#set text(
  font: "IBM Plex Sans",
  size: 11pt,
  lang: "de",
  hyphenate: true,
)

#set par(
  justify: true,
  leading: 0.78em,
  spacing: 1.25em,
)

#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  v(0.8em)
  text(size: 20pt, weight: "bold", fill: rgb("#17324d"))[#it.body]
  v(0.25em)
  line(length: 100%, stroke: 1.4pt + rgb("#2f80ed"))
  v(0.9em)
}

#show heading.where(level: 2): it => {
  v(0.85em)
  text(size: 14pt, weight: "semibold", fill: rgb("#17324d"))[#it.body]
  v(0.35em)
}

#show heading.where(level: 3): it => {
  v(0.55em)
  text(size: 11.5pt, weight: "bold", fill: rgb("#17324d"))[#it.body]
  v(0.15em)
}

#show outline.entry.where(level: 1): it => {
  strong(it)
}

#show table.cell: it => {
  set par(justify: false, leading: 0.55em)
  set text(size: 9.2pt)
  it
}

#set table(
  stroke: (x, y) => (
    top: if y == 0 { 1.2pt + rgb("#17324d") } else { 0.25pt + luma(220) },
    bottom: if y == 0 { 0.8pt + rgb("#17324d") } else { none },
  ),
  fill: (x, y) => if y == 0 { rgb("#17324d") } else if calc.odd(y) { rgb("#f7f9fc") } else { white },
  inset: 7pt,
)

#show table.cell.where(y: 0): it => {
  set text(fill: white, weight: "bold", size: 9.4pt)
  it
}

#let infobox(content) = rect(
  fill: rgb("#f5f8fb"),
  stroke: (left: 3pt + rgb("#17324d")),
  inset: 13pt,
  radius: 2pt,
  width: 100%,
)[#content]

#let decision(content) = rect(
  fill: rgb("#eef6ff"),
  stroke: (left: 3pt + rgb("#2f80ed")),
  inset: 13pt,
  radius: 2pt,
  width: 100%,
)[#content]

#let risk(content) = rect(
  fill: rgb("#fff7ed"),
  stroke: (left: 3pt + rgb("#f97316")),
  inset: 13pt,
  radius: 2pt,
  width: 100%,
)[#content]

// ------------------------------------------------------------
// Titelseite
// ------------------------------------------------------------

#align(center)[
  #v(4.6cm)
  #text(size: 11pt, fill: rgb("#2f80ed"), weight: "bold", tracking: 1.5pt)[
    INTERDISZIPLINÄRES SEMESTERPROJEKT
  ]
  #v(0.9cm)
  #text(size: 30pt, weight: "bold", fill: rgb("#17324d"))[
    Smarte Mülltonne 2.0
  ]
  #v(0.35cm)
  #text(size: 15pt, fill: luma(90))[
    Hardware-Weiterentwicklung, Fahrverhalten und Flottenmanagement
  ]
  #v(0.8cm)
  #line(length: 42%, stroke: 1.5pt + rgb("#2f80ed"))
  #v(1.1cm)
  #text(size: 11pt)[
    Dokumentation des Projektstands, der Hardware-Konzeption und der digitalen Systemerweiterung \
    Studiengang Digitale Technologien
  ]
  #v(4.2cm)
  #grid(
    columns: (1fr, 1fr),
    align(left)[
      #text(size: 9pt, fill: luma(125))[*Projektgruppe*] \
      #text(size: 10.5pt)[Jan-Lukas · Theresa Pelz · Alaeddine Baghyour · Samiy Fulya Bulut · Jonas Wiesner]
    ],
    align(right)[
      #text(size: 9pt, fill: luma(125))[*Stand der Dokumentation*] \
      #text(size: 10.5pt)[03. Mai 2026]
    ]
  )
]

#pagebreak()
#outline(title: [Inhaltsverzeichnis])
#pagebreak()

= Einordnung und Übergabe

== Ausgangslage bei Projektübergabe

Das Projekt "Smarte Mülltonne" wurde aus einer Vorarbeit des Wintersemesters 2025/26 übernommen. Diese Vorarbeit bildet den technischen Startpunkt, wird in dieser Dokumentation aber nur als Ausgangslage beschrieben. Der Schwerpunkt dieser Dokumentation liegt auf der Weiterentwicklung im aktuellen Semester: bessere Fahreigenschaften, stabilere Mechanik, überarbeitete Sensorik, Energie- und Sicherheitsfunktionen sowie eine ergänzende Flottenmanagement-Web-App.

Bei der Übergabe lag bereits ein funktionsorientierter Prototyp mit Hardware- und Softwareanteilen vor. Die vorhandene Software außerhalb enthielt unter anderem MicroPython-Code für einen Raspberry Pi Pico beziehungsweise Pico 2W, Module für DC-Motoren, Linienverfolgung, Ultraschallmessung, Buttons, Buzzer, LEDs, Netzwerkkommunikation und eine einfache serverseitige Missionslogik. Zusätzlich waren Schaltpläne, 3D-Druckteile, Rechnungen, Fotos, Videos und eine ältere Dokumentation vorhanden.

#infobox[
  *Kurzfassung des Ist-Zustands:* Die vorherige Gruppe hatte eine einzelne smarte Mülltonne als Prototyp vorbereitet. Die Tonne konnte grundsätzlich fahren und war mit Sensorik, Motorsteuerung und lokalen Zuständen gedacht; softwareseitig existierten Pico-Client-Code und ein einfacher Serveransatz. Offen waren vor allem robuste Fahreigenschaften, zuverlässige Mechanik, verbesserter Antrieb, saubere Integration neuer Hardwarekomponenten, Energie- und Sicherheitskonzept sowie ein modernes Managementsystem für mehrere Tonnen.
]

== Abgrenzung dieser Dokumentation

Die alten Quellcodes, Bauteildateien und Dokumente aus dem Vorsemester werden nicht im Detail dokumentiert, weil sie nicht durch die aktuelle Projektgruppe erstellt wurden. Sie sind für die Einordnung relevant, aber nicht Gegenstand der eigenen Leistungsdokumentation.

Die eigene Weiterentwicklung konzentriert sich auf folgende Bereiche:

- Vision und Pflichtenheft für "Smarte Mülltonne 2.0"
- Use-Case-Matrix und Priorisierung
- Projektkoordination und Sprintplanung
- Hardware-, Mechanik- und Antriebskonzeption als zentrale Weiterentwicklung
- Verbesserung von Fahrverhalten, Traktion, Rädern, Kettenführung und Sensorintegration
- Energie-, Sicherheits- und Bedienkonzept
- Konzeption und Implementierung der Flottenmanagement-Web-App als digitale Erweiterung
- Schnittstellen zwischen Hardware, App, Backend und Simulation

= Zielbild

== Vision Statement

Die Projektvision beschreibt die Transformation einer passiven Mülltonne zu einem autonomen, energieautarken IoT-System. Ziel ist ein intelligentes Entsorgungsnetzwerk, das Komfort für Nutzer erhöht, Ressourcen schont und kommunale Abläufe durch datenbasierte Planung effizienter macht.

#decision[
  *Vision:* Die smarte Mülltonne soll nicht nur eine einzelne fahrende Tonne sein, sondern Teil eines Systems aus Sensorik, autonomer Bewegung, Energieüberwachung, Sicherheitslogik und zentraler Flottensteuerung.
]

== Pflichtenheft-Säulen

#figure(
  table(
    columns: (0.8fr, 1.8fr, 3fr),
    [*Nr.*], [*Säule*], [*Bedeutung im Projekt*],
    [1], [Intelligente Flottensteuerung], [Verwaltung mehrerer Tonnen, Planung von Abholrouten, zentrale Statusübersicht und bidirektionale Kommunikation.],
    [2], [Autarkie und Energie], [Ladestation beziehungsweise Docking-Konzept und Monitoring von Akku- und Ladezuständen.],
    [3], [Mobilität und Interaktion], [Verbesserte Fahrdynamik, Liniennavigation, Hindernisreaktion, Bedienung über Touchpanel und klare Nutzerfeedbacks.],
  ),
  caption: [Pflichtenheft-Säulen der Smarten Mülltonne 2.0],
)

== Vom Einzelprototyp zum fahrfähigen System

Der wichtigste konzeptionelle Schritt war nicht nur der Wechsel von einer isolierten Tonne zu einem Flottenmanagement, sondern zuerst die Weiterentwicklung des physischen Prototyps zu einem zuverlässig fahrenden System. Die Mülltonne muss mechanisch stabil, kontrollierbar und wiederholbar fahren, bevor die digitale Steuerung ihren Nutzen vollständig zeigen kann. Die Web-App erweitert diese Hardwarebasis um Monitoring, Planung und Demonstration, ersetzt sie aber nicht.

= Chronologische Projektstruktur

== Sprint 0: Orientierung und Sichtung

Sprint 0 war zunächst als Setup- und Alignment-Phase vom 14. April 2026 bis 19. April 2026 geplant. In dieser Phase standen die Sichtung der Vorarbeiten, die Rollenklärung, die Projektvision, die Tool-Auswahl und die Definition erster Use Cases im Vordergrund.

#figure(
  table(
    columns: (1.2fr, 2.2fr, 2.4fr),
    [*Zeitraum*], [*Schwerpunkt*], [*Ergebnis*],
    [14.04.–19.04.2026], [Setup & Alignment], [Projektvision konkretisieren, Rollen und Schwerpunkte klären, Projektplan anlegen.],
    [14.04.–19.04.2026], [Research], [Vorarbeiten aus dem Wintersemester 2025/26 sichten und Übergabe bewerten.],
    [15.04.–19.04.2026], [Use Cases], [Grundfunktionen wie Navigation, Füllstand, Status, Serververwaltung, Sicherheit und Aufladen sammeln.],
  ),
  caption: [Sprint 0 nach Notion-Zeitplanung],
)

== Sprint 1: Anforderungen, Architektur und Planung

Sprint 1 war vom 20. April 2026 bis 10. Mai 2026 geplant. Da diese Dokumentation den Stand vom 03. Mai 2026 abbildet, liegen einige Sprint-1-Arbeiten bereits als Konzept oder Prototyp vor, während andere laut Notion-Board noch in Bearbeitung oder offen sind.

Der Sprint hatte vier parallele Arbeitsrichtungen:

- Hardware und Mechanik: Antrieb, neue Räder, Kettenführung, Sensorik, Fahrwerk, Elektrik, Sicherheitskomponenten.
- Software und System: Fahrlogik, sichere Zustände, Motorsteuerung, Datenübergabe an App.
- App und UX/UI: Flottenmanagement-App, Layout, Karte, Visualisierung und Interaktionskonzept.
- Konzept und Produktstrategie: Vision, Use Cases, Storyline und Priorisierung.

== Weitere geplante Projektphasen

Die anschließende Planung sieht Sprint 2 vom 11. Mai 2026 bis 15. Mai 2026 mit Hardwareintegration, App-Pico-Verbindung, Touchpanel, ersten Fahrtests, Antriebsverbesserungen und Umsetzung des Flottenmanagement-Prototyps vor. Sprint 3 ist für den 06. Juni 2026 bis 10. Juni 2026 vorgesehen und fokussiert Erweiterungen wie Diebstahlschutz, kontinuierliche Navigationsverbesserung, UX-Verbesserungen, Hardwaretests und Fehleranalyse. Sprint 4 umfasst Ende Juni und Juli 2026 Finalisierung, Präsentation, Medien und technische Dokumentation.

= Use Cases und Priorisierung

== Überblick

Die Use-Case-Matrix ordnet die Projektidee in sechs Hauptkategorien:

#figure(
  table(
    columns: (0.7fr, 1.7fr, 3fr),
    [*ID*], [*Kategorie*], [*Ziel*],
    [UC1], [Autonome Navigation], [Die Mülltonne bewegt sich entlang einer definierten Linie, erkennt Hindernisse und erreicht die Bereitstellungsposition.],
    [UC2], [Füllstandsüberwachung], [Der Füllstand wird gemessen, in Prozent berechnet und an Anzeige beziehungsweise Server übergeben.],
    [UC3], [Statusanzeige], [Betriebszustände werden lokal über Touchpanel, Buzzer oder LED und digital in der App sichtbar.],
    [UC4], [Zentrale Serververwaltung], [Daten werden gespeichert, analysiert und für Routenplanung, Steuerung und Monitoring verwendet.],
    [UC5], [Diebstahl/Fremdnutzung], [Unberechtigtes Öffnen oder Manipulationen werden erkannt und als Sicherheitsereignis gemeldet.],
    [UC6], [Aufladen], [Die Tonne soll in eine Ladestation fahren und ohne manuellen Eingriff geladen werden.],
  ),
  caption: [Use-Case-Kategorien],
)

== Priorisierte Funktionen

Aus Sicht der Umsetzung wurden besonders die Funktionen priorisiert, die den Wechsel zum Systemprototyp ermöglichen: autonome Linienfahrt, Hindernisreaktion, Füllstandsmessung, Statusübermittlung, Serverdatenverarbeitung, bidirektionale Kommunikation, Routenplanung nach Füllstand und die Simulation von Abholprozessen.

#figure(
  table(
    columns: (0.8fr, 2fr, 1fr, 2.8fr),
    [*Use Case*], [*Funktion*], [*Priorität*], [*Kerntechnologie*],
    [1.0], [Autonome Linienfahrt], [1], [IR-Liniensensoren, Motorsteuerung],
    [1.2], [Dynamische Hindernisumfahrung], [1], [Ultraschallsensoren seitlich],
    [2.0], [Füllstand erkennen und ausgeben], [1], [Ultraschallsensorik],
    [3.4], [Zustand an Flottenmanagement-App übermitteln], [1], [API-Integration],
    [5.0], [Server speichert und analysiert Daten], [1], [Backend, Datenbank],
    [5.2], [Befehle und Updates], [1], [HTTP oder MQTT],
    [5.4], [Optimierte Routenplanung], [1], [Algorithmus beziehungsweise LLM-Agent],
    [6.0], [Docking-Ladestation], [2], [Ladekontakte, präzise Positionierung],
  ),
  caption: [Auszug aus der priorisierten Use-Case-Matrix],
)

= Hardware- und Mechanikentwicklung

== Ziel der Hardware-Weiterentwicklung

Die Hardware ist der Kern des Projekts. Die digitale Steuerung kann nur dann überzeugend funktionieren, wenn die Mülltonne mechanisch zuverlässig fährt, sauber auf Lenkbefehle reagiert und im Testaufbau wiederholbare Ergebnisse liefert. Deshalb liegt ein wesentlicher Teil der aktuellen Weiterentwicklung auf Antrieb, Rädern, Ketten, Gewichtsverteilung, Sensorpositionierung und sicherer Elektrik.

Aus der Übergabe ergab sich: Der vorhandene Prototyp war als Demonstrator wertvoll, seine Fahreigenschaften mussten für eine robuste Weiterentwicklung aber deutlich verbessert werden. Besonders kritisch sind Geradeauslauf, Kurvenverhalten, Traktion, Kettenführung, Spiel in der Mechanik und die Abstimmung zwischen Motoren, Sensorik und Software-Regelung.

#decision[
  *Hardware-Schwerpunkt:* Die Mülltonne soll nicht nur "irgendwie fahren", sondern kontrolliert, reproduzierbar und sicher entlang einer Linie navigieren. Neue Motoren, gedruckte Räder, angepasste Ketten und eine überarbeitete Mechanik sind deshalb zentrale Projektbestandteile.
]

== Fahrwerk, Räder und Ketten

Ein großer praktischer Arbeitsbereich ist die Verbesserung des Fahrwerks. Die vorhandene Kettenlösung bietet grundsätzlich gute Traktion, bringt aber auch Herausforderungen mit sich: Ketten können abspringen, zu viel Reibung erzeugen oder bei enger Kurvenfahrt ungleichmäßig laufen. Außerdem beeinflussen Durchmesser, Material und Geometrie der Räder direkt, wie gleichmäßig die Tonne anfährt und wie gut sie eine Linie halten kann.

Für die Weiterentwicklung werden deshalb neue Räder beziehungsweise Antriebselemente konstruiert und gedruckt. Ziel ist eine bessere Kraftübertragung, eine stabilere Kettenführung und eine mechanisch sauberere Verbindung zwischen Motor und Fahrwerk. Zusätzlich wird die Erweiterung beziehungsweise Anpassung der Ketten betrachtet, damit die Mülltonne mehr Auflagefläche und zuverlässigere Traktion erhält.

#figure(
  table(
    columns: (1.7fr, 3.2fr),
    [*Baustelle*], [*Ziel der Überarbeitung*],
    [Neue Räder drucken], [Bessere Passung zum Fahrwerk, stabilere Kraftübertragung und reproduzierbarere Bewegung.],
    [Ketten erweitern/anpassen], [Mehr Traktion, weniger Durchrutschen und stabileres Fahrverhalten auf dem Testuntergrund.],
    [Kettenführung verbessern], [Abspringen oder Verkanten reduzieren, besonders bei Kurven und Drehungen.],
    [Fahrwerk überarbeiten], [Einbaupositionen für Motoren, Sensorik, Akku, Touchpanel und Hardbutton sauber festlegen.],
    [Gewichtsverteilung prüfen], [Kippen, Schleifen und einseitige Belastung vermeiden.],
  ),
  caption: [Mechanische Schwerpunkte zur Verbesserung der Fahreigenschaften],
)

== Antriebsauslegung und Schrittmotoren

Die Antriebsauslegung bewertet die vorhandenen DC-Motoren und vergleicht sie mit möglichen Schrittmotoren. Hintergrund ist, dass die bisherige Fahrweise zwar demonstrierbar war, für präzise Liniennavigation, kontrollierte Kurven und wiederholbare Manöver aber mehr Reserven und eine feinere Ansteuerbarkeit benötigt werden.

Für ein Kettenrad mit 70 mm Teilkreisdurchmesser und eine angenommene Zugkraft von rund 10 N ergibt sich ein Drehmoment am Antriebsrad von etwa 0,35 Nm. Auf zwei Motoren verteilt entspricht dies etwa 0,175 Nm pro Motor.

#figure(
  table(
    columns: (2fr, 1.4fr, 2.6fr),
    [*Größe*], [*Wert*], [*Bedeutung*],
    [Zugkraft mit Sicherheitsfaktor], [ca. 10 N], [Grundlage für Drehmomentabschätzung.],
    [Drehmoment am Antriebsrad], [ca. 0,35 Nm], [Benötigtes Moment am Rad bei 35 mm Radius.],
    [Drehmoment pro Motor], [ca. 0,175 Nm], [Verteilung auf zwei Antriebe.],
    [Drehzahl bei 0,3 m/s], [ca. 82 U/min], [Langsame, kontrollierte Bewegung.],
    [Drehzahl bei 0,5 m/s], [ca. 136 U/min], [Schnellere Fahrt im Testbetrieb.],
  ),
  caption: [Auszug aus der Motorauslegung],
)

Als mögliche Schrittmotor-Optionen wurden ein NEMA17 42BYGHM809 und ein stärkerer NEMA17-05GM betrachtet. Die Berechnung zeigt, dass der stärkere Motor mit nutzbarem Drehmoment von ungefähr 0,504 bis 0,840 Nm eine deutlich höhere Reserve bietet. Der Schrittmotor ist für das Projekt besonders interessant, weil er sich exakter ansteuern lässt und dadurch bessere Voraussetzungen für kontrollierte Drehungen, gleichmäßige Geschwindigkeit und reproduzierbare Fahrmanöver schafft.

#figure(
  table(
    columns: (1.8fr, 1.4fr, 2.4fr),
    [*Komponente*], [*Status/Plan*], [*Relevanz*],
    [NEMA17-Schrittmotor], [geplant/geprüft], [Mehr Drehmomentreserve und präzisere Bewegungssteuerung als reine DC-Ansteuerung.],
    [Schrittmotor-Treiber], [recherchiert], [Notwendig für saubere Ansteuerung, Strombegrenzung und Microstepping.],
    [Gedruckte Räder], [in Planung/Umsetzung], [Mechanische Kopplung zwischen Motor, Achse und Kette verbessern.],
    [Kettenchassis], [vorhanden, wird überarbeitet], [Grundlage der Mobilität, aber abhängig von sauberer Führung und Spannung.],
  ),
  caption: [Antriebskomponenten und Rolle im Projekt],
)

== Sensorik und Bedienung

Für die Weiterentwicklung wurden zusätzliche oder überarbeitete Sensorik- und Bedienkomponenten geplant. Dazu gehören Magnetschalter für Deckelöffnung beziehungsweise Fremdnutzung, ein Touchdisplay als lokale Schnittstelle, Not-Aus, Buzzer, ggf. eine Akkuüberwachung, ein Spannungswandler und eine Ladeinfrastruktur.

Die Notion-Materialliste führt außerdem vorhandene Grundkomponenten wie Kettenroboterchassis, Mülltonnenkorpus, Motoren, Motortreiber und Bleiakku. Als Randbedingung wurde unter anderem ein Gesamtbudget und die verfügbare GPIO-Anzahl betrachtet; in der Materialliste ist festgehalten, dass 34 GPIO-Ports benötigt werden.

== Fahrlogik und Regelung

Die mechanische Verbesserung ist eng mit der Fahrlogik gekoppelt. Die vorhandene Software arbeitet mit Linienverfolgung, PD-Regelung, Hinderniserkennung, Pausen- und Startzuständen sowie Netzwerkkommunikation. Für die Weiterentwicklung bedeutet das: Neue Motoren und Räder können nicht isoliert betrachtet werden. Nach mechanischen Änderungen müssen Parameter wie Grundgeschwindigkeit, Regelverstärkung, Trim der beiden Antriebsseiten und Verhalten bei Linienverlust erneut getestet werden.

Die wichtigsten fahrtechnischen Ziele sind:

- stabiler Geradeauslauf ohne starkes Pendeln
- weichere Kurvenfahrt entlang der Linie
- kontrollierte 180-Grad-Drehung an Ziel- oder Wendepunkten
- sicherer Stopp bei Hindernissen
- Wiederfinden der Linie nach Störung oder Ausweichbewegung
- klare sichere Zustände bei Not-Aus, Sensorfehler oder Kommunikationsverlust

== Energie, Sicherheit und Elektrik

Neben dem Fahrwerk werden auch Energieversorgung und Sicherheit weitergedacht. Die geplante Dockingstation soll langfristig ermöglichen, dass die Tonne ohne manuelles Laden einsatzfähig bleibt. Gleichzeitig sind Magnetschalter, Not-Aus, Buzzer und Statusanzeigen relevant, weil die Tonne im öffentlichen oder halböffentlichen Raum zuverlässig und nachvollziehbar reagieren muss.

#figure(
  table(
    columns: (1.8fr, 3.2fr),
    [*Bereich*], [*Geplante Funktion*],
    [Ladung und Akku], [Betriebsdauer erhöhen, Ladestand messen und in App beziehungsweise Display anzeigen.],
    [Dockingstation], [Automatisches Laden über Kontaktflächen als Zukunftsschritt.],
    [Magnetschalter], [Deckelöffnung erkennen und Fremdnutzung melden.],
    [Not-Aus], [Physischer, hardwareunabhängiger Sicherheitsstopp.],
    [Touchpanel], [Lokale Bedienung und Statusanzeige direkt an der Tonne.],
    [Buzzer/LED], [Akustisches und visuelles Feedback bei Fehlern, Hindernissen oder Statuswechseln.],
  ),
  caption: [Hardwarefunktionen neben dem Antrieb],
)

== Bewertung für den Projektverlauf

Die Hardwareentwicklung ist der entscheidende Erfolgsfaktor des Projekts. Routenplanung, Sicherheitslogik und Energieanzeige entfalten ihren Wert erst, wenn die Mülltonne als physischer Prototyp zuverlässig fährt und sinnvoll Daten liefern kann. Gleichzeitig ist die Hardwareintegration risikoreich, da Motorsteuerung, Räder, Ketten, Sensorik, Energieversorgung und Kommunikation zeitlich eng gekoppelt sind.

#risk[
  *Technische Risiken:* Die wichtigsten Risiken liegen in der sauberen Linienverfolgung, der Kettenführung, der mechanischen Passung gedruckter Räder, der stabilen Stromversorgung, der Anzahl benötigter GPIOs, der zuverlässigen WLAN-Kommunikation und der Synchronisation zwischen lokaler Fahrlogik und zentralen Serverbefehlen.
]

= Digitale Erweiterung: Flottenmanagement-Web-App 

== Rolle der Web-App im Gesamtprojekt

Die Web-App wurde als ergänzender Prototyp im Ordner `smart-bin` entwickelt. Sie ist ein wichtiges Zusatzmodul, aber nicht die einzige Projektleistung. Während Hardware, Mechanik und Fahreigenschaften die Grundlage bilden, zeigt die App, wie die Tonne später in ein größeres System eingebunden werden kann: mit mehreren Tonnen, Füllstand, Akku, Ladeleistung, Sicherheitsstatus, Position, Routenplanung und Live-Visualisierung.

Die App dient damit als Demonstrator, Testumgebung und spätere Integrationsschicht zur Hardware. Sie ist gewissermaßen das sichtbare Management-Layer über dem eigentlichen mechatronischen System.

== Benchmarking bestehender Smart-Waste- und Fleet-Management-Systeme

=== Ziel des Benchmarkings

Im Rahmen der Konzeption der Flottenmanagement-Web-App für das Projekt "Smarte Mülltonne 2.0" wurde ein Benchmarking bestehender Systeme aus den Bereichen Smart Waste Management und Robot Fleet Management durchgeführt. Ziel war es, relevante funktionale und gestalterische Muster existierender Plattformen zu identifizieren, ihre Übertragbarkeit auf das eigene Projekt zu prüfen und daraus Anforderungen, Strukturprinzipien sowie Entwicklungsperspektiven für die eigene Web-Anwendung abzuleiten.

Die Web-App ist im Projekt als digitaler Management-Layer vorgesehen. Sie soll mehrere smarte Mülltonnen visualisieren, überwachen und perspektivisch operative Entscheidungen unterstützen. Damit ergänzt sie den mechatronischen Kern des Projekts, also die fahrende, sensorisch erfasste und energieüberwachte Mülltonne.

=== Ausgangspunkt der Betrachtung

Die digitale Erweiterung wurde nicht als isolierte Einzelansicht entworfen, sondern als Flottenmanagementsystem im Kleinen. Sie soll den Zustand mehrerer Tonnen in Echtzeit sichtbar machen, Routen visualisieren, Energie- und Sicherheitszustände abbilden und eine Schnittstelle zwischen simulierten beziehungsweise später real integrierten Hardwarekomponenten und einem zentralen Managementsystem herstellen.

Für das Benchmarking wurden deshalb nicht nur klassische Smart-Waste-Plattformen betrachtet, sondern auch Systeme aus dem Bereich Robot Fleet Management. Diese Systeme adressieren ähnliche Herausforderungen: zentrale Leitstellenlogik, Visualisierung verteilter Einheiten, Health-Monitoring, Routen- und Aufgabenkoordination sowie Verarbeitung von Live-Daten in webbasierten Dashboards.

=== Betrachtete Referenzsysteme

#figure(
  table(
    columns: (1.3fr, 1.25fr, 2.1fr, 2.35fr),
    [*System*], [*Domäne*], [*Relevante Funktionen*], [*Relevanz für unser Projekt*],
    [BrighterBins], [Smart Waste Management], [Echtzeit-Dashboard, Füllstandsanzeige, Alarme, Routenoptimierung.], [Referenz für die Verbindung aus Behältermonitoring und operativer Tourenplanung.],
    [ThingsBoard / IoT Hub], [IoT / Smart Waste], [Live-Dashboards, Rule Engine, Multi-Tenant-Strukturen, Sensordatenintegration.], [Relevant für die zentrale Visualisierung und Verarbeitung von Zustandsdaten mehrerer Einheiten.],
    [Renderbit], [Smart City / Waste Tracking], [Live-Karte, Fahrzeug- und Behältertracking, farbliche Statuscodierung, Historical Playback.], [Besonders relevant für kartenzentrierte Leitstellenlogik und visuelle Flottendarstellung.],
    [MiR Fleet], [Robot Fleet Management], [Zentrale Flottensteuerung, Task-Zuweisung, Statusmonitoring.], [Referenz für eine Leitstellenlogik für mehrere autonome Einheiten.],
    [InOrbit], [Robot Operations], [Echtzeit-Flottenübersicht, Incident-Logik, Health-Monitoring, Verlaufsdaten.], [Relevant für die Kombination aus Monitoring, Ereignismanagement und operativer Übersicht.],
    [KUKA.AMR Fleet Manager], [AMR-Flottenmanagement], [Routenkoordination, Prozessstatus, Flottensteuerung, Integrationsschnittstellen.], [Zeigt, wie komplexere Flottenmanagementsysteme als operative Steuerungsebene aufgebaut sind.],
    [Boston Dynamics Orbit], [Robot Fleet / Site Operations], [Standortübergreifende Dashboards, Flottengesundheit, Performance-Monitoring.], [Referenz für die Aggregation von Zustandsdaten in einer zentralen Oberfläche.],
  ),
  caption: [Betrachtete Referenzsysteme im Benchmarking],
)

Aus dem Vergleich der betrachteten Systeme wurde deutlich, dass sich unabhängig von der jeweiligen Domäne mehrere wiederkehrende Funktionsblöcke identifizieren lassen. Dazu gehören insbesondere eine zentrale Flottenübersicht, die Verdichtung von Telemetrie- und Statusdaten, Funktionen zur Einsatz- und Routenkoordination sowie Mechanismen zur Ereignis- und Sicherheitsbehandlung.

=== Relevante Vergleichsdomänen

*Smart-Waste-Management-Systeme* sind besonders nah an der eigenen Projektidee, da sie Behälterzustände, Füllstandssensorik, Sammelprozesse und kommunale Entsorgungslogik digital unterstützen. Die betrachteten Systeme zeigen wiederkehrend dieselben Kernmuster: eine zentrale Übersicht über Behälter und Fahrzeuge, Darstellung von Füllständen und Zuständen in Echtzeit, Alarme bei kritischen Ereignissen sowie Unterstützung bei Touren- und Sammelprozessen.

*Robot-Fleet-Management-Systeme* sind nicht direkt dem Entsorgungsbereich zuzuordnen, zeigen jedoch sehr deutlich, wie verteilte autonome Einheiten zentral überwacht, koordiniert und in operative Prozesse eingebunden werden können. Für das eigene Projekt waren sie relevant, weil sie starke Vorbilder für Dashboard-Architektur, Flottenübersicht, Zustandsaggregation, Aufgabensteuerung und Leitstellenlogik liefern.

=== Vergleichsachsen für die eigene Konzeption

Ein zentrales Muster der Benchmark-Systeme ist die Kombination aus Kartenansicht und Flottenliste. Position und Status einzelner Einheiten werden meist über Marker auf einer Karte beziehungsweise einer räumlichen Oberfläche sowie ergänzend in Listen, Statuskarten oder Panels dargestellt. Diese Beobachtung war direkt anschlussfähig an die eigene Web-App, in der FleetPanel, MapView, Route, Depot und Truck bewusst nebeneinander gedacht wurden.

Ein weiteres Ergebnis war die hohe Bedeutung verdichteter Betriebs- und Zustandsdaten. In Smart-Waste-Systemen stehen Füllstände, Batterie- oder Energiezustände, Konnektivität und Sammelstatus im Vordergrund. In Robot-Fleet-Systemen treten Health-Indikatoren wie Batterie, Verfügbarkeit, Incident-Status oder Netzwerkzustände an ihre Stelle. Für das eigene Projekt bestätigte dies die Konzentration auf Füllstand, Akku, Ladeleistung, Sicherheitszustand und Sperrstatus als zentrale Telemetriedaten.

Auch Routen- und Einsatzplanung erscheinen in professionellen Systemen als Kernfunktion. Für das eigene Projekt war dabei weniger entscheidend, welcher konkrete Optimierungsalgorithmus in der frühen Prototypenphase genutzt wird. Wichtiger war die Erkenntnis, dass Routing grundsätzlich datengetrieben, dynamisch und erweiterbar gedacht werden sollte. Die aktuelle Tourenlogik ist daher als funktionaler Prototyp zu verstehen. Perspektivisch sind stärkere Optimierungsverfahren wie 2-Opt, verbesserte Tourenheuristiken oder Python-basierte Routing-Frameworks anschlussfähig und wurden auch im Austausch mit dem betreuenden Professor als sinnvoller Entwicklungspfad diskutiert.

Die Analyse bestehender Systeme zeigte außerdem, dass professionelles Flottenmanagement fast immer Ereignis- und Alarmmanagement umfasst. In Smart-Waste-Lösungen betrifft dies beispielsweise Überfüllung, Manipulation, Feuer oder Fremdnutzung. In Robotiksystemen geht es eher um Incidents, technische Ausfälle, Kommunikationsprobleme oder Zustandsverletzungen. Diese Einordnung stärkte die Entscheidung, Sicherheitsereignisse, Sperrlogik, Alert-Banner und Quittierungsmechanismen in die eigene Lösung aufzunehmen.

Besonders relevant war zudem die Rolle von Simulation und Demo-Betrieb. Viele professionelle Systeme verfügen über Verlaufsansichten, historische Auswertungen oder Testumgebungen. Für das eigene Projekt wurde früh entschieden, die digitale Schicht auch unabhängig von vollständig integrierter Hardware entwickelbar zu machen. Simulation wurde daher nicht als Notlösung verstanden, sondern als sinnvoller Entwicklungspfad für ein cyber-physisches System.

=== Zusammenfassende Vergleichsdimensionen

#figure(
  table(
    columns: (1.25fr, 2.2fr, 2.4fr),
    [*Vergleichsdimension*], [*Beobachtung in Benchmark-Systemen*], [*Relevanz für das Projekt*],
    [Flottenübersicht], [Zentrale Kombination aus Karte, Flottenliste und Statusanzeige.], [Bestätigung der eigenen Dashboard-Struktur mit FleetPanel und MapView.],
    [Telemetrie], [Echtzeitdarstellung von Füllstand, Batterie, Status und Konnektivität.], [Bestätigung der Fokussierung auf Füllstand, Akku, Ladeleistung und Sicherheitsstatus.],
    [Routenplanung], [Routing und Einsatzplanung sind Kernbestandteil professioneller Systeme.], [Routing wurde früh als ausbaufähige Kernfunktion integriert.],
    [Sicherheitslogik], [Alerts, Incidents und Ereignismanagement gehören zum Standard.], [Bestätigung von Sicherheitsereignissen, Sperren und Quittierungen.],
    [Simulation / Historie], [Historisierung, Testumgebungen und Playback-Funktionen sind verbreitet.], [Bestätigung der Strategie "Simulation vor Hardwareintegration".],
    [Leitstellenlogik], [Zentrale operative Oberflächen verdichten Informationen und ermöglichen Eingriffe.], [Einordnung der Web-App als Management-Layer und nicht nur als Visualisierung.],
  ),
  caption: [Vergleichsdimensionen und Ableitungen für die eigene Konzeption],
)

=== Bedeutung für die Systemkonzeption

Aus Sicht der Projektgruppe hatte das Benchmarking vor allem drei Funktionen. Erstens half es dabei, die Web-App nicht nur als projektspezifische Einzelentwicklung zu betrachten, sondern als Teil eines größeren Musters digitaler Flottenmanagementsysteme. Zweitens zeigte es, dass Flottenübersicht, Statusdarstellung, Routenlogik, Sicherheitsereignisse und Simulation keine isolierten Ideen sind, sondern sich eng an wiederkehrenden Strukturen realer Systeme orientieren. Drittens machte das Benchmarking sichtbar, an welchen Stellen der Prototyp langfristig weiterentwickelt werden kann: stärkere Tourenoptimierung, Rollenmodelle, historische Auswertungen, Replay-Funktionen und vertiefte agentische Unterstützung.

Das Benchmarking war damit kein Mittel zur nachträglichen Bewertung der eigenen Lösung, sondern ein konzeptionelles Werkzeug zur Orientierung und Einordnung. Es positioniert die Web-App als nachvollziehbaren Prototyp innerhalb eines professionellen Systemkontexts und zeigt zugleich Entwicklungsperspektiven für den weiteren Ausbau.

#pagebreak() 

== Zielgruppe und User Persona

=== Methodisches Vorgehen

Bevor konkrete Bildschirmlayouts oder Interaktionsmuster entworfen wurden, erfolgte eine bewusste Verortung der Web-App auf Seiten der Anwendenden. Das Benchmarking hatte gezeigt, welche Funktionen professionelle Flottenmanagementsysteme bereitstellen, beantwortete aber nicht die Frage, für wen diese Funktionen im konkreten Einsatzkontext der Smarten Mülltonne tatsächlich zugeschnitten sein müssen. Die Bildung einer User Persona dient deshalb nicht der Marktforschung, sondern als Designwerkzeug: Sie macht implizite Annahmen über Nutzungssituation, technische Vorerfahrung und Aufgaben sichtbar und prüfbar.

Die Persona wurde aus drei Quellen abgeleitet. Erstens aus den Use-Case-Anforderungen, die im vorangegangenen Kapitel formuliert wurden, insbesondere dem Disponieren der Tonnen-Abholung, dem Reagieren auf Sicherheits- und Akku-Ereignisse sowie dem Bedienen des Fahrzeugs. Zweitens aus realistischen Berufsbildern in kommunalen Entsorgungsbetrieben, in denen Fahrerinnen und Fahrer zunehmend Aufgaben übernehmen, die früher in einer separaten Leitstelle abgewickelt wurden. Drittens aus den Beschränkungen des Einsatzkontexts: laute Umgebung, Witterung, Handschuhe, kurze Aufmerksamkeitsfenster zwischen Tonnen-Stops, mobile Nutzung im Fahrzeug.

=== Primärpersona: Fahrer und Systemoperator in einer Person

#figure(
  grid(
    columns: (1fr, 1.9fr),
    column-gutter: 1em,
    rows: (auto),
    align: (center + top, left + top),
    [
      #box(
        clip: true,
        radius: 10pt,
        stroke: 0.5pt + rgb("#e2e8f0"),
        image("Persona.png", height: 6.6cm, fit: "cover"),
      )
    ],
    [
      #table(
        columns: (1fr, 2fr),
        [*Eigenschaft*], [*Beschreibung*],
        [*Name*], [Stefan Krüger],
        [*Alter*], [42 Jahre],
        [*Rolle*], [Müllwagenfahrer und Tour-Disponent eines kommunalen Entsorgungsbetriebs],
        [*Erfahrung*], [16 Jahre Berufserfahrung im Entsorgungswesen, davon 4 Jahre als Tourenverantwortlicher],
        [*Arbeitsplatz*], [Mobil im Fahrerhaus eines Entsorgungsfahrzeugs, ergänzt durch ein Tablet im Fahrzeug und einen Desktop-Arbeitsplatz im Betriebshof],
        [*Technikaffinität*], [Mittel — alltäglicher Smartphone-Nutzer, vertraut mit Navigations- und Auftragssystemen, Chatbots, aber kein IT-Fachmann],
        [*Bezug zum System*], [Bedient die Web-App primär als operativer Disponent vor und während der Tour],
      )
    ],
  ),
  caption: [Steckbrief der Primärpersona Stefan Krüger],
)

#pagebreak()
=== Hintergrund und Arbeitskontext

Stefan beginnt seinen Arbeitstag um sechs Uhr am Betriebshof. Während er auf Kollegen wartet, prüft er auf einem Bildschirm die Übersicht der heute relevanten Tonnen. Er sieht auf einen Blick, welche Behälter besonders hohe Füllstände aufweisen, ob in der Nacht Sicherheitsereignisse aufgetreten sind und ob Tonnen aufgrund von Manipulationsverdacht gesperrt werden müssen. Auf Basis dieser Informationen entscheidet er, welche Touren heute zuerst gefahren werden und ob das Fahrzeug zusätzlich beladen werden muss.

Sobald die Tour beginnt, wechselt Stefans Rolle. Er sitzt am Steuer eines schweren Fahrzeugs, trägt Arbeitshandschuhe und hat regelmäßig keine freie Hand. Komplexe Eingaben sind in dieser Situation nicht möglich. Er möchte stattdessen schnell sehen, wo die nächste Tonne steht, ob sich der Status seit Tour-Beginn geändert hat und ob er zwischendurch auf Ereignisse reagieren muss. Während er das Fahrzeug bewegt, dient die Web-App eher als Informations-Cockpit denn als Eingabewerkzeug.

Am Ende der Tour kehrt Stefan zum Betriebshof zurück und schließt die Tour ab. In Ausnahmefällen muss er zusätzliche Sicherheitsereignisse dokumentieren, etwa wenn eine Tonne vor Ort beschädigt wurde oder eine Sperrung notwendig ist. Auch hier nutzt er die Web-App primär, um den Zustand der Tonnen für die nächste Schicht oder für Kollegen sauber abzubilden.

=== Ziele

Stefans übergeordnetes Ziel ist eine effiziente, vollständige und sichere Abholung der ihm zugewiesenen Tonnen. Daraus ergeben sich konkrete Teilziele.

#figure(
  table(
    columns: (1.5fr, 3.5fr),
    [*Ziel*], [*Bedeutung im Alltag*],
    [Schneller Überblick über volle Tonnen], [Reduziert Leerfahrten und ermöglicht das Setzen klarer Prioritäten zu Schichtbeginn.],
    [Verlässliche Routenplanung], [Spart Zeit, Treibstoff und reduziert kognitive Last während der Fahrt.],
    [Klare Reaktion auf Sicherheitsereignisse], [Schützt vor Eskalation bei Manipulation, Brandverdacht oder Vandalismus.],
    [Aktueller Energie- und Akkustatus], [Vermeidet Ausfälle einzelner Tonnen mitten in der Tour.],
    [Übergabefähige Dokumentation], [Sichert reibungslose Schichtwechsel und nachvollziehbare Tour-Berichte.],
  ),
  caption: [Operative Ziele der Primärpersona],
)

=== Frustrationen und Herausforderungen

Aus seiner Erfahrung mit bestehenden Systemen im Betrieb und im privaten Umfeld bringt Stefan eine Reihe von Erwartungen mit, die zugleich seine typischen Frustrationen markieren. Bestehende Branchensoftware empfindet er häufig als überladen. Häufig sind zentrale Statusinformationen tief in Untermenüs verborgen, was unter Zeitdruck im Fahrerhaus nicht praktikabel ist. Außerdem erlebt er häufig Brüche zwischen Disposition, Fahrzeug und Tonne: Informationen, die im Büro vorliegen, erreichen ihn auf der Tour erst verspätet oder gar nicht.

=== Technische Voraussetzungen und Endgeräte

Stefan ist kein passionierter Anwender komplexer Software, aber routinierter Nutzer alltagstauglicher digitaler Werkzeuge. Sein Smartphone bedient er sicher, mit Touch-Geräten im Fahrzeug ist er vertraut, da viele moderne Entsorgungsfahrzeuge bereits mit ähnlichen Bordsystemen ausgestattet sind. Komplexe Konfigurationsmenüs vermeidet er hingegen — sie kosten Zeit und führen aus seiner Erfahrung selten zu spürbaren Vorteilen. Er erwartet stattdessen eine klare, intuitive Oberfläche, die ihm die wichtigsten Informationen auf einen Blick liefert und einfache, sichere Interaktionen ermöglicht. Das Tablet im Fahrzeug ist sein primäres Endgerät für die Web-App, da es mobil, gut sichtbar und mit dem Fahrzeug verbunden ist. Ein Desktop-Arbeitsplatz im Betriebshof dient ergänzend für die Planung und Dokumentation.

=== Beispielhafter Interaktionsablauf

Ein typischer Schichtbeginn verläuft folgendermaßen. Stefan öffnet die Web-App auf seinem Tablet, sieht auf einer Karte alle 35 Tonnen seines Reviers eingefärbt nach Füllstand. Auffällig sind drei rot markierte Tonnen mit Werten über neunzig Prozent. Er klickt auf "Route planen" und erhält in unter einer Sekunde eine kompakte Tour mit acht Tonnen, die einen Füllstand über 60 Prozent aufweisen.

Während der Fahrt verfolgt Stefan auf der Karte die Bewegung des Fahrzeugs. Kurz vor dem Eintreffen an die Abholposition sendet der Server ein Signal an die angesteuerte Tonne, um diese an die Straße zu rufen. Die Tonne setzt sich darufhin in Bewegung, der Füllstand wird nach erfolgter Leerung durch den Müllwagen automatisch zurückgesetzt und das Fahrzeug fährt zur nächsten Position weiter. Mitten in der Tour erscheint im Sicherheits-Panel ein Hinweis auf einen mutmaßlichen Manipulationsversuch an einer noch nicht angefahrenen Tonne. Stefan öffnet kurz den Chat-Bereich, fragt: „Sperre Tonne 22 wegen Manipulationsverdacht." Der Agent quittiert die Aktion, das Fleet-Panel markiert die Tonne grau, und sie wird automatisch aus der weiteren Routenplanung ausgeschlossen.

=== Konsequenzen für das Interaktionsdesign der Web-App

Aus dem Profil von Stefan und seinem Arbeitsablauf lassen sich konkrete Designentscheidungen ableiten, die die Web-App spürbar prägen. Sie erklären, warum die Oberfläche bestimmten Prinzipien folgt und an welchen Stellen bewusst auf Komplexität verzichtet wurde.

#figure(
  table(
    columns: (1.5fr, 3.5fr),
    [*Persona-Eigenschaft*], [*Designkonsequenz*],
    [Geringe Toleranz gegenüber Fehlbedienung], [Aktionen mit echten Auswirkungen, etwa Sperren oder Fahrzeugbefehle, werden klar zurückgemeldet und sind reversibel.],
    [Schneller Überblick gefordert], [Drei-Spalten-Layout aus Fleet-Panel, Karte und Chat erlaubt simultanes Erfassen von Status, Räumlichkeit und aktuellen Aktionen ohne Navigationsschritte.],
    [Wechsel zwischen Disposition und Fahrt], [Karte und Liste sind die zentralen, jederzeit sichtbaren Elemente; Sekundärfunktionen wie Energie und Sicherheit sind als Tabs in einem Panel zusammengefasst.],
    [Reagieren auf Live-Ereignisse], [WebSocket-basierte Echtzeit-Updates, Alert-Banner für aktive Sicherheitsereignisse, sofortige Spiegelung von Aktionen in allen offenen Sichten.],
    [Begrenzte Technikaffinität], [Natürlichsprachliche Eingabe über den Chat-Agenten als alternativer Bedienpfad zu klassischen Schaltflächen.],
    [Realistische Tourenplanung], [Automatische Optimierung über 2-opt-Heuristik mit nachvollziehbarer Anzeige der Strecken-Ersparnis.],
    [Demo- und Schulungsszenario], [Simulationssteuerung mit Zeitraffer-Funktion, damit Tour-Abläufe in wenigen Minuten erlebbar werden.],
  ),
  caption: [Übersetzung der Persona-Eigenschaften in Designentscheidungen],
)

=== Sekundäre Anwender und Abgrenzung

Neben Stefan als Primärpersona profitieren weitere Rollen von der Web-App, ohne dass sie deren primäre Adressaten wären. Eine Werkstatt-Technikerin, die einzelne Tonnen wartet, kann das Energie-Panel nutzen, um Akku- und Solar-Daten zu prüfen. Ein Schichtleiter im Betriebshof verwendet die Übersicht primär für die Personal- und Touren-Planung. Anwohnerinnen und Anwohner sind keine direkten Anwender der Flottenmanagement-Web-App; ihre Interaktion mit dem System erfolgt ausschließlich über das Touch-Display an der Tonne selbst, das in einem späteren Kapitel separat betrachtet wird.

Diese Abgrenzung ist wichtig, weil sie verhindert, dass die Web-App versucht, alle möglichen Anwendergruppen gleichzeitig zu adressieren. Stattdessen folgt sie konsequent dem Bedarf des operativen Disponenten und Fahrers — alle weiteren Rollen werden über separate Schnittstellen oder zusätzliche, klar abgegrenzte Ansichten abgebildet.

#decision[
  *Entscheidung:* Die Flottenmanagement-Web-App ist primär für eine Person gestaltet, die gleichzeitig disponiert und fährt. Alle weiteren Rollen werden bewusst als sekundäre Anwender behandelt, um die Oberfläche fokussiert und mobil-tauglich zu halten.
]

#pagebreak()

== Monorepo-Struktur

#figure(
  table(
    columns: (1.5fr, 3.5fr),
    [*Ordner*], [*Rolle*],
    [`backend/`], [FastAPI-Backend mit SQLite-Datenbank, REST-Endpunkten, WebSocket, Routenplanung und Agent.],
    [`frontend/`], [Next.js-15-Dashboard mit Karte, Fleet Panel, Chat, Energie- und Sicherheitsansicht.],
    [`simulator/`], [Python-Simulatoren für Füllstand, Energie, Sicherheitsereignisse und Abholfahrzeug.],
    [`docs/`], [Architektur- und API-Vertrag zwischen Backend und späterer Hardware.],
    [`docker-compose.yml`], [Lokale Orchestrierung von Backend und Frontend.],
  ),
  caption: [Struktur des neuen `smart-bin`-Prototyps],
)

== Architekturentscheidung: feste Standorte statt GPS

Eine zentrale Entscheidung war, auf GPS-Ortung zu verzichten. Mülltonnen stehen in der Regel an bekannten Adressen. Deshalb werden Koordinaten einmalig in der Datenbank hinterlegt. Die Hardware muss später nur Statusdaten wie Füllstand, Akku, Sicherheitsereignisse und gegebenenfalls Fahrzustand übertragen.

#decision[
  *Entscheidung:* Die Web-App modelliert Tonnen über feste Adressen und Koordinaten. Dadurch bleibt die Hardware einfacher, und die Flottenlogik kann trotzdem echte Karten- und Routenfunktionen nutzen.
]

== Architekturentscheidung: Simulation vor Hardwareintegration

Da die echte Hardware nicht durchgehend verfügbar beziehungsweise noch nicht vollständig integriert ist, simuliert `smart-bin` mehrere Systemteile. Die Simulation ist kein Ersatz für echte Tests, aber sie erlaubt eine frühzeitige Entwicklung der App-Logik: Live-Daten, Routen, Truck-Bewegung, Füllstandsdynamik, Ladeleistungen und Sicherheitsalerts können ohne angeschlossene Tonne geprüft werden.

= Backend

== Technologie und Aufbau

Das Backend basiert auf FastAPI, SQLAlchemy, SQLite und Pydantic Settings. Beim Start initialisiert es die Datenbank und legt Beispieldaten für Tonnen im Raum Soest an. Die API ist in Router für Tonnen, Routen, Sicherheit, Energie, Fahrzeug, Commands, Agent, Simulation und WebSocket aufgeteilt.

#figure(
  table(
    columns: (1.6fr, 3.2fr),
    [*Modul*], [*Aufgabe*],
    [`main.py`], [Initialisiert FastAPI, CORS, Datenbank-Lifespan und Router.],
    [`database.py`], [SQLAlchemy-Engine, Session-Verwaltung und Seed-Daten für Soester Tonnen.],
    [`models/`], [Datenmodelle für Tonnen, Routen, Commands und Sicherheitsereignisse.],
    [`routers/`], [REST-, SSE- und WebSocket-Endpunkte.],
    [`services/routing.py`], [OSRM-Anbindung für echte Straßenrouten mit Fallback auf Luftlinie.],
    [`agent/`], [Tool-calling-Agent für natürliche Sprache und operative Aktionen.],
  ),
  caption: [Backend-Bausteine],
)

== Datenmodell

Das Datenmodell ist bewusst klein gehalten, deckt aber die Kernobjekte des Systems ab.

#figure(
  table(
    columns: (1.4fr, 3.4fr),
    [*Tabelle*], [*Inhalt*],
    [`bins`], [Name, Adresse, Koordinaten, Füllstand, Akku, Ladeleistung- und Zustand, Status, Sperrstatus und letztes Update.],
    [`routes`], [Route mit geordneten Tonnen-IDs, Distanz, Dauer, GeoJSON-Geometrie, Abschlussstatus und optionaler Agentenbegründung.],
    [`security_events`], [Manipulations- oder Fremdnutzungsereignisse mit Tonne, Typ, Zeitstempel und Quittierungsstatus.],
    [`commands`], [Warteschlange für Kommandos an einzelne Tonnen, inklusive Parametern und ACK-Zeitpunkt.],
  ),
  caption: [Persistente Kernobjekte],
)

== API-Funktionen

Die REST-API ist so aufgebaut, dass sie sowohl vom Frontend als auch später von einem Raspberry Pi oder Pico-Gateway genutzt werden kann.

#figure(
  table(
    columns: (1.8fr, 3.2fr),
    [*Endpunktgruppe*], [*Funktion*],
    [`/bins`], [Alle Tonnen abrufen, einzelne Tonne abrufen, partielle Statusupdates schreiben.],
    [`/routes`], [Route planen, letzte Route abrufen und Route als abgeschlossen markieren.],
    [`/security`], [Sicherheitsereignisse abrufen oder erzeugen, Tonne sperren, entsperren und Alerts quittieren.],
    [`/energy`], [Akku- und Ladezustände abrufen, Docking-Status setzen.],
    [`/truck`], [Simulierten Truck-Status lesen, Position schreiben und Start/Pause/Stop setzen.],
    [`/bins/{id}/command`], [Kommandos an eine Tonne einreihen, pending Commands pollen und ACKs zurückmelden.],
    [`/agent/chat`], [Server-Sent-Events-Streaming für den Chat-Agenten.],
    [`/ws/live`], [Live-Payload aus Tonnen, Alerts und Truck im Zwei-Sekunden-Takt.],
  ),
  caption: [API-Überblick],
)

== Routenplanung

Die Routenplanung filtert zunächst gesperrte Tonnen und Tonnen unterhalb eines Füllstand-Schwellwerts von 60 Prozent heraus. Danach wird ab dem Depot eine Nearest-Neighbor-Reihenfolge gebildet. Für die resultierende Rundfahrt wird über OSRM eine echte Straßenroute mit Distanz, Dauer und GeoJSON-Geometrie angefragt. Falls OSRM nicht erreichbar ist, erzeugt das Backend eine gerade Fallback-Route.

Diese Lösung ist für den Prototyp pragmatisch: Sie ist nachvollziehbar, schnell implementierbar und zeigt bereits den Nutzen von datenbasierter Abholplanung. Für eine spätere Version könnte der Algorithmus durch eine bessere Optimierung oder externe Tourenplanung ersetzt werden.

== Agentische Steuerung

Der Agent im Backend nutzt LangChain mit Groq beziehungsweise Llama 3.3 70B und kann über Tools echte Backend-Aktionen auslösen. Er kann Tonnenstatus abrufen, Routen planen, den Truck starten, Tonnen sperren oder entsperren, Sicherheitsereignisse prüfen und Energiedaten auswerten.

Die Systemregeln priorisieren Tonnen mit hohem Füllstand, behandeln Akku als Monitoring-Wert und reagieren bei Manipulationsereignissen mit Sperrlogik. Der Agent ist damit nicht nur ein Chatbot, sondern eine natürliche Bedienoberfläche für operative Flottenaktionen.

= Frontend

== Technologie und Oberfläche

Das Frontend basiert auf Next.js 15, React 19, TypeScript, Tailwind CSS 4, React Leaflet, OpenStreetMap und Lucide Icons. Die Startseite leitet direkt auf `/dashboard` weiter. Das Dashboard ist als Arbeitsoberfläche aufgebaut und besteht aus Live-Status, Kartenansicht und Seitenpanel.

== Dashboard-Aufbau

#figure(
  table(
    columns: (1.5fr, 3.4fr),
    [*Bereich*], [*Funktion*],
    [Header], [Titel, Live-Status, Simulationsgeschwindigkeit und Button zur Routenplanung.],
    [AlertBanner], [Roter Warnbereich bei offenen Sicherheitsereignissen.],
    [FleetPanel], [Liste aller Tonnen sortiert nach Füllstand mit Akku- und Ladezustandsanzeige und Sperrstatus.],
    [MapView], [OpenStreetMap-Karte mit Tonnenmarkern, Depot, Route und animiertem Truck.],
    [Chat], [Streaming-Chat mit Tool-Call-Anzeige und Quick Prompts.],
    [Energie], [Gesamt Ladeleistung, durchschnittlicher Akkustand und Detailwerte je Tonne.],
    [Sicherheit], [Offene Ereignisse, Sperren und Quittieren.],
  ),
  caption: [Frontend-Komponenten],
)

== Live-Datenfluss

Die Web-App erhält Live-Daten über `WS /ws/live`. Der Hook `useLiveData()` stellt automatisch eine WebSocket-Verbindung her, verarbeitet JSON-Payloads und reconnectet nach Verbindungsabbrüchen. Dadurch bleiben Karte, Fleet Panel, Energieansicht und Sicherheitsansicht konsistent.

#infobox[
  *Live-Payload:* Das Backend sendet alle zwei Sekunden Tonnenliste, offene Alerts und optional die Truck-Position. Das Frontend rendert daraus Marker, Warnungen, Statuskarten und Bewegungsanimationen.
]

== Karten- und Routenvisualisierung

Die Karte nutzt OpenStreetMap-Tiles und React Leaflet. Tonnen werden als farbcodierte Marker dargestellt: Grün für niedrigen, Gelb für mittleren und Rot für hohen Füllstand. Kritisch volle Tonnen erhalten eine visuelle Pulsierung; gesperrte Tonnen werden grau dargestellt. Eine geplante Route wird als GeoJSON-Linie gerendert, wenn OSRM-Geometrie vorhanden ist. Der simulierte Truck wird als eigener Marker animiert und zwischen WebSocket-Updates geglättet.

== Chat-Interface

Das Chat-Interface ist an den Agent-Endpunkt angebunden und verarbeitet Server-Sent Events. Text wird tokenweise gestreamt, Tool-Aufrufe werden als eigene Karten angezeigt. Dadurch ist sichtbar, wann der Agent tatsächlich eine Route plant, den Truck startet oder Sicherheitsaktionen ausführt.

= Simulation und Demo-Betrieb

== Simulationsmodule

Die Simulatoren ermöglichen eine vollständige Demo ohne angeschlossene Hardware.

#figure(
  table(
    columns: (1.7fr, 3.1fr),
    [*Script*], [*Simuliertes Verhalten*],
    [`mock_bins.py`], [Füllstände steigen langsam an und skalieren mit der Demo-Geschwindigkeit.],
    [`mock_energy.py`], [Ladeleistung folgt einer Sinuskurve, Akkus laden oder entladen sich.],
    [`mock_security.py`], [Erzeugt zufällige Öffnungs- oder Fremdnutzungsereignisse.],
    [`mock_truck.py`], [Fährt entlang der letzten OSRM-Route, leert Tonnen beim Erreichen und markiert die Route als abgeschlossen.],
  ),
  caption: [Simulationsbausteine],
)

== Zeitraffersteuerung

Über `/sim/speed` kann die Demo-Geschwindigkeit zwischen 0,5-fach und 20-fach gesetzt werden. Das Frontend bietet dafür Buttons mit 1x, 5x, 10x und 20x. Die Simulatoren pollen den Wert und passen Tick-Rate beziehungsweise Bewegungsfortschritt an. Damit lassen sich Routen, Füllstandsdynamik und Abholprozesse in kurzer Zeit zeigen.

= Schnittstelle zur Hardware

== API-Vertrag

Der API-Vertrag in `docs/api_contract.md` definiert, wie ein Raspberry Pi oder ein Hardware-Gateway später mit dem Backend sprechen soll. Tonnen senden regelmäßig oder bei Änderungen Statusupdates an `/bins/{bin_id}/update`. Sicherheitsereignisse werden sofort an `/security/events` gesendet.

Beispielhafte Statusdaten:

```json
{
  "fill_level": 87,
  "battery": 64,
  "timestamp": "2026-04-10T14:32:00Z"
}
```

Optionale Energiedaten können Ladeleistung und Ladezustand ergänzen:

```json
{
  "fill_level": 87,
  "battery": 64,
  "charging_output_w": 11.4,
  "is_charging": true
}
```

== Command-Queue

Für Befehle an einzelne Tonnen existiert eine Command-Queue. Das Backend kann Aktionen wie `lock`, `unlock`, `empty` oder spätere Spezialbefehle einreihen. Eine Tonne beziehungsweise ein Gateway kann regelmäßig `pending-command` abfragen und anschließend per ACK bestätigen. Diese Polling-Logik ist robust genug für einen Prototyp, weil die Hardware nicht dauerhaft eine eingehende Serververbindung halten muss.

== Integrationsstrategie

Die vorgesehene Integrationsstrategie ist inkrementell:

1. Hardware sendet zunächst nur Füllstand und Akku.
2. Sicherheitsereignisse werden als eigener Pfad ergänzt.
3. Commands werden über Polling und ACKs eingebunden.
4. Fahrzustände und Position beziehungsweise Zustandsübergänge werden in die Live-Daten aufgenommen.
5. Danach wird getestet, ob der Agent operative Aktionen zuverlässig auslösen darf.


#pagebreak()

= Nutzerinteraktion und Touchpanel

== Rolle des Touchpanels im Gesamtsystem

Das Touchpanel bildet die lokale Benutzerschnittstelle der Smarten Mülltonne 2.0. Während die Flottenmanagement-Web-App für die zentrale Überwachung und Steuerung mehrerer Mülltonnen vorgesehen ist, ermöglicht das Touchpanel die direkte Interaktion mit einer einzelnen Mülltonne am jeweiligen Standort. Beide Bedienebenen ergänzen sich und verbinden die Nutzerinnen und Nutzer mit der lokalen Hardwaresteuerung und dem digitalen Managementsystem.

Über das Touchpanel können zentrale Betriebsfunktionen ausgelöst und aktuelle Systemzustände eingesehen werden. Dazu gehören das Starten und Stoppen der autonomen Fahrt sowie die Funktion "Nach Hause", mit der die Mülltonne zu ihrem definierten Standplatz zurückkehrt.

Der Startbildschirm zeigt außerdem Datum und Uhrzeit, den aktuellen Akkustand, den Füllstand, die zugeordnete Adresse und den Verbindungsstatus. Erkannte Hindernisse, technische Fehler und Sicherheitsereignisse werden ebenfalls lokal dargestellt. Relevante Zustände werden gleichzeitig an die Flottenmanagement-Web-App übertragen. Dadurch bleiben lokale Bedienung und zentrale Überwachung miteinander verbunden.

#figure(
  table(
    columns: (1.45fr, 2.3fr, 2.3fr),
    [*Bereich*], [*Darstellung und Bedienung am Touchpanel*], [*Verbindung zur Web-App*],

    [Fahrsteuerung],
    [Starten und Stoppen der autonomen Fahrt sowie Rückkehr über die Funktion "Nach Hause".],
    [Der aktuelle Fahr- und Betriebszustand wird zentral sichtbar.],

    [Allgemeine Informationen],
    [Anzeige von Datum, Uhrzeit und zugeordneter Adresse der Mülltonne.],
    [Die Adresse ermöglicht die eindeutige Zuordnung innerhalb der Flottenübersicht.],

    [Akku und Füllstand],
    [Darstellung des Akkustands und des gemessenen Füllstands als Prozentwerte.],
    [Die Werte können für Monitoring und Abholplanung verwendet werden.],

    [Verbindungsstatus],
    [Ein Statussymbol zeigt die Verbindung zum digitalen Managementsystem an.],
    [Die Erreichbarkeit der Mülltonne kann zentral kontrolliert werden.],

    [Fehler und Sicherheit],
    [Hindernisse, technische Fehler und sicherheitsrelevante Zustände werden lokal angezeigt.],
    [Die Ereignisse werden zusätzlich in der Web-App dargestellt.],
  ),
  caption: [Funktionen des Touchpanels und ihre Verbindung zum Flottenmanagement],
)

 Für das Bedienkonzept ist entscheidend, dass die lokale Benutzeroberfläche mit der Hardwaresteuerung verbunden ist und relevante Systemzustände mit der Web-App synchronisiert werden.

#decision[
  *Systementscheidung:* Das Touchpanel und die Flottenmanagement-Web-App wurden als zwei sich ergänzende Bedienebenen konzipiert. Das Touchpanel ermöglicht die direkte lokale Interaktion mit einer einzelnen Mülltonne. Die Web-App übernimmt dagegen die zentrale Überwachung und Steuerung des gesamten Systems.
]

== Zielgruppen und Nutzungskontext

Das Touchpanel richtet sich grundsätzlich an Bewohnerinnen und Bewohner aller Altersgruppen, die eine Smarte Mülltonne im privaten oder gemeinschaftlichen Wohnumfeld nutzen. Die Benutzeroberfläche wurde deshalb nicht für eine eng abgegrenzte technische Nutzergruppe, sondern als allgemein verständliche und möglichst barrierearme Schnittstelle konzipiert.

Ein besonderer Fokus liegt auf älteren Menschen und Personen mit eingeschränkter Mobilität. Für diese Nutzergruppen kann das manuelle Bewegen einer gefüllten Mülltonne bis zur Straße eine erhebliche körperliche Belastung darstellen. Durch die lokale Fahrsteuerung und die ergänzende Fernsteuerung soll die Mülltonne ohne großen körperlichen Aufwand zur Abholposition bewegt und nach der Leerung wieder zu ihrem Standplatz zurückgerufen werden können.

Die Interaktion mit dem Touchpanel findet überwiegend im Außenbereich und häufig innerhalb eines kurzen Zeitfensters statt. Typische Nutzungssituationen sind das Einwerfen von Abfall, das Kontrollieren von Füllstand und Akkustand, das Starten der Fahrt zur Abholposition, die Rückkehr nach der Leerung sowie die Reaktion auf Hindernisse, Fehler- oder Sicherheitsmeldungen.

Da das Display bei unterschiedlichen Lichtverhältnissen erkennbar bleiben muss, wurde für die Nutzung bei Tageslicht ein eigener Tagmodus berücksichtigt. Dieser unterstützt eine kontrastreiche Darstellung der zentralen Informationen und Bedienelemente. Ergänzend ermöglicht die Web-App eine ortsunabhängige Kontrolle des Systems, wenn eine direkte Bedienung an der Mülltonne nicht möglich oder nicht sinnvoll ist.

#figure(
  table(
    columns: (1.55fr, 2.15fr, 2.35fr),
    [*Nutzergruppe*], [*Typischer Nutzungskontext*], [*Zentrales Bedürfnis*],

    [Bewohnerinnen und Bewohner],
    [Direkte Nutzung der Mülltonne im privaten oder gemeinschaftlichen Wohnumfeld.],
    [Einfache Bedienung und schneller Zugriff auf die wichtigsten Funktionen.],

    [Ältere Menschen],
    [Bereitstellung und Rückholung der Mülltonne ohne hohe körperliche Belastung.],
    [Verständliche Navigation, gut erkennbare Zustände und wenige Bedienschritte.],

    [Personen mit eingeschränkter Mobilität],
    [Lokale oder ortsunabhängige Steuerung der Mülltonne.],
    [Reduzierung manueller Wege und körperlicher Anstrengung.],

    [Service- und Entsorgungspersonal],
    [Kontrolle von Betriebszuständen, Fehlern oder Sicherheitsmeldungen direkt vor Ort.],
    [Schneller Überblick über den Zustand der einzelnen Mülltonne.],
  ),
  caption: [Zielgruppen und Nutzungskontexte des Touchpanels],
)

#infobox[
  *Zielgruppenentscheidung:* Das Touchpanel wurde als allgemein verständliche Schnittstelle für Bewohnerinnen und Bewohner konzipiert. Die besonderen Bedürfnisse älterer Menschen und Personen mit eingeschränkter Mobilität werden dabei als Maßstab für eine möglichst barrierearme Bedienung verwendet, ohne andere Nutzergruppen auszuschließen.
]

== Anforderungen an die lokale Bedienung

Aus den Zielgruppen und den typischen Nutzungssituationen wurden konkrete Anforderungen an die lokale Bedienung abgeleitet. Das Touchpanel muss auf einem kleinen Display schnell erfassbar sein, direkte Rückmeldungen geben und gleichzeitig vor unbeabsichtigten oder unberechtigten Eingriffen schützen. Da die Bedienung häufig im Außenbereich und nur für kurze Zeit erfolgt, müssen die wichtigsten Informationen ohne eine lange Navigation sichtbar sein.

Statusinformationen wie Akkustand, Füllstand, Standort, Uhrzeit und Verbindungsstatus werden bereits auf dem Startbildschirm dargestellt. Dadurch können Nutzerinnen und Nutzer den Zustand der Mülltonne kontrollieren, ohne sich zunächst anmelden oder durch mehrere Menüs navigieren zu müssen. Steuerungsfunktionen mit direkter Auswirkung auf das System werden dagegen über eine PIN-Eingabe geschützt.

#figure(
  table(
    columns: (1.55fr, 2.25fr, 2.25fr),
    [*Anforderung*], [*Begründung*], [*Umsetzung im Bedienkonzept*],

    [Schnelle Erfassbarkeit],
    [Die Interaktion erfolgt häufig nur für wenige Sekunden.],
    [Zentrale Zustände werden direkt auf dem Startbildschirm angezeigt.],

    [Gute Sichtbarkeit],
    [Das Display wird im Außenbereich und bei unterschiedlichen Lichtverhältnissen verwendet.],
    [Kontrastreiche Gelb-Grau-Gestaltung sowie ein für Tageslicht vorgesehener Tagmodus.],

    [Einfache Navigation],
    [Auch Personen ohne technische Vorkenntnisse müssen die Funktionen verstehen können.],
    [Reduzierte Menüstruktur, Swipe- beziehungsweise Pfeilnavigation und ein deutlich sichtbarer Zurück-Button.],

    [Eindeutige Rückmeldung],
    [Nutzerinnen und Nutzer müssen erkennen, ob eine Aktion erfolgreich ausgelöst wurde.],
    [Separate Bestätigungsanzeigen wie "Auswahl bestätigt", "Meldung gesendet" oder "Verbindung hergestellt".],

    [Verständliche Fehlerkommunikation],
    [Hindernisse oder technische Fehler dürfen nicht ausschließlich über einen Farbwechsel kommuniziert werden.],
    [Kombination aus Farbe, Symbol und Text für Zustände wie "Hindernis erkannt" oder "Linie verloren".],

    [Zugriffsschutz],
    [Fahr-, Sicherheits- oder Systemfunktionen dürfen nicht unbeabsichtigt oder durch unbefugte Personen ausgelöst werden.],
    [Statusinformationen bleiben direkt sichtbar; geschützte Bedienfunktionen werden erst nach der PIN-Eingabe freigegeben.],

    [Multimodales Feedback],
    [Kritische Situationen müssen auch dann wahrnehmbar sein, wenn der Bildschirm nicht dauerhaft betrachtet wird.],
    [Visuelle Statusanzeigen werden bei kritischen Ereignissen durch akustisches Feedback über den Buzzer ergänzt.],
  ),
  caption: [Anforderungen an die lokale Bedienung und ihre Umsetzung im Touchpanel],
)

Die Farbcodierung unterstützt die schnelle Orientierung, ist jedoch nicht der einzige Informationsträger. Gelb kennzeichnet aktive Elemente, ausgewählte Funktionen oder wichtige Hinweise. Rot wird für Fehler- und Gefahrenzustände verwendet, während Grün einen regulären beziehungsweise verbundenen Zustand signalisiert. Symbole und kurze Textmeldungen ergänzen die Farben, damit die Bedeutung auch ohne vorherige Einweisung verständlich bleibt.

#decision[
  *Interaktionsentscheidung:* Allgemeine Statusinformationen sollen unmittelbar zugänglich sein. Funktionen mit Auswirkungen auf Fahrt, Sicherheit oder Systemzustand werden dagegen durch PIN-Eingabe, eindeutige Auswahl und anschließende Bestätigung abgesichert.
]

== Iterativer Designprozess

Die Benutzeroberfläche des Touchpanels entstand nicht in einem einzelnen Entwurf, sondern wurde in mehreren aufeinander aufbauenden Gestaltungsphasen entwickelt. Ausgangspunkt waren die zuvor definierten Use Cases und Nutzungsszenarien. Darauf aufbauend wurden erste Skizzen, Wireframes, Wireflows und User Flows erstellt, um die benötigten Funktionen, möglichen Navigationswege und Rückmeldungen des Systems sichtbar zu machen.

Im Verlauf des Projekts wurden unterschiedliche horizontale, vertikale und visuelle Interface-Ansätze entwickelt. Die Entwürfe wurden innerhalb des Teams besprochen und anhand der Anforderungen an Verständlichkeit, Sichtbarkeit, Zugriffsschutz und Anzahl der notwendigen Bedienschritte bewertet. Zusätzlich flossen Rückmeldungen des Hardwareteams zu Displaygröße und technischen Einschränkungen sowie Feedback aus der Projektbetreuung in die Weiterentwicklung ein.

Die einzelnen Entwürfe dienten daher nicht nur als visuelle Varianten. Mit ihnen wurde geprüft, wie viele Funktionen auf dem begrenzten Display sinnvoll dargestellt werden können und wie Nutzerinnen und Nutzer zwischen Statusanzeige, Fahrsteuerung, Wartung, Sicherheitsfunktionen und Fehlermeldungen navigieren.

#figure(
  image("touchpanel_entwurfsuebersicht.png", width: 100%),
  caption: [Übersicht der untersuchten Wireframes, Navigationsvarianten und Funktionsabläufe],
)

=== Erste Entwurfsphase: Horizontale und vertikale Navigationsvarianten

In der ersten Entwurfsphase wurde eine bewusst reduzierte, skizzenhafte Benutzeroberfläche entwickelt. Einzelne Funktionen wie Füllstands- und Akkuanzeige, PIN-Eingabe, Deckelsteuerung, Fahrt zur Abholposition, Rückkehr zum Standplatz, Problemmeldung und Wartung wurden zunächst auf getrennte Screens verteilt.

Für die Navigation wurden unterschiedliche Varianten untersucht. In der horizontalen Variante wechselten die Nutzerinnen und Nutzer über Pfeile beziehungsweise eine lineare Abfolge zwischen den einzelnen Funktionsseiten. Dieser Ansatz stellte jeweils nur wenige Inhalte gleichzeitig dar und ermöglichte dadurch große Symbole, gut erkennbare Schaltflächen und eindeutige Bestätigungsanzeigen.

Parallel dazu wurden vertikale und kompaktere Varianten entwickelt. Dabei wurden Statusinformationen und Funktionsbereiche stärker auf einer Oberfläche gebündelt. Seitlich oder untereinander angeordnete Symbole ermöglichten einen direkteren Wechsel zwischen Deckelsteuerung, Problemmeldung und Wartungsfunktionen.

#figure(
  align(
    center,
    image("touchpanel_vertikal.png", width: 48%),
  ),
  caption: [Untersuchte vertikale und kompakte Navigationsvarianten],
)

#figure(
  table(
    columns: (1.45fr, 2.35fr, 2.25fr),
    [*Variante*], [*Vorteil*], [*Erkannte Schwäche*],

    [Horizontale Navigation],
    [Große Bedienelemente und klare Konzentration auf jeweils eine Funktion.],
    [Viele einzelne Screens und entsprechend lange Navigationswege.],

    [Vertikale beziehungsweise kompakte Navigation],
    [Mehrere Funktionsbereiche können auf einer Oberfläche erreicht werden.],
    [Die kleine Displayfläche wird schneller überladen und einzelne Symbole werden kleiner.],
  ),
  caption: [Vergleich der ersten horizontalen und vertikalen Navigationsvarianten],
)

Obwohl die ersten Entwürfe visuell einfach und grundsätzlich verständlich waren, entstand durch die große Anzahl einzelner Screens ein umfangreicher User Flow. Häufig benötigte Funktionen waren teilweise erst nach mehreren Navigationsschritten erreichbar. Gleichzeitig zeigte die kompakte vertikale Variante, dass zu viele Funktionen auf einer kleinen Fläche die Übersichtlichkeit und Treffergenauigkeit der Bedienelemente reduzieren.

Die erste Entwurfsphase machte damit den zentralen Zielkonflikt sichtbar: Eine starke Aufteilung erzeugt zu viele Screens, während eine zu starke Verdichtung das kleine Display überlädt. Diese Erkenntnis bildete die Grundlage für die folgenden Designiterationen.

=== Zweite Entwurfsphase: Pixelästhetik und kompakte Navigation

In der zweiten Entwurfsphase wurde eine pixelorientierte Benutzeroberfläche entwickelt. Ausgangspunkt war die Überlegung, dass eine reduzierte Pixelästhetik grundsätzlich gut zu einem kleinen Display und einer begrenzten Bildschirmauflösung passen kann. Gleichzeitig sollte bewusst eine spielerische und nostalgische Gestaltungsrichtung erprobt werden, um zu untersuchen, ob sich die technische Mülltonne dadurch zugänglicher und emotionaler darstellen lässt.

Im Gegensatz zu den umfangreichen linearen Screen-Flows der ersten Entwurfsphase wurde hier erstmals eine kompaktere menübasierte Navigation eingesetzt. Der zentrale Systemzustand wurde gemeinsam mit der Mülltonne auf einer Hauptansicht dargestellt. Direkt erreichbare Symbole für Startseite, Fahrsteuerung und Einstellungen reduzierten die Anzahl der benötigten Navigationsschritte.

Die größeren Icons und die deutlich voneinander unterscheidbaren Statusfarben funktionierten auf dem kleinen Bildschirm besonders gut. Zustände wie "Bereit" und "Akku niedrig" konnten durch die Kombination aus Farbe, Text, Batterieanzeige und veränderter Darstellung der Mülltonne schnell unterschieden werden. Auch die dauerhaft sichtbare Akkuanzeige erwies sich als sinnvoll.

#figure(
  align(
    center,
    image("touchpanel_pixel.jpeg", width: 50%),
  ),
  caption: [Pixelorientierter Entwurf mit kompakter Navigation und farbcodierten Systemzuständen],
)

Trotz dieser Vorteile wurde die Pixelästhetik nicht als finale Gestaltungsrichtung übernommen. Die Oberfläche wirkte im Verhältnis zum technischen und kommunalen Anwendungskontext teilweise zu spielerisch. Gleichzeitig entstand ein deutlicher visueller Unterschied zur modern gestalteten Flottenmanagement-Web-App. Für das Gesamtsystem war jedoch eine zusammenhängende Designsprache zwischen lokaler Bedienoberfläche und zentraler Web-Anwendung sinnvoller.

Die zweite Entwurfsphase wurde deshalb nicht verworfen, ohne ihre Erkenntnisse weiterzuverwenden. Die reduzierte Menüstruktur, die größeren Icons, die kompakte Akkuanzeige und die eindeutige farbliche Unterscheidung von Systemzuständen wurden als positive Elemente erkannt und in die Entwicklung der finalen Benutzeroberfläche übertragen.

#infobox[
  *Übernommene Erkenntnisse:* Die Pixelästhetik wurde nicht fortgeführt, die kompaktere Navigation, größeren Symbole, permanente Akkuanzeige und klare Statusfarben beeinflussten jedoch direkt den finalen Entwurf.
]

=== Finaler Entwurf: Modulare Funktionsnavigation

Der finale Entwurf entstand als Synthese der vorangegangenen Gestaltungsphasen und der dazu erhaltenen Rückmeldungen. Funktionierende Elemente der früheren Varianten wurden übernommen und weiterentwickelt. Gleichzeitig sollten die erkannten Probleme, insbesondere lange Navigationswege und eine Überladung der kleinen Displayfläche, vermieden werden.

Die Entwürfe, Wireframes und Wireflows wurden im UX/UI-Arbeitspaket mit Figma entwickelt und schrittweise zu einem gemeinsamen Bedienkonzept zusammengeführt. Dadurch konnten unterschiedliche Bildschirmaufteilungen, Navigationsvarianten und Systemzustände bereits vor der technischen Umsetzung visuell überprüft und miteinander verglichen werden.

Für die visuelle Weiterentwicklung wurde eine neue digitale Darstellung der Smarten Mülltonne gestaltet. Diese ersetzte die zuvor verwendete skizzenhafte beziehungsweise pixelorientierte Darstellung und bildete die Grundlage für eine modernere Benutzeroberfläche, die gestalterisch besser mit der Flottenmanagement-Web-App harmoniert.

Auf dieser visuellen Grundlage wurden die Navigationsstruktur, die Wireflows und der dazugehörige User Flow weiterentwickelt. Die einzelnen Funktionen wurden in logisch zusammengehörige Module gegliedert. Allgemeine Statusinformationen bleiben unmittelbar sichtbar, während Fahr-, Sicherheits-, Verbindungs-, Energie- und Diagnosefunktionen über geschützte Bedienbereiche erreichbar sind.

Anschließend wurde der Entwurf innerhalb des UX/UI- und Softwareteams hinsichtlich seiner technischen Umsetzbarkeit auf dem vorhandenen Touchdisplay sowie seiner Verbindung zur Hardware- und Web-App-Struktur überprüft. Bewertet wurden insbesondere die Anzahl der notwendigen Navigationsschritte, die Größe der Bedienelemente, die Sichtbarkeit wichtiger Systemzustände und die technische Realisierbarkeit der vorgesehenen Funktionen. Auf Grundlage dieser gemeinsamen Prüfung wurde die modulare Funktionsnavigation als finaler Entwurf ausgewählt.


#figure(
  table(
    columns: (1.45fr, 2.25fr, 2.25fr),
    [*Ausgangspunkt*], [*Gewonnene Erkenntnis*], [*Übernahme in den finalen Entwurf*],

    [Erste Wireframes],
    [Große Symbole und eindeutige Bestätigungen erleichtern die Bedienung.],
    [Große Funktionskarten, klare Beschriftungen und separate Bestätigungsanzeigen.],

    [Horizontale und vertikale Varianten],
    [Zu viele einzelne Screens verlängern den Bedienweg; eine zu starke Verdichtung überlädt das Display.],
    [Gliederung der Funktionen in logisch zusammengehörige, modular erreichbare Bereiche.],

    [Pixelorientierter Entwurf],
    [Kompakte Navigation, permanente Akkuanzeige und deutliche Statusfarben funktionieren auf dem kleinen Display gut.],
    [Übernahme der kompakten Statusdarstellung, größeren Symbole und farblichen Zustandsunterscheidung.],

    [Feedback und technische Prüfung],
    [Die Oberfläche muss mit Displaygröße, Hardwarefunktionen und Web-App-Struktur vereinbar sein.],
    [Modernisierte Designsprache und gemeinsam überprüfter User Flow.],
  ),
  caption: [Übertragung der Erkenntnisse aus den Entwurfsphasen in das finale Bedienkonzept],
)

Der finale Entwurf folgt einer modularen Funktionsnavigation. Der Startbildschirm bietet einen direkten Überblick über Füllstand, Akkustand, zugeordnete Adresse, Verbindungsstatus und aktuelle Systemmeldungen. Diese Informationen können ohne vorherige PIN-Eingabe eingesehen werden.

Nach der PIN-Eingabe erhalten die Nutzerinnen und Nutzer Zugriff auf die vorgesehenen Funktionsmodule. Dazu gehören unter anderem Fahrsteuerung, Deckelsteuerung, Sicherheit, Verbindung, Problemmeldung, Energieverwaltung und Diagnose. Aktionen mit Auswirkungen auf Fahrt, Sicherheit oder Systemzustand werden durch eindeutige Bestätigungsanzeigen abgeschlossen.

#figure(
  image("touchpanel_final_wireflow.png", width: 30%),
  caption: [In Figma entwickelter finaler Wireflow der modularen Funktionsnavigation],
)

#decision[
  *Finale Designentscheidung:* Die modulare Funktionsnavigation wurde ausgewählt, weil sie die Verständlichkeit der ersten Wireframes, die kompakte Statusdarstellung des Pixelentwurfs und eine moderne, zur Web-App passende Designsprache miteinander verbindet. Die endgültige Entscheidung erfolgte nach gemeinsamer Prüfung der Nutzerführung und technischen Umsetzbarkeit.
]

== Informationsarchitektur und User Flow

Die Informationsarchitektur des finalen Touchpanel-Entwurfs trennt frei zugängliche Statusinformationen von geschützten Bedienfunktionen. Dadurch können Nutzerinnen und Nutzer den aktuellen Zustand der Mülltonne schnell kontrollieren, ohne sich zunächst durch mehrere Menüs bewegen oder eine PIN eingeben zu müssen.

Die Bedienstruktur ist in vier Ebenen gegliedert: Start- und Statusbereich, Zugriffsschutz, modulare Funktionsnavigation sowie Rückmeldung und Bestätigung. Diese Gliederung reduziert die Anzahl gleichzeitig sichtbarer Inhalte und sorgt dafür, dass jede Ansicht eine klar erkennbare Aufgabe besitzt.

#figure(
  table(
    columns: (1.25fr, 1.8fr, 2.85fr),
    [*Ebene*], [*Funktion*], [*Inhalt*],

    [1],
    [Start und Status],
    [Anzeige des aktuellen Systemzustands, Füllstands, Akkustands, Standorts und Verbindungsstatus.],

    [2],
    [Zugriffsschutz],
    [PIN-Eingabe vor dem Zugriff auf geschützte Steuerungs- und Systemfunktionen.],

    [3],
    [Funktionsnavigation],
    [Navigation zwischen den logisch gruppierten Bedienmodulen über Swipe-Gesten beziehungsweise Pfeile.],

    [4],
    [Rückmeldung],
    [Bestätigung erfolgreicher Aktionen sowie Darstellung von Fehler-, Warn- und Sicherheitszuständen.],
  ),
  caption: [Ebenen der Informationsarchitektur des Touchpanels],
)

Der reguläre User Flow beginnt auf dem Start- beziehungsweise Statusscreen. Dort werden die wichtigsten Informationen ohne vorherige Anmeldung dargestellt. Über den Zugang zu den Bedienfunktionen gelangt die Nutzerin oder der Nutzer zur PIN-Eingabe. Erst nach erfolgreicher Eingabe werden die geschützten Funktionsmodule freigegeben.

Innerhalb der Funktionsnavigation können die einzelnen Module über eine Swipe-Geste oder durch das Anklicken eines Pfeils gewechselt werden. Jedes Modul bündelt inhaltlich zusammengehörige Aktionen. Ein deutlich sichtbarer "Zurück"-Button ermöglicht die Rückkehr zur vorherigen Ansicht und verhindert, dass die Nutzerinnen und Nutzer innerhalb der Navigationsstruktur die Orientierung verlieren.

Nach der Auswahl einer Aktion zeigt das System eine separate Bestätigungsansicht. Rückmeldungen wie "Auswahl bestätigt", "Meldung gesendet", "Tonne entsperrt" oder "Verbindung hergestellt" machen sichtbar, dass die Eingabe erkannt und verarbeitet wurde. Anschließend kann über die Navigation zum vorherigen Funktionsbereich oder zum Startscreen zurückgekehrt werden.

Der typische Interaktionsablauf lässt sich damit in sechs Schritte gliedern:

1. Aktuellen Status auf dem Startscreen erfassen.
2. Geschützten Bedienbereich auswählen.
3. Zugriff über die PIN-Eingabe freigeben.
4. Zum gewünschten Funktionsmodul navigieren.
5. Aktion auswählen und Systemrückmeldung abwarten.
6. Zur vorherigen Ansicht oder zum Startscreen zurückkehren.

#figure(
  align(
    center,
    image("touchpanel_final_navigation.png", width: 68%),
  ),
  caption: [Zentraler User Flow vom Startscreen über die PIN-Eingabe bis zur modularen Funktionsnavigation],
)

Fehler- und Sicherheitsmeldungen bilden einen parallelen System-Flow. Zustände wie "Hindernis erkannt", "Linie verloren" oder "Hilfe benötigt" können unabhängig vom aktuell geöffneten Funktionsmodul eingeblendet werden. Dadurch haben sicherheitsrelevante Informationen Vorrang vor der normalen Navigation und werden unmittelbar sichtbar.

#infobox[
  *Kernprinzip des User Flows:* Statusinformationen bleiben direkt zugänglich. Systemverändernde Aktionen werden durch PIN-Eingabe geschützt, innerhalb klar getrennter Funktionsmodule ausgeführt und anschließend durch eine eindeutige Rückmeldung bestätigt.
]

== Technische Umsetzung und interne Evaluation

Nach der Auswahl des finalen Bedienkonzepts wurde die in Figma entwickelte Struktur für den funktionalen Prototyp aufbereitet und mit der lokalen Hardwaresteuerung sowie der Flottenmanagement-Web-App verbunden. Im Mittelpunkt der technischen Umsetzung standen die für den Demonstrationsbetrieb zentralen Funktionen.

Dazu gehörten die Anzeige von Füllstand, Akkustand und Systemzustand, das Starten und Stoppen der Fahrt, die Bewegung zur Abholposition, die Rückkehr über die Funktion "Nach Hause" sowie die Darstellung von Fehler- und Sicherheitsmeldungen. Relevante Zustände wurden zusätzlich mit der Web-App synchronisiert, sodass lokale Bedienung und zentrale Überwachung gemeinsam geprüft werden konnten.

Nicht alle im vollständigen Figma-Wireflow vorgesehenen Module wurden mit derselben technischen Tiefe umgesetzt. Bereiche wie Energieverwaltung, Diagnose, Verbindungsoptionen und erweiterte Problemmeldungen wurden im Bedienkonzept vollständig berücksichtigt, ihre konkrete Funktionalität blieb jedoch teilweise vom Entwicklungsstand der angeschlossenen Hardware- und Softwarekomponenten abhängig.

#figure(
  table(
    columns: (1.55fr, 2.15fr, 2.35fr),
    [*Prüfbereich*], [*Technischer Stand*], [*Ergebnis der internen Bewertung*],

    [Statusanzeige],
    [Darstellung von Füllstand, Akkustand, Verbindung und aktuellen Systemzuständen.],
    [Die wichtigsten Informationen konnten ohne tiefe Navigation unmittelbar erfasst werden.],

    [Fahrsteuerung],
    [Start, Stopp, Fahrt zur Abholposition und Rückkehr zum Standplatz.],
    [Die zentralen Bewegungsfunktionen ließen sich über die lokale Bedienoberfläche auslösen.],

    [Fehler und Sicherheit],
    [Lokale Darstellung von Hindernissen, Linienverlust und sicherheitsrelevanten Zuständen.],
    [Die Kombination aus Symbol, Farbe, Text und akustischer Rückmeldung erleichterte die Zuordnung des Zustands.],

    [Web-App-Synchronisation],
    [Übertragung relevanter Status- und Betriebsdaten an das zentrale Managementsystem.],
    [Lokale Anzeige und zentrale Überwachung konnten als zusammenhängendes System betrachtet werden.],

    [Erweiterte Module],
    [Energie, Diagnose, Verbindung und Problemmeldung wurden im Wireflow vorgesehen.],
    [Der Funktionsumfang war teilweise vom technischen Integrationsstand der jeweiligen Systemkomponente abhängig.],
  ),
  caption: [Technischer Stand und interne Bewertung der Touchpanel-Funktionen],
)

Die interne Evaluation erfolgte während der schrittweisen Integration und der Tests am realen Gesamtsystem. Dabei wurde insbesondere geprüft, ob die vorgesehenen Zustände verständlich dargestellt werden, die zentralen Bedienwege nachvollziehbar bleiben und die Rückmeldungen nach einer Aktion eindeutig sind.

Als positiv erwiesen sich die Trennung zwischen unmittelbar sichtbaren Statusinformationen und geschützten Bedienfunktionen sowie die separaten Bestätigungsanzeigen. Gleichzeitig bestätigte die Umsetzung, dass die begrenzte Displayfläche eine konsequente Priorisierung der Inhalte erfordert. Nicht jede technisch mögliche Information sollte dauerhaft angezeigt werden.

Eine standardisierte Usability-Studie mit externen Testpersonen war nicht Bestandteil der internen Evaluation. Für eine weitere Entwicklung sollten insbesondere Tests mit älteren Menschen und Personen mit eingeschränkter Mobilität durchgeführt werden. Zusätzlich sind längere Tests bei unterschiedlichen Licht- und Wetterbedingungen sowie die systematische Prüfung von Fehlersituationen sinnvoll.

#infobox[
  *Bewertung:* Das Touchpanel konnte als funktionsfähige lokale Schnittstelle in das Gesamtsystem eingebunden werden. Die zentralen Bedien- und Statusfunktionen waren für den Demonstrationsbetrieb verfügbar. Für eine produktnahe Weiterentwicklung sind jedoch externe Usability-Tests, Langzeittests im Außenbereich und eine vollständige technische Integration aller vorgesehenen Module erforderlich.
]


#pagebreak()

= Präsentations- und Medienkonzept

== Kontinuierliche Video-Dokumentation

Der Projektverlauf wurde von Beginn an kontinuierlich durch Videoaufnahmen dokumentiert. In nahezu jeder Projektwoche entstanden mit Smartphones sowohl kurze Einzelaufnahmen als auch längere Videos. Dabei wurde nicht nur die technische Entwicklung des Prototyps festgehalten. Auch Arbeits-, Abstimmungs- und Planungsprozesse innerhalb des Teams wurden dokumentiert, um die Entstehung des Gesamtsystems möglichst vollständig nachvollziehbar zu machen.

Die Aufnahmen zeigen verschiedene Phasen des Projekts, darunter den mechanischen und elektronischen Aufbau, die Verkabelung, die Integration einzelner Komponenten sowie Fahr- und Funktionstests. Darüber hinaus wurden die Entwicklung des Touchpanels, die Flottenmanagement-Web-App und das Zusammenspiel der verschiedenen Systembereiche aufgezeichnet. Neben erfolgreichen Tests wurden auch Fehlversuche, technische Probleme und die daraus entstandenen Verbesserungen bewusst festgehalten.

Die kontinuierliche Dokumentation erfüllte mehrere Zwecke. Sie ermöglichte dem Team, frühere Arbeitsschritte erneut zu betrachten, Entscheidungen nachzuvollziehen und die Entwicklung des Prototyps über den gesamten Projektzeitraum zu vergleichen. Gleichzeitig dienten die Aufnahmen als Nachweis der praktischen Projektarbeit und der Funktionsfähigkeit des Systems. Aus dem entstandenen Videomaterial konnten später geeignete Sequenzen für die Projektpräsentation und die abschließenden Videos ausgewählt werden. Darüber hinaus bildeten die Aufnahmen eine visuelle Absicherung für den Fall, dass einzelne Funktionen während einer Live-Demonstration nicht zuverlässig vorgeführt werden konnten.

== Videoschnitt und dramaturgische Aufbereitung

Aus dem während des Projekts entstandenen umfangreichen Videomaterial wurden mehrere Videos mit unterschiedlichen inhaltlichen Schwerpunkten erstellt. Der Videoschnitt und die gestalterische Aufbereitung erfolgten mit Microsoft Clipchamp. Dabei wurden sowohl kurze Einzelaufnahmen als auch längere Aufzeichnungen gesichtet, ausgewählt und zu zusammenhängenden Darstellungen verarbeitet.

Für die Auswahl der Aufnahmen waren insbesondere die Bildqualität, die Verständlichkeit der dargestellten Abläufe und die Sichtbarkeit der tatsächlich funktionierenden Systemkomponenten entscheidend. Unklare, wiederholte oder für den jeweiligen Verwendungszweck nicht relevante Sequenzen wurden gekürzt oder entfernt. Im ausführlichen Projektvideo wurden hingegen auch Fehlversuche und technische Probleme bewusst beibehalten, da sie den Entwicklungsprozess und die daraus entstandenen Verbesserungen nachvollziehbar machen.

Die ausgewählten Sequenzen wurden durch Schnitte, Beschleunigungen, Übergänge, Musik, Überschriften und ergänzende Texte aufbereitet. Zusätzlich wurden das Logo der Hochschule sowie die Namen der Projektbeteiligten integriert. Die Länge, Reihenfolge und inhaltliche Gewichtung der Videos wurden innerhalb des Teams abgestimmt und anhand gemeinsamer Rückmeldungen schrittweise angepasst.

#figure(
  table(
    columns: (1.45fr, 2.25fr, 2.45fr),
    [*Videoformat*], [*Dramaturgischer Schwerpunkt*], [*Verwendungszweck*],

    [Kurztrailer],
    [Kompakte und aufmerksamkeitsstarke Zusammenfassung des Projekts.],
    [Kurze Vorstellung des Projekts zu Beginn der Präsentation.],

    [Teamvorstellung],
    [Vorstellung der Projektgruppe und ihrer gemeinsamen Arbeit.],
    [Einordnung des Teams und Herstellung eines persönlichen Projektbezugs.],

    [Systemdemonstration],
    [Gezielte Darstellung der technischen Funktionen und des Zusammenspiels der Systembereiche.],
    [Nachweis der Funktionsfähigkeit und visuelle Absicherung bei möglichen Problemen während der Live-Demonstration.],

    [Ausführliches Projektvideo],
    [Chronologische Darstellung der Projektphasen einschließlich Fehlversuchen, Anpassungen und Verbesserungen.],
    [Umfassender Überblick über den Entwicklungsprozess sowie Wiedergabe im Hintergrund nach der Präsentation.],
  ),
  caption: [Aufbereitung und Einsatz der erstellten Videoformate],
)

#infobox[
  *KI-gestützte Videoproduktion:* Ergänzend zum dokumentarischen Videomaterial wurden mithilfe generativer KI und gezielt formulierter Prompts zwei kurze Werbevideos erstellt. Diese dienten dazu, die Projektidee kompakt, kreativ und aufmerksamkeitsstark zu vermitteln.
]


== Einsatz in Abschlusspräsentation und Ausstellung

Für die Abschlusspräsentation wurde in Canva eine umfangreiche Präsentation mit rund 90 Folien entwickelt. Zunächst entstand eine inhaltliche Grundstruktur, die anschließend zu einer multimedialen Präsentation weiterentwickelt wurde. Texte, Bilder, Videos und technische Darstellungen wurden so miteinander kombiniert, dass die einzelnen Entwicklungsbereiche nicht nur erklärt, sondern auch anhand realer Projektaufnahmen veranschaulicht werden konnten.

Die Gestaltung orientierte sich an der visuellen Sprache des Touchpanels und der Flottenmanagement-Web-App. Dunkle Flächen, gelbe Akzente, einheitliche Symbole und Darstellungen der Smarten Mülltonne sorgten für ein zusammenhängendes Erscheinungsbild. Die Inhalte der unterschiedlichen Fachbereiche wurden gemeinsam an diese Gestaltungsstruktur angepasst, sodass Hardware, Software, Touchpanel, Web-App und Medien nicht wie voneinander getrennte Teilprojekte wirkten, sondern als Bestandteile eines gemeinsamen Gesamtsystems präsentiert wurden.

Bereits der Wartebildschirm enthielt eine kurze KI-gestützte Animation. Für den eigentlichen Einstieg wurde die Smarte Mülltonne anhand des realen Prototyps in Blender als dreidimensionales Modell nachgebildet. Dieses Modell wurde anschließend in Unreal Engine in einer filmischen Szene inszeniert. Dabei erscheint die Mülltonne aus der Dunkelheit, bevor der Projekttitel eingeblendet wird. Direkt im Anschluss folgte das Video zur Vorstellung des Projektteams.

Während der weiteren Präsentation wurden in nahezu allen Themenbereichen passende Videoausschnitte eingesetzt. Die während des Projekts aufgenommenen Szenen ergänzten die jeweiligen Erläuterungen und machten Aufbau, Entwicklung, Tests und Systemfunktionen unmittelbar sichtbar. Dadurch konnten auch komplexe technische Inhalte anschaulicher und näher an der tatsächlichen Projektarbeit vermittelt werden.

Den Abschluss bildete das ausführliche Projektvideo. Es zeigte den gesamten Entwicklungsprozess einschließlich Planungsphasen, technischer Arbeiten, erfolgreicher Tests, aufgetretener Fehler und daraus entstandener Verbesserungen. Nach dem Ende der eigentlichen Präsentation konnte dieses Video im Ausstellungsbereich weiter im Hintergrund abgespielt werden. Besucherinnen und Besucher erhielten dadurch die Möglichkeit, den Projektverlauf und zusätzliche Details auch unabhängig vom mündlichen Vortrag nachzuvollziehen.


= Projektorganisation

== Teamrollen

Die Notion-Koordination teilt das Projekt in vier Arbeitsbereiche:

#figure(
  table(
    columns: (1.7fr, 2.4fr, 2fr),
    [*Team*], [*Aufgaben*], [*Personen laut Board*],
    [Hardware & Mechanik], [Antrieb, Konstruktion, Sensoren, Akku, Elektronik.], [Jan-Lukas, Theresa, Alaeddine],
    [Software & System], [Pico-Code, Kommunikation, Backend, Datenverarbeitung, Navigation.], [Jan-Lukas, Jonas, Theresa, Alaeddine],
    [App & UX/UI], [App-Design, User Flows, Touchpanel, Feedbacksysteme, Usability.], [Fulya, Jonas],
    [Konzept & Produktstrategie], [Use Cases, Vision, Flottenmanagement-Konzept, Storytelling.], [Fulya, Jonas],
  ),
  caption: [Rollenmodell aus dem Notion-Board],
)

== Status zum 03. Mai 2026

Zum aktuellen Dokumentationsstand ist die Hardware-Weiterentwicklung inhaltlich klar ausgerichtet: Der vorhandene Prototyp soll mechanisch und fahrdynamisch verbessert werden. Dazu gehören Schrittmotor-Auslegung, neue gedruckte Räder, Anpassung der Ketten, Überarbeitung des Fahrwerks, Sensorintegration, Energieversorgung, Sicherheitskomponenten und spätere Fahrtests. Parallel dazu ist der Software- und App-Prototyp bereits weit konkretisiert: Die Web-App enthält Backend, Frontend, Datenmodell, Live-Kommunikation, Karte, Simulation, Routenplanung und Agenten-Chat.

Der Projektstand ist damit zweigeteilt: Die Hardware bildet den eigentlichen mechatronischen Kern und wird schrittweise stabilisiert; die Web-App ist das digitale Zusatzsystem, mit dem Monitoring, Flottenlogik und Demo-Szenarien sichtbar gemacht werden.

== Nächste Schritte

Die nächsten technisch sinnvollen Schritte ergeben sich direkt aus der Chronologie:

- neue Räder konstruieren, drucken und mechanisch testen.
- Kettenlänge, Kettenspannung und Kettenführung am Fahrwerk prüfen.
- Schrittmotoren und Motortreiber elektrisch sowie softwareseitig integrieren.
- Fahrparameter für Geradeauslauf, Kurvenfahrt und Drehmanöver neu abstimmen.
- erste strukturierte Fahrtests mit Linienführung und Hindernissen durchführen.
- Sensorpositionen, Touchpanel, Not-Aus und Magnetschalter am Korpus festlegen.
- API-Vertrag mit der Hardware final testen.
- Echte Füllstands- und Akkudaten vom Pico beziehungsweise Gateway an das Backend senden.
- Sicherheitsereignisse des Magnetschalters integrieren.
- Command-Queue mit echter Hardware verproben.
- Routenplanung und Truck-Simulation durch reale Fahrzustände ersetzen oder ergänzen.
- Usability-Test des Dashboards durchführen.
- Energie- und Ladezustände mit realen Messwerten validieren.

= Zusammenfassung

Die aktuelle Weiterentwicklung der Smarten Mülltonne verfolgt zwei Ebenen. Die erste und wichtigste Ebene ist der physische Prototyp: Antrieb, Schrittmotoren, Räder, Ketten, Fahrwerk, Sensorik, Energieversorgung und Sicherheit müssen so überarbeitet werden, dass die Mülltonne zuverlässig, kontrolliert und wiederholbar fährt. Genau dort liegt der Kern der Projektarbeit.

Die zweite Ebene ist die digitale Erweiterung `smart-bin`. Sie stellt mehrere Tonnen auf einer Karte dar, verarbeitet Live-Daten, plant Abholrouten nach Füllstand, visualisiert Energie- und Sicherheitsdaten, simuliert den Betrieb und bietet mit dem Agenten eine natürliche Bedienoberfläche. Die App ist damit ein starkes Zusatzmodul und ein wichtiger Demonstrator, steht aber auf der Hardwarebasis.

Die Vorarbeiten aus dem Wintersemester bleiben als technischer Ausgangspunkt relevant, werden aber bewusst nicht als eigene Leistung dokumentiert. Die eigene Arbeit besteht darin, aus dem bestehenden Einzelprototyp eine besser fahrende, sinnvoll erweiterte und systemfähig dokumentierte Smarte Mülltonne 2.0 zu entwickeln.
