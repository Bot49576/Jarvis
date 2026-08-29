# Liam JARVIS – Schritt 02 vor Veröffentlichung

Stand: 29.08.2026

## Geprüfter Ausgangspunkt

- GitHub `main`: `cf1273db135fa5b3a6f59e514d561ed2d9c9618d`
- Entspricht exakt dem vollständigen Rückkehrpunkt aus `STEP00_PWA_20260829`.
- Render verwendet weiterhin `Bot49576/Jarvis`, Branch `main`, Build `pip install -r requirements.txt` und Start `python bot.py`.
- Bestehende Zugangsdaten wurden nicht ausgelesen oder verändert.

## Lokale Änderung

- Gemeinsamer Render-Webdienst für Telegram und Dashboard.
- Geschützte Endpunkte für Status, Sessions und Chat.
- PWA-Auslieferung unter `/dashboard/`.
- Fremde Browser-Ursprünge und Anfragen ohne Geräteberechtigung werden abgewiesen.
- Ohne `ALLOWED_TELEGRAM_USER_ID` bleibt die Dashboard-API absichtlich gesperrt; die Gerätefreigabe gehört zu Schritt 03.
- Neue getrennte Session-Tabelle `jarvis_dashboard_sessions_v1`; keine Änderung an `jarvis_chat_memory_v1`.

## Prüfung

- 35 von 35 Tests bestanden.
- Darin enthalten: alle 26 bisherigen Telegram-/Gemini-/Memory-Tests und 9 neue Schnittstellen-, Session- und Zugriffstests.
- Zusätzlich vollständige Neuinstallation aus `requirements.txt` in einer sauberen Python-Umgebung geprüft.
- Geprüfte Kernversionen: python-telegram-bot 22.5 und Tornado 6.5.8.
- Lokale PWA ohne Browserfehler; lokale Vorschau bleibt im Demo-Modus.
- Bei den Prüfungen wurden keine echten Gemini-, Fish-Audio- oder Neon-Anfragen ausgelöst.

## Noch nicht durchgeführt

- Keine Veröffentlichung auf GitHub oder Render.
- Keine Gerätefreigabe.
- Kein produktiver Dashboard-Chat.
- Keine Änderung oder Löschung bestehender Neon-Memories.
