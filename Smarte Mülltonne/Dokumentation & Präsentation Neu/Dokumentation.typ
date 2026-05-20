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
      #text(size: 10.5pt)[Jan-Lukas · Theresa Pelz · Alaeddine Baghyour · Fulya · Jonas Wiesner]
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

Bei der Übergabe lag bereits ein funktionsorientierter Prototyp mit Hardware- und Softwareanteilen vor. Die vorhandene Software außerhalb von `smart-bin` enthielt unter anderem MicroPython-Code für einen Raspberry Pi Pico beziehungsweise Pico W, Module für DC-Motoren, Linienverfolgung, Ultraschallmessung, Buttons, Buzzer, LEDs, Netzwerkkommunikation und eine einfache serverseitige Missionslogik. Zusätzlich waren Schaltpläne, 3D-Druckteile, Rechnungen, Fotos, Videos und eine ältere Dokumentation vorhanden.

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
- Konzeption und Implementierung der Flottenmanagement-Web-App `smart-bin` als digitale Erweiterung
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
