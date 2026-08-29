# Schritt 07 – lokale Vorabnahme

Stand: 29.08.2026

## Ergebnis

Die lokal vorbereitete PWA-Version hat die vollständige Vorabnahme bestanden.
Für den Test wurden ausschließlich künstliche Antworten, Audiodaten und eine
künstliche Textdatei verwendet. Gemini, Fish Audio und andere kostenpflichtige
Schnittstellen wurden nicht aufgerufen.

## Bestandene Prüfungen

- 50 automatisierte Python-Tests für JARVIS-Logik, Sicherheit, Dashboard-API,
  Memory-Verknüpfung, Text, Audio und Dateien.
- 14 gezielte Tests für die sofortigen, aufgabengerechten Kurzrückmeldungen.
- Geschützter Gerätestatus lehnt Zugriffe ohne Freigabe ab.
- Einmaliger Freigabelink wurde angenommen; der geheime Teil verschwand sofort
  aus der Adresse.
- Ein neuer Browser-Tab blieb ohne erneuten Freigabelink verbunden.
- Textnachricht, Sofortmeldung und endgültige Antwort liefen vollständig durch
  den echten lokalen Dashboard-Server.
- Eine künstliche Textdatei wurde über den sichtbaren Plus-Knopf ausgewählt,
  übertragen und korrekt verarbeitet.
- Systemseite zeigte alle vier vorgesehenen Dienstzustände und echte lokale
  Ereignisse ohne Browserwarnungen.
- Spracheingabe- und Sprachausgabe-Endpunkte wurden mit künstlichen Audiodaten
  über den geschützten Serverweg erfolgreich geprüft.
- Der lokale JARVIS-Dienst wurde vollständig beendet. Der Stillstand wurde
  bestätigt, danach wurde ein neuer sauberer Prozess gestartet.
- Nach dem Neustart blieb das Gerät ohne Freigabecode verbunden. Die Adresse
  enthielt weiterhin kein Geheimnis.
- iPhone-Format 390 × 844: alle drei Seiten 388 Pixel breit bei 390 Pixel
  Dokumentbreite, kein horizontaler Überlauf.
- Desktop-Format 1280 × 720: Dashboard 518 Pixel breit und vollständig im
  Fenster; keine Browserfehler.
- Manifest, PWA-Dateien und Sicherheitsheader wurden vom lokalen Webdienst
  korrekt ausgeliefert.

## Bewusst erst nach Veröffentlichung prüfbar

- echte Mikrofonfreigabe und Aufnahme in Safari auf Liams iPhone
- echte Transkription durch Gemini
- echte Fish-Audio-Erzeugung und automatische beziehungsweise manuelle
  Wiedergabe auf dem iPhone
- Aktualisierung der bereits installierten PWA über HTTPS/Render
- dauerhafte Gerätefreigabe im echten Render-Dienst nach dessen Neustart
- echtes Neon-Memory und reale Systemwerte des veröffentlichten Dienstes

Diese Punkte gehören zur Produktionsabnahme in Schritt 08. Schritt 07 bestätigt
den veröffentlichungsreifen lokalen Stand, nicht bereits den Produktionsbetrieb.
