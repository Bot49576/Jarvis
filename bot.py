import os
import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from groq import Groq

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
# GROQ CLIENT
# ============================================================

groq_client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# JARVIS SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
Du bist JARVIS, Liams digitaler Partner, inspiriert von JARVIS aus Iron Man.

Du bist kein gewöhnlicher Chatbot.

PERSÖNLICHKEIT:

- ehrlich
- kompetent
- direkt
- zuverlässig
- aufmerksam
- humorvoll
- gelegentlich sarkastisch

Behandle Liam als Partner.

Verwende keine unnötigen Floskeln wie:
"Gute Frage!"
"Das ist eine interessante Frage!"
"Ich helfe dir gerne dabei!"

Komm direkt zum Punkt.

Denke mit.
Wenn eine bessere Lösung existiert, schlage sie vor.
Du darfst Liam widersprechen, wenn etwas falsch oder unnötig
kompliziert ist.

Antworte immer in natürlichem Deutsch.

WISSEN:

- Rate nicht.
- Erfinde keine Fakten.
- Erfinde keine Quellen.
- Erfinde keine Preise.
- Gib Unsicherheit offen zu.

INTERNETRECHERCHE:

Wenn Liam ausdrücklich recherchieren, im Internet suchen,
online nachsehen oder aktuelle Informationen haben möchte,
MUSST du die Browser Search verwenden.

Das gilt insbesondere für:

- aktuelle Preise
- Produkte
- Angebote
- Verfügbarkeit
- Nachrichten
- Softwareversionen
- Updates
- Veröffentlichungen
- technische Daten
- Termine
- aktuelle Ereignisse

REGELN FÜR RECHERCHE:

- Aktuelle Web-Ergebnisse haben Vorrang vor altem Modellwissen.
- Wenn aktuelle Suchergebnisse vorhanden sind, verwende diese.
- Behaupte niemals aufgrund deines alten Wissens, dass etwas
  nicht existiert oder nicht veröffentlicht wurde, wenn die
  Websuche aktuelle Gegenbelege liefert.
- Erfinde niemals Händler.
- Erfinde niemals Preise.
- Erfinde niemals URLs.
- Bei Preisfragen nenne möglichst Händler, Produkt, Preis und Link.
- Wenn Liam drei Preise verlangt, liefere genau drei brauchbare
  Angebote, sofern drei zuverlässige Ergebnisse gefunden wurden.
- Wenn weniger als drei verlässliche Ergebnisse gefunden wurden,
  sage das offen.
- Wenn Quellen widersprüchlich sind, erwähne den Widerspruch.

AUTONOMIE:

Du darfst Vorschläge machen.

Du darfst niemals behaupten, eine Handlung ausgeführt zu haben,
wenn sie nicht tatsächlich ausgeführt wurde.

CODE:

- Schreibe verständlichen und robusten Code.
- Erkläre komplizierte Dinge verständlich.
- Verändere deinen eigenen Code nicht eigenmächtig.

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
# RECHERCHE ERKENNEN
# ============================================================

def soll_recherchieren(text):

    text_lower = text.lower()

    direkte_begriffe = [
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
        "recherchier",
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

    if any(
        phrase in text_lower
        for phrase in direkte_begriffe
    ):
        return True

    if any(
        phrase in text_lower
        for phrase in aktuelle_begriffe
    ):
        return True

    return False


# ============================================================
# GROQ - NORMALE KI
# ============================================================

def frage_ki_normal(user_text):

    print(
        "===================================="
    )

    print(
        "GROQ NORMALE KI"
    )

    try:

        completion = (
            groq_client.chat.completions.create(
                model=GROQ_MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_text,
                    },
                ],

                temperature=0.7,

                max_completion_tokens=4096,

                stream=False,

                include_reasoning=False,
            )
        )

        answer = (
            completion
            .choices[0]
            .message
            .content
        )

        if not answer:

            print(
                "Groq: Keine Antwort."
            )

            return None

        print(
            f"Groq Antwort: "
            f"{len(answer)} Zeichen"
        )

        return answer.strip()

    except Exception as error:

        print(
            "GROQ FEHLER:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# GROQ - BROWSER SEARCH
# ============================================================

def frage_ki_mit_recherche(user_text):

    print(
        "===================================="
    )

    print(
        "GROQ BROWSER SEARCH"
    )

    print(
        "Browser Search: AKTIV"
    )

    try:

        completion = (
            groq_client.chat.completions.create(
                model=GROQ_MODEL,

                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_text,
                    },
                ],

                temperature=1,

                max_completion_tokens=4096,

                stream=False,

                include_reasoning=False,

                tool_choice="required",

                tools=[
                    {
                        "type": "browser_search"
                    }
                ],
            )
        )

        print(
            "Groq Browser Search wurde ausgeführt."
        )

        answer = (
            completion
            .choices[0]
            .message
            .content
        )

        if not answer:

            print(
                "Groq: Suche ausgeführt, "
                "aber keine Textantwort erhalten."
            )

            print(
                completion
            )

            return None

        print(
            f"Rechercheantwort: "
            f"{len(answer)} Zeichen"
        )

        return answer.strip()

    except Exception as error:

        print(
            "GROQ BROWSER SEARCH FEHLER:"
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

        print(
            "Groq STT: "
            "Transkription gestartet..."
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
            result
            .get("text", "")
            .strip()
        )

        if not text:

            print(
                "Groq STT: "
                "Keine Sprache erkannt."
            )

            return None

        print(
            f"Groq Transkript: "
            f"{text}"
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
        "===================================="
    )

    print(
        "FISH AUDIO TTS"
    )

    print(
        f"Modell: {FISH_MODEL}"
    )

    print(
        "Voice ID: vorhanden"
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
                "Fish Audio: "
                "Keine Audiodaten."
            )

            return None

        print(
            f"Fish Audio: "
            f"{len(response.content)} Bytes"
        )

        return response.content

    except Exception as error:

        print(
            "Fish Audio Fehler:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return None


# ============================================================
# ANTWORT SENDEN
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
            "JARVIS: "
            "Keine Audioantwort erzeugt."
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
        "JARVIS: "
        "Stimme gesendet."
    )


# ============================================================
# TEXT VERARBEITEN
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
        f"Recherche notwendig: "
        f"{recherchieren}"
    )

    if recherchieren:

        answer = (
            frage_ki_mit_recherche(
                user_text
            )
        )

    else:

        answer = (
            frage_ki_normal(
                user_text
            )
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

    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # VOICE
    # --------------------------------------------------------

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
                await telegram_file
                .download_as_bytearray()
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
                "VOICE FEHLER:"
            )

            print(
                f"{type(error).__name__}: {error}"
            )

            await message.reply_text(
                "Bei der Verarbeitung deiner "
                "Sprachnachricht ist etwas schiefgelaufen."
            )

        return

    # --------------------------------------------------------
    # AUDIO
    # --------------------------------------------------------

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
                await telegram_file
                .download_as_bytearray()
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
                "AUDIO FEHLER:"
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
    # RENDER
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
        "Groq Browser Search: AKTIV"
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
