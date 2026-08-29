# Liam Mini-Jarvis – Memory Upgrade

## Gesicherter Ausgangspunkt

- Repository: `Bot49576/Jarvis`
- Ausgangs-Commit: `c18e66fa4af4a0f2368d204395922c63ce16e86c`
- Der Commit bleibt über die GitHub-Historie vollständig wiederherstellbar.

## Neue, bewusst kleine Struktur

- Letzte 50 Nachrichten bleiben vollständig im Gesprächskontext.
- Ab 80 Nachrichten werden ältere Teile mit einem einzelnen günstigen
  Gemini-Aufruf zusammengefasst; 50 Nachrichten bleiben wörtlich erhalten.
- Ausdrückliche Fakten werden mit `Merk dir: ...` gespeichert.
- `Vergiss: ...` entfernt passende ausdrückliche Fakten.
- `/memory` zeigt den Speicherstatus, `/reset` löscht nur den Gesprächsverlauf,
  `/forgetall` löscht Verlauf und Fakten.
- Normale Fragen verwenden `thinking_level=low`; `/deep` oder „denk gründlich“
  verwendet `medium`.
- Google Search wird nur bei erkennbar aktuellen oder ausdrücklich gewünschten
  Recherchen zugeschaltet. Webrecherchen verwenden die aktuelle Gemini-
  Interactions-API; normale Gespräche bleiben auf der schlanken
  Generate-Content-Schnittstelle.
- Tokenzahlen werden im Render-Protokoll ausgegeben.
- Text und Sprache sind getrennt aufbereitet: Telegram zeigt die Antwort und
  höchstens drei anklickbare Quellen; Fish Audio liest nur eine kurze,
  bereinigte Fassung ohne URLs, Quellenblock oder Markdown vor. Dafür ist kein
  zweiter Gemini-Aufruf nötig.
- Telegram-Sprachnachrichten bis zwei Minuten werden von Gemini in Text
  umgewandelt und anschließend durch denselben sicheren Gesprächs-, Memory- und
  Rechercheablauf verarbeitet wie eine getippte Nachricht. Fish Audio bleibt
  ausschließlich für die gesprochene JARVIS-Antwort zuständig.
- Liams Angaben aus `Liam_allgemein_jarvis.txt` werden als geschützte Render-
  Variable `LIAM_BASE_PROFILE` hinterlegt, nicht im öffentlichen Repository.
  Neuere Aussagen und gespeicherte Fakten haben Vorrang; leere Felder werden
  nicht mit erfundenen Angaben gefüllt.

## Render-Variable für Neon

`DATABASE_URL` muss die Neon-Verbindungsadresse enthalten. Ohne diese Variable
bleibt der Bot funktionsfähig, merkt sich Dinge aber nur bis zum nächsten
Render-Neustart.

Optional kann `ALLOWED_TELEGRAM_USER_ID` auf Liams numerische Telegram-ID gesetzt
werden. Dann beantwortet der Bot keine fremden Nutzer.

## Hosting-Entscheidung und Ausweichplan (22.08.2026)

- Der bestehende Render-Free-Dienst mit Telegram-Webhook bleibt unverändert.
- Bekannte Grenze: Die kostenlose Render-Instanz kann nach einer Ruhephase
  einschlafen. Die erste Anfrage danach braucht deshalb deutlich länger und
  kann bei ungünstigem Ablauf wie eine ausgebliebene Antwort wirken.
- Falls dieser Fehler wiederholt auftritt oder die Wartezeit nicht mehr
  akzeptabel ist, ist eine dauerhaft laufende Google-Compute-Engine-Instanz
  vom Typ `e2-micro` der vorgemerkte Ausweichplan.
- Geschätzter Umstiegsaufwand: etwa 1,5 bis 3 Stunden plus etwas mehr laufende
  Wartung. Ein Wechsel erfolgt nicht automatisch, sondern erst nach erneuter
  Prüfung und Daniels Freigabe.
- Diese Entscheidung gehört ausschließlich zum Liam-Mini-Jarvis und ändert
  nichts am separaten DARVIS-Projekt.

## Noch bewusst nicht enthalten

- automatische Speicherung jedes persönlichen Details als dauerhafter Fakt
- OpenRouter, DDGS oder Groq
- autonome Hintergrundfunktionen

## Dashboard-Schnittstelle – Stufe 02

- Telegram und Dashboard verwenden denselben Render-Webdienst und dieselbe geprüfte JARVIS-Antwortlogik.
- `/healthz` meldet nur, ob der Dienst erreichbar ist. Chat, Status und Sessions benötigen immer eine gültige Geräteberechtigung.
- Ohne `ALLOWED_TELEGRAM_USER_ID` bleibt die gesamte Dashboard-API absichtlich gesperrt. Die eigentliche Gerätefreigabe und Übergabe des Zugangsschlüssels erfolgt erst in Stufe 03.
- Browser-Anfragen werden zusätzlich auf die eigene Render-Adresse begrenzt. Fremde Webseiten können die geschützte API nicht verwenden.
- Dashboard-Sessions liegen in der neuen Tabelle `jarvis_dashboard_sessions_v1`. Die bestehende Tabelle `jarvis_chat_memory_v1` wird nicht verändert; JARVIS verwendet für beide Eingänge weiterhin Liams gemeinsames Memory.
- Die PWA wird unter `/dashboard/` direkt vom vorhandenen Render-Dienst ausgeliefert. Telegram bleibt vollständig erhalten.
- Ein Ausfall oder fehlender Gerätezugang wird in der Oberfläche rot angezeigt; Zuhören und Antwortsuche bleiben gelb, Bereit und Antworten cyan.

## Sichere Gerätefreigabe – Stufe 03

- Nur Liams numerische Telegram-Kennung wird bei Render als erlaubter Besitzer hinterlegt. Fremde Telegram-Nutzer und nicht freigegebene Browser erhalten keinen Dashboard-Zugang.
- Ein freizugebendes Gerät öffnet einmalig einen persönlichen Freigabelink. Der geheime Teil steht ausschließlich hinter `#` und wird dadurch nicht an Render oder andere Server übertragen.
- Das Dashboard entfernt den geheimen Teil sofort aus der sichtbaren Adresszeile und tauscht ihn über die eigene Render-Adresse gegen ein geschütztes Geräte-Cookie ein.
- Das Cookie ist auf dauerhafte Nutzung ausgelegt, wird bei jedem erfolgreichen Zugriff automatisch verlängert, ist nur über HTTPS übertragbar und für JavaScript unsichtbar. Damit wird es beim Hinzufügen zum iPhone-Startbildschirm in die PWA übernommen; normaler Browser-Speicher wird von iOS dagegen nicht kopiert. Eine neue Freigabe ist erst nach Widerruf, gelöschten App-/Browserdaten oder einer vom Betriebssystem erzwungenen Löschung nötig.
- Bereits freigegebene Desktop-Browser mit dem älteren lokalen Zugang bleiben während der Umstellung kompatibel.
- Ein unvollständiger oder veränderter Schlüssel wird abgewiesen. Das Dashboard bleibt dann gesperrt und zeigt den Fehler rot an.
- Derselbe geprüfte Freigabelink kann gezielt auf Liams iPhone und dem vorgesehenen Desktop geöffnet werden. Ein bloßer Aufruf der Dashboard-Adresse ohne Gerätefreigabe reicht nicht aus.
- Telegram, Fish Audio, Gemini und das bestehende gemeinsame Memory bleiben durch diese Stufe unverändert.

## Abgenommenes Drei-Seiten-Design – Schritt 02

- Die bisherige Demo-Oberfläche ist lokal durch das abgenommene Design mit Startseite, Vollbild-Chat und Systemseite ersetzt.
- Die Startseite enthält den dynamischen JARVIS-Ring und einen eigenen Datei-Upload. Der Chat besitzt weiterhin einen zweiten, getrennten Datei-Upload.
- Seitenwechsel über die untere Navigation und Wischgesten funktionieren. Die lokale Browser-Prüfung aller drei Seiten verlief ohne JavaScript-Fehler.
- Die sichtbaren Nachrichten und Systemwerte sind in diesem Schritt noch reine Gestaltungsbeispiele. Ring, Sprache, Chat, Uploads und Live-Systemdaten werden erst in den ausdrücklich freigegebenen Schritten 03 bis 05 angeschlossen.
- Dieser Stand ist nur lokal gespeichert und noch nicht zu GitHub oder Render veröffentlicht.

## Aktivierte Startseite – Schritt 03

- Ein Tippen auf den JARVIS-Ring startet beziehungsweise beendet die echte Mikrofonerfassung des Geräts. Echo-Unterdrückung, Rauschminderung und automatische Pegelanpassung werden angefordert.
- Die neun Balken in der Ringmitte folgen beim Zuhören dem tatsächlich gemessenen Mikrofonpegel. Bereit, Zuhören, Arbeiten, Antworten, Fehler und Offline besitzen klar getrennte Farben und Bewegungen.
- Beim Verlassen der Seite werden Mikrofonspur und Audioverarbeitung beendet, damit das Mikrofon nicht unbeabsichtigt weiterläuft.
- Der Plus-Knopf öffnet die Dateiauswahl, merkt die gewählten Dateien und übergibt sie sichtbar an die Chatseite. Das tatsächliche Senden und Verarbeiten der Auswahl gehört weiterhin zu Schritt 04.
- Die mobile Ansicht wurde mit 390 × 844 Pixeln geprüft: kein Überlauf, alle Bedienelemente sichtbar und keine Browserfehler.
- Mikrofon- und Dateiberechtigungen werden nicht umgangen. Der echte Berechtigungstest auf dem iPhone erfolgt nach Veröffentlichung im vollständigen Geräte-Endtest.
