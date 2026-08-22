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

## Noch bewusst nicht enthalten

- Spracheingabe/STT
- automatische Speicherung jedes persönlichen Details als dauerhafter Fakt
- OpenRouter, DDGS oder Groq
- autonome Hintergrundfunktionen
