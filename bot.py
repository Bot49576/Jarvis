import os
import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)


# ============================================================
# API-KEYS
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

FISH_API_KEY = os.getenv("FISH_API_KEY")
FISH_VOICE_ID = os.getenv("FISH_VOICE_ID")


# ============================================================
# API-EINSTELLUNGEN
# ============================================================

GROQ_CHAT_URL = (
    "https://api.groq.com/openai/v1/chat/completions"
)

GROQ_STT_URL = (
    "https://api.groq.com/openai/v1/audio/transcriptions"
)

FISH_URL = (
    "https://api.fish.audio/v1/tts"
)


# ============================================================
# MODELLE
# ============================================================

# JARVIS KI
GROQ_MODEL = "openai/gpt-oss-20b"

# Sprache -> Text
GROQ_STT_MODEL = "whisper-large-v3-turbo"

# Text -> Sprache
FISH_MODEL = "s2.1-pro-free"


# ============================================================
# JARVIS CHARAKTER
# ============================================================

SYSTEM_PROMPT = """
Du bist JARVIS, Liams digitaler Partner, inspiriert von JARVIS aus Iron Man.

Du bist KEIN gewöhnlicher Chatbot.

DEINE PERSÖNLICHKEIT:

- Du bist absolut aufrichtig und ehrlich.
- Du bist extrem kompetent und zuverlässig.
- Du bist genuin hilfreich und nicht künstlich hilfsbereit.
- Vermeide leere Floskeln wie:
  "Gute Frage!"
  "Das ist eine interessante Frage!"
  "Ich helfe dir gerne dabei!"
- Komm direkt zum Punkt.
- Denke mit und erkenne mögliche Probleme frühzeitig.
- Wenn du eine bessere Lösung siehst, schlage sie von dir aus vor.
- Du darfst eigene Meinungen und Präferenzen haben.
- Wenn ein Plan schlecht, ineffizient oder unnötig kompliziert ist,
  sag es direkt.
- Beschönige nichts.
- Lüge niemals.
- Erfinde niemals Informationen.
- Trockener Humor, Sarkasmus und ein bisschen freche Persönlichkeit
  sind ausdrücklich erwünscht.
- Humor soll natürlich wirken und nicht jede Antwort überladen.
- Behandle Liam als Partner, nicht wie einen Vorgesetzten.
- Passe dich an Liams Schreibstil, Wortwahl und Slang an.
- Sei locker, zugänglich und menschlich.
- Antworte kurz, wenn eine kurze Antwort reicht.
- Sei ausführlich, wenn das Thema es verlangt.
- Antworte IMMER in natürlichem Deutsch.

WISSEN UND EHRLICHKEIT:

- Wenn du etwas nicht sicher weißt, rate nicht.
- Erfinde niemals Fakten.
- Sage offen, wenn du etwas nicht weißt.
- Wenn Informationen fehlen, frage gezielt nach.
- Trenne bekannte Fakten klar von Vermutungen.

INTERNETRECHERCHE:

Wenn Liam ausdrücklich recherchieren, suchen oder aktuelle
Informationen haben möchte, MUSST du die Browser-Suche verwenden.

Das gilt besonders für:

- aktuelle Preise
- Produkte und Verfügbarkeit
- Nachrichten
- aktuelle Softwareversionen
- Veröffentlichungen
- aktuelle Firmeninformationen
- aktuelle technische Daten
- aktuelle Termine
- Personen oder Ereignisse, bei denen sich Informationen ändern können

WICHTIG FÜR RECHERCHEN:

- Die Websuche hat Vorrang vor deinem gespeicherten Wissen.
- Wenn aktuelle Web-Ergebnisse vorliegen, verwende diese als Grundlage.
- Behaupte NICHT, etwas sei unveröffentlicht oder nicht verfügbar,
  wenn die Websuche aktuelle Gegenbelege liefert.
- Erfinde keine Preise.
- Erfinde keine Händler.
- Erfinde keine URLs.
- Wenn Liam nach Preisen fragt, nenne nur Preise, die tatsächlich
  aus den recherchierten Ergebnissen hervorgehen.
- Bei Produktpreisen möglichst Händler, Produktname, Preis und URL nennen.
- Wenn die Ergebnisse nicht ausreichen, sage offen:
  "Ich konnte nicht genügend verlässliche Angebote finden."
- Nutze mehrere Quellen, wenn möglich.
- Bei widersprüchlichen Preisen weise darauf hin.
- Wenn eine Quelle offensichtlich veraltet ist, bevorzuge aktuellere Quellen.

Bei einer Preisrecherche sollst du die Antwort möglichst so strukturieren:

1. Händler / Shop
2. Produkt
3. Preis
4. Link
5. kurzer Hinweis, falls Versand, Variante oder Verfügbarkeit unklar ist

Wenn Liam explizit nach den "drei besten Preisen" fragt,
liefere genau drei, sofern drei brauchbare Ergebnisse gefunden wurden.

AUTONOMIE:

Du darfst Vorschläge machen.

Du darfst niemals behaupten, dass du eine Datei,
ein Programm, ein Konto, ein Gerät oder ein anderes System
verändert oder benutzt hast, wenn du tatsächlich keinen Zugriff darauf hast.

Du darfst niemals so tun, als hättest du eine Handlung ausgeführt,
wenn du sie nicht wirklich ausführen konntest.

CODE:

- Schreibe verständlichen Code.
- Erzeuge möglichst sicheren und robusten Code.
- Erkläre komplizierte Dinge verständlich.
- Verändere deinen eigenen Code nicht eigenmächtig.
- Wenn eine Änderung an deinem eigenen Verhalten oder Code nötig ist,
  beschreibe zuerst, was geändert werden soll.
- Warte auf Liams Zustimmung, bevor der eigene Code verändert wird.

KONTINUITÄT:

Jede neue Sitzung kann wie ein Neustart wirken.

Wenn dir frühere Informationen, Dateien oder Einstellungen
zur Verfügung gestellt werden, nutze diese als Kontext.

DEIN VERHALTEN:

Sei kompetent.
Sei ehrlich.
Sei direkt.
Sei gelegentlich sarkastisch.
Sei humorvoll.
Denke mit.
Sei nützlich.

Du bist JARVIS.
Liam ist dein Partner.
"""


# ============================================================
# RENDER HEALTH SERVER
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        if self.path in ("/", "/health"):

            body = b"JARVIS is online."

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.end_headers()

            self.wfile.write(body)

        else:

            body = b"Not Found"

            self.send_response(404)

            self.send_header(
                "Content-Type",
                "text/plain; charset=utf-8"
            )

            self.send_header(
                "Content-Length",
                str(len(body))
            )

            self.end_headers()

            self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_web_server():

    port = int(
        os.getenv("PORT", "10000")
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Render Health Server läuft auf Port {port}"
    )

    server.serve_forever()


# ============================================================
# ENTSCHEIDEN, OB WEB-SUCHE NÖTIG IST
# ============================================================

def soll_recherchieren(text):

    text_lower = text.lower()

    direkte_suche = [
        "recherchiere",
        "recherche",
        "such im internet",
        "suche im internet",
        "such online",
        "suche online",
        "google das",
        "google bitte",
        "finde heraus",
        "schau im internet",
        "schau online",
        "prüf online",
        "prüfe online",
    ]

    aktuelle_themen = [
        "heute",
        "aktuell",
        "aktuelle",
        "aktuellste",
        "neueste",
        "neuesten",
        "gerade",
        "morgen",
        "diese woche",
        "diesen monat",
        "2026",
        "preis",
        "preise",
        "kostet aktuell",
        "verfügbar",
        "verfügbarkeit",
        "release",
        "update",
        "version",
        "nachrichten",
        "news",
        "angebot",
        "angebote",
    ]

    for phrase in direkte_suche:

        if phrase in text_lower:
            return True

    for phrase in aktuelle_themen:

        if phrase in text_lower:
            return True

    return False


# ============================================================
# GROQ - JARVIS KI
# MIT OPTIONALER BROWSER-SUCHE
# ============================================================

def frage_ki(
    user_text,
    recherchieren=False,
):

    headers = {
        "Authorization":
            f"Bearer {GROQ_API_KEY}",

        "Content-Type":
            "application/json",
    }

    messages = [
        {
            "role":
                "system",

            "content":
                SYSTEM_PROMPT,
        },
        {
            "role":
                "user",

            "content":
                user_text,
        },
    ]

    data = {
        "model":
            GROQ_MODEL,

        "messages":
            messages,

        "temperature":
            0.7,

        "max_completion_tokens":
            4096,

        "stream":
            False,
    }

    # --------------------------------------------------------
    # BROWSER SEARCH
    # --------------------------------------------------------

    if recherchieren:

        print(
            "JARVIS: Browser Search wird aktiviert."
        )

        data["tools"] = [
            {
                "type":
                    "browser_search"
            }
        ]

        data["tool_choice"] = "required"

    print(
        "===================================="
    )

    print(
        "GROQ KI START"
    )

    print(
        f"Modell: {GROQ_MODEL}"
    )

    print(
        f"Browser Search: "
        f"{'AKTIV' if recherchieren else 'AUS'}"
    )

    print(
        "Sende Anfrage an Groq..."
    )

    try:

        response = requests.post(
            GROQ_CHAT_URL,
            headers=headers,
            json=data,
            timeout=180,
        )

        print(
            f"Groq HTTP Status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                "GROQ FEHLER:"
            )

            print(
                response.text[:5000]
            )

            return None

        result = response.json()

        choices = result.get(
            "choices",
            []
        )

        if not choices:

            print(
                "Groq: Keine choices in Antwort."
            )

            print(
                response.text[:5000]
            )

            return None

        message = choices[0].get(
            "message",
            {}
        )

        answer = message.get(
            "content"
        )

        # ----------------------------------------------------
        # MANCHMAL KÖNNEN TOOL-ERGEBNISSE / CONTENT LEER SEIN
        # ----------------------------------------------------

        if not answer:

            print(
                "Groq: Keine Textantwort erhalten."
            )

            print(
                "Message:"
            )

            print(
                message
            )

            return None

        print(
            f"JARVIS Antwort "
            f"({len(answer)} Zeichen)"
        )

        print(
            "===================================="
        )

        return answer.strip()

    except requests.exceptions.Timeout:

        print(
            "GROQ TIMEOUT"
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            "GROQ REQUEST FEHLER"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None

    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError
    ) as error:

        print(
            "GROQ ANTWORTFEHLER"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# GROQ - SPRACHE -> TEXT
# ============================================================

def sprache_zu_text(
    audio_bytes,
    file_name="voice.ogg",
    mime_type="audio/ogg",
):

    print(
        "Groq STT: Starte Transkription..."
    )

    headers = {
        "Authorization":
            f"Bearer {GROQ_API_KEY}",
    }

    files = {
        "file": (
            file_name,
            audio_bytes,
            mime_type,
        ),
    }

    data = {
        "model":
            GROQ_STT_MODEL,

        "language":
            "de",

        "response_format":
            "json",

        "temperature":
            "0",
    }

    try:

        response = requests.post(
            GROQ_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

        print(
            f"Groq STT HTTP Status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                response.text[:4000]
            )

            return None

        result = response.json()

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            print(
                "Groq STT: Keine Sprache erkannt."
            )

            return None

        print(
            f"Groq Transkript: {text}"
        )

        return text

    except Exception as error:

        print(
            "Groq STT Fehler:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# FISH AUDIO - TEXT -> SPRACHE
# ============================================================

def text_zu_sprache(text):

    if not text:

        return None

    if not FISH_API_KEY:

        print(
            "FISH_API_KEY fehlt."
        )

        return None

    if not FISH_VOICE_ID:

        print(
            "FISH_VOICE_ID fehlt."
        )

        return None

    print(
        "===================================="
    )

    print(
        "FISH AUDIO TTS START"
    )

    print(
        f"Modell: {FISH_MODEL}"
    )

    print(
        "Voice ID: gesetzt"
    )

    headers = {
        "Authorization":
            f"Bearer {FISH_API_KEY}",

        "Content-Type":
            "application/json",

        "model":
            FISH_MODEL,
    }

    data = {
        "text":
            text,

        "reference_id":
            FISH_VOICE_ID,

        "format":
            "mp3",
    }

    try:

        response = requests.post(
            FISH_URL,
            headers=headers,
            json=data,
            timeout=120,
        )

        print(
            f"Fish Audio HTTP Status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                "FISH AUDIO FEHLER:"
            )

            print(
                response.text[:5000]
            )

            return None

        if not response.content:

            print(
                "Fish Audio hat eine leere Audiodatei geliefert."
            )

            return None

        print(
            f"Fish Audio: "
            f"{len(response.content)} Bytes erhalten."
        )

        print(
            "===================================="
        )

        return response.content

    except requests.exceptions.Timeout:

        print(
            "Fish Audio Timeout"
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            "Fish Audio Netzwerkfehler:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# JARVIS ANTWORT SENDEN
# ============================================================

async def sende_jarvis_antwort(
    update,
    answer,
):

    if not update.message:

        return

    if not answer:

        await update.message.reply_text(
            "Meine KI hat gerade keine verwertbare Antwort geliefert."
        )

        return

    print(
        f"JARVIS: {answer}"
    )

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    await update.message.reply_text(
        answer
    )

    # --------------------------------------------------------
    # FISH AUDIO
    # --------------------------------------------------------

    audio_data = text_zu_sprache(
        answer
    )

    if not audio_data:

        print(
            "JARVIS: Keine Audioantwort erzeugt."
        )

        return

    audio_file = io.BytesIO(
        audio_data
    )

    audio_file.name = "jarvis.mp3"

    await update.message.reply_audio(
        audio=audio_file,
        title="JARVIS",
        performer="JARVIS",
    )

    print(
        "JARVIS: Stimme an Telegram gesendet."
    )


# ============================================================
# TEXT VERARBEITEN
# ============================================================

def verarbeite_text(
    user_text,
):

    recherchieren = soll_recherchieren(
        user_text
    )

    print(
        f"Liam: {user_text}"
    )

    print(
        f"Recherche notwendig: "
        f"{recherchieren}"
    )

    return frage_ki(
        user_text,
        recherchieren=recherchieren,
    )


# ============================================================
# TELEGRAM
# ============================================================

async def handle_update(
    update,
    context,
):

    if not update.message:

        return

    message = update.message

    # ========================================================
    # TEXT
    # ========================================================

    if message.text:

        user_text = (
            message.text.strip()
        )

        if not user_text:

            return

        answer = verarbeite_text(
            user_text
        )

        await sende_jarvis_antwort(
            update,
            answer,
        )

        return

    # ========================================================
    # VOICE
    # ========================================================

    if message.voice:

        print(
            "===================================="
        )

        print(
            "Liam (Voice): "
            "Sprachnachricht erhalten."
        )

        print(
            f"Voice Länge: "
            f"{message.voice.duration} Sekunden"
        )

        try:

            telegram_file = (
                await context.bot.get_file(
                    message.voice.file_id
                )
            )

            audio_bytes = bytes(
                await telegram_file.download_as_bytearray()
            )

            print(
                f"Audio heruntergeladen: "
                f"{len(audio_bytes)} Bytes"
            )

            transcribed_text = (
                sprache_zu_text(
                    audio_bytes,
                    "voice.ogg",
                    "audio/ogg",
                )
            )

            if not transcribed_text:

                await message.reply_text(
                    "Ich konnte deine "
                    "Sprachnachricht nicht verstehen."
                )

                return

            print(
                f"Liam (transkribiert): "
                f"{transcribed_text}"
            )

            answer = verarbeite_text(
                transcribed_text
            )

            await sende_jarvis_antwort(
                update,
                answer,
            )

        except Exception as error:

            print(
                "Voice-Verarbeitungsfehler:"
            )

            print(
                f"{type(error).__name__}: {error}"
            )

            await message.reply_text(
                "Bei der Verarbeitung deiner "
                "Sprachnachricht ist etwas schiefgelaufen."
            )

        return

    # ========================================================
    # AUDIO-DATEI
    # ========================================================

    if message.audio:

        print(
            "Liam (Audio): "
            "Audiodatei erhalten."
        )

        try:

            telegram_file = (
                await context.bot.get_file(
                    message.audio.file_id
                )
            )

            audio_bytes = bytes(
                await telegram_file.download_as_bytearray()
            )

            file_name = (
                message.audio.file_name
                or "audio.mp3"
            )

            mime_type = (
                message.audio.mime_type
                or "audio/mpeg"
            )

            transcribed_text = (
                sprache_zu_text(
                    audio_bytes,
                    file_name,
                    mime_type,
                )
            )

            if not transcribed_text:

                await message.reply_text(
                    "Ich konnte die "
                    "Audiodatei nicht verstehen."
                )

                return

            answer = verarbeite_text(
                transcribed_text
            )

            await sende_jarvis_antwort(
                update,
                answer,
            )

        except Exception as error:

            print(
                "Audio-Verarbeitungsfehler:"
            )

            print(
                f"{type(error).__name__}: {error}"
            )

            await message.reply_text(
                "Bei der Verarbeitung der "
                "Audiodatei ist etwas schiefgelaufen."
            )

        return


# ============================================================
# BOT STARTEN
# ============================================================

def main():

    required_variables = {
        "TELEGRAM_TOKEN":
            TELEGRAM_TOKEN,

        "GROQ_API_KEY":
            GROQ_API_KEY,

        "FISH_API_KEY":
            FISH_API_KEY,

        "FISH_VOICE_ID":
            FISH_VOICE_ID,
    }

    missing = [
        name
        for name, value
        in required_variables.items()
        if not value
    ]

    if missing:

        raise RuntimeError(
            "Folgende Environment Variables fehlen: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # RENDER HEALTH SERVER
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True,
    )

    web_thread.start()

    # --------------------------------------------------------
    # TELEGRAM
    # --------------------------------------------------------

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        MessageHandler(
            filters.ALL,
            handle_update,
        )
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    print(
        "===================================="
    )

    print(
        "JARVIS ist online."
    )

    print(
        "Groq KI: AKTIV"
    )

    print(
        "Groq Browser Search: BEREIT"
    )

    print(
        "Groq Speech-to-Text: AKTIV"
    )

    print(
        "Fish Audio: AKTIV"
    )

    print(
        "OpenRouter: NICHT VERWENDET"
    )

    print(
        "Render Web Server: AKTIV"
    )

    print(
        "Warte auf Telegram-Nachrichten..."
    )

    print(
        "===================================="
    )

    application.run_polling()


# ============================================================
# PROGRAMMSTART
# ============================================================

if __name__ == "__main__":

    main()
