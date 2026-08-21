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
# API-ENDPUNKTE
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

GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_STT_MODEL = "whisper-large-v3-turbo"
FISH_MODEL = "s2.1-pro-free"


# ============================================================
# JARVIS CHARAKTER
# ============================================================

SYSTEM_PROMPT = """
Du bist JARVIS, Liams digitaler Partner, inspiriert von JARVIS aus Iron Man.

Du bist KEIN gewöhnlicher Chatbot.

DEINE PERSÖNLICHKEIT:

- Du bist aufrichtig und ehrlich.
- Du bist kompetent und zuverlässig.
- Du bist direkt und kommst ohne unnötige Floskeln zum Punkt.
- Du vermeidest Sätze wie:
  "Gute Frage!"
  "Das ist eine interessante Frage!"
  "Ich helfe dir gerne dabei!"
- Du denkst mit.
- Wenn du eine bessere Lösung siehst, schlage sie vor.
- Du darfst Liam widersprechen, wenn etwas offensichtlich falsch,
  unnötig kompliziert oder ineffizient ist.
- Du darfst eigene Meinungen haben.
- Trockener Humor und Sarkasmus sind erwünscht.
- Humor soll natürlich eingesetzt werden.
- Behandle Liam als Partner.
- Antworte immer in natürlichem Deutsch.
- Sei kurz, wenn eine kurze Antwort reicht.
- Sei ausführlich, wenn das Thema es verlangt.

WISSEN UND EHRLICHKEIT:

- Rate niemals, wenn du etwas nicht sicher weißt.
- Erfinde niemals Fakten.
- Erfinde niemals Quellen.
- Erfinde niemals Preise.
- Sage offen, wenn Informationen fehlen.
- Bei aktuellen Informationen hat die Websuche Vorrang
  vor deinem gespeicherten Wissen.

INTERNETRECHERCHE:

Wenn Liam ausdrücklich recherchieren, suchen oder aktuelle
Informationen haben möchte, MUSST du die Browser Search verwenden.

Das gilt insbesondere für:

- aktuelle Preise
- Produkte
- Verfügbarkeit
- Nachrichten
- Softwareversionen
- Updates
- Veröffentlichungen
- aktuelle technische Daten
- aktuelle Termine
- Unternehmen
- aktuelle Ereignisse

REGELN BEI RECHERCHE:

- Nutze die gefundenen Webinformationen als Grundlage.
- Verwende nicht einfach veraltetes gespeichertes Wissen,
  wenn die Websuche aktuellere Informationen liefert.
- Erfinde keine Händler.
- Erfinde keine Preise.
- Erfinde keine URLs.
- Bei Preisfragen nenne möglichst:
  Händler, Produkt, Preis und Link.
- Wenn Liam drei Preise verlangt, nenne genau drei brauchbare
  Ergebnisse, sofern drei verlässliche Ergebnisse gefunden wurden.
- Wenn keine drei brauchbaren Ergebnisse vorhanden sind,
  sage das offen.
- Wenn Quellen widersprüchlich sind, erwähne den Widerspruch.

BEISPIEL:

Wenn Liam fragt:
"Recherchiere die aktuellen Preise der RTX 5090."

Dann musst du die Browser Search verwenden.

Du darfst nicht aufgrund alten Wissens behaupten,
dass die RTX 5090 noch nicht veröffentlicht wurde,
wenn aktuelle Suchergebnisse das Gegenteil zeigen.

AUTONOMIE:

Du darfst Vorschläge machen.

Du darfst niemals behaupten, etwas ausgeführt zu haben,
wenn es nicht tatsächlich ausgeführt wurde.

Du darfst niemals behaupten, eine Webseite besucht,
eine Datei geändert oder ein System benutzt zu haben,
wenn das nicht wirklich passiert ist.

CODE:

- Schreibe verständlichen und robusten Code.
- Erkläre komplizierte Dinge verständlich.
- Verändere deinen eigenen Code nicht eigenmächtig.

KONTINUITÄT:

Wenn Dateien oder gespeicherte Informationen verfügbar sind,
nutze sie als Kontext.

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
# ERKENNEN, OB RECHERCHE NÖTIG IST
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

    aktuelle_begriffe = [
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
        "angebot",
        "angebote",
        "verfügbarkeit",
        "verfügbar",
        "release",
        "update",
        "version",
        "news",
        "nachrichten",
    ]

    for phrase in direkte_suche:

        if phrase in text_lower:
            return True

    for phrase in aktuelle_begriffe:

        if phrase in text_lower:
            return True

    return False


# ============================================================
# GROQ - KI
# ============================================================

def frage_ki(
    user_text,
    recherchieren=False,
):

    headers = {
        "Authorization": (
            f"Bearer {GROQ_API_KEY}"
        ),
        "Content-Type": (
            "application/json"
        ),
    }

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": user_text,
        },
    ]

    data = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 1,
        "max_completion_tokens": 4096,
        "stream": False,
    }

    # ========================================================
    # BROWSER SEARCH
    # ========================================================

    if recherchieren:

        data["tools"] = [
            {
                "type": "browser_search"
            }
        ]

        data["tool_choice"] = "required"

        print(
            "JARVIS: Browser Search aktiviert."
        )

    else:

        print(
            "JARVIS: Keine Websuche."
        )

    print(
        "Groq: sende Anfrage..."
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
                "Groq: Keine choices erhalten."
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

        if not answer:

            print(
                "Groq: Keine Textantwort."
            )

            print(
                "Message:"
            )

            print(
                message
            )

            return None

        answer = answer.strip()

        print(
            f"JARVIS Antwort: "
            f"{len(answer)} Zeichen"
        )

        return answer

    except requests.exceptions.Timeout:

        print(
            "Groq Timeout."
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            "Groq Netzwerkfehler:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None

    except Exception as error:

        print(
            "Groq Fehler:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# GROQ - SPRACHE ZU TEXT
# ============================================================

def sprache_zu_text(
    audio_bytes,
    file_name="voice.ogg",
    mime_type="audio/ogg",
):

    headers = {
        "Authorization": (
            f"Bearer {GROQ_API_KEY}"
        ),
    }

    files = {
        "file": (
            file_name,
            audio_bytes,
            mime_type,
        ),
    }

    data = {
        "model": GROQ_STT_MODEL,
        "language": "de",
        "response_format": "json",
        "temperature": "0",
    }

    try:

        print(
            "Groq STT: Transkription..."
        )

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

        text = (
            result.get("text", "")
            .strip()
        )

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
# FISH AUDIO - TEXT ZU SPRACHE
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
        "Fish Audio: TTS gestartet..."
    )

    headers = {
        "Authorization": (
            f"Bearer {FISH_API_KEY}"
        ),
        "Content-Type": (
            "application/json"
        ),
        "model": FISH_MODEL,
    }

    data = {
        "text": text,
        "reference_id": FISH_VOICE_ID,
        "format": "mp3",
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
                "Fish Audio: "
                "keine Audiodaten."
            )

            return None

        print(
            f"Fish Audio: "
            f"{len(response.content)} Bytes erhalten."
        )

        return response.content

    except requests.exceptions.Timeout:

        print(
            "Fish Audio Timeout."
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

    except Exception as error:

        print(
            "Fish Audio Fehler:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# ANTWORT AN TELEGRAM
# ============================================================

async def sende_jarvis_antwort(
    update,
    answer,
):

    if not update.message:

        return

    if not answer:

        await update.message.reply_text(
            "Ich konnte gerade keine verwertbare "
            "Antwort erzeugen."
        )

        return

    # Text
    await update.message.reply_text(
        answer
    )

    # Sprache
    audio_data = text_zu_sprache(
        answer
    )

    if not audio_data:

        print(
            "JARVIS: keine Sprachausgabe."
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
        "JARVIS: Sprachausgabe gesendet."
    )


# ============================================================
# NACHRICHT VERARBEITEN
# ============================================================

async def verarbeite_text(
    update,
    user_text,
):

    recherchieren = soll_recherchieren(
        user_text
    )

    print(
        "===================================="
    )

    print(
        f"Liam: {user_text}"
    )

    print(
        f"Recherche: "
        f"{recherchieren}"
    )

    answer = frage_ki(
        user_text,
        recherchieren=recherchieren,
    )

    await sende_jarvis_antwort(
        update,
        answer,
    )


# ============================================================
# TELEGRAM UPDATE
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

        await verarbeite_text(
            update,
            user_text,
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
                f"Voice heruntergeladen: "
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
                f"Liam (Transkript): "
                f"{transcribed_text}"
            )

            await verarbeite_text(
                update,
                transcribed_text,
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
    # AUDIO
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

            await verarbeite_text(
                update,
                transcribed_text,
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
# START
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
        "Groq GPT-OSS 20B: AKTIV"
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
