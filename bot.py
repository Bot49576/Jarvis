import os
import io
import time
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
# MODELLE
# ============================================================

GROQ_MODEL = "openai/gpt-oss-20b"
GROQ_STT_MODEL = "whisper-large-v3-turbo"
FISH_MODEL = "s2.1-pro-free"


# ============================================================
# API-ENDPUNKTE
# ============================================================

GROQ_STT_URL = (
    "https://api.groq.com/openai/v1/audio/transcriptions"
)

FISH_URL = (
    "https://api.fish.audio/v1/tts"
)


# ============================================================
# GROQ CLIENT
# ============================================================

groq_client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# JARVIS CHARAKTER
# ============================================================

SYSTEM_PROMPT = """
Du bist JARVIS, Liams digitaler Partner.

Persönlichkeit:
- ehrlich
- kompetent
- direkt
- zuverlässig
- ruhig
- humorvoll
- gelegentlich trocken-sarkastisch

Behandle Liam als Partner.

Keine unnötigen Floskeln wie:
"Gute Frage!"
"Das ist eine interessante Frage!"
"Ich helfe dir gerne!"

Komm direkt zum Punkt.
Denke mit.
Wenn eine bessere Lösung existiert, schlage sie vor.
Du darfst Liam widersprechen, wenn etwas falsch oder unnötig
kompliziert ist.

Antworte immer in natürlichem Deutsch.

WISSEN:
- Rate niemals.
- Erfinde keine Fakten.
- Erfinde keine Quellen.
- Erfinde keine Preise.
- Wenn du etwas nicht weißt, sage es.

RECHERCHE:
Wenn Liam ausdrücklich recherchieren oder aktuelle Informationen
möchte, verwende die Browser Search.
Das gilt insbesondere für Preise, Angebote, Verfügbarkeit,
Nachrichten, Updates, Versionen und aktuelle Ereignisse.

Bei Recherche:
- Aktuelle Webinformationen haben Vorrang vor altem Wissen.
- Erfinde keine Händler.
- Erfinde keine Preise.
- Erfinde keine URLs.
- Bei Preisfragen nenne möglichst Händler, Produkt, Preis und Link.
- Wenn drei brauchbare Angebote gefunden werden, nenne drei.
- Wenn weniger gefunden werden, sage das offen.
- Widersprüche zwischen Quellen erwähnen.

AUTONOMIE:
Behaupte niemals, etwas ausgeführt zu haben, wenn es nicht
tatsächlich ausgeführt wurde.

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
# GROQ RATE LIMIT INFORMATION
# ============================================================

def log_rate_limits(headers):

    print("----- GROQ RATE LIMITS -----")

    names = [
        "retry-after",
        "x-ratelimit-limit-requests",
        "x-ratelimit-remaining-requests",
        "x-ratelimit-reset-requests",
        "x-ratelimit-limit-tokens",
        "x-ratelimit-remaining-tokens",
        "x-ratelimit-reset-tokens",
    ]

    for name in names:

        value = headers.get(name)

        if value is not None:

            print(
                f"{name}: {value}"
            )

    print("----------------------------")


def wait_for_retry_after(
    headers
):

    value = headers.get(
        "retry-after"
    )

    if not value:
        return False

    try:

        seconds = float(
            value
        )

        seconds = max(
            1,
            min(seconds, 30)
        )

        print(
            f"Groq verlangt "
            f"eine Pause von {seconds:.1f} Sekunden."
        )

        time.sleep(
            seconds + 0.5
        )

        return True

    except (
        TypeError,
        ValueError
    ):

        return False


# ============================================================
# GROQ KI - NORMAL
# ============================================================

def frage_ki_normal(
    user_text
):

    print(
        "===================================="
    )

    print(
        "GROQ JARVIS"
    )

    max_attempts = 2

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            print(
                f"Groq Versuch "
                f"{attempt}/{max_attempts}"
            )

            completion = (
                groq_client
                .chat
                .completions
                .create(
                    model=GROQ_MODEL,

                    messages=[
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
                    ],

                    temperature=0.6,

                    max_completion_tokens=1200,

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
                    "Groq: Leere Antwort."
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
                f"{type(error).__name__}: "
                f"{error}"
            )

            # SDK-Fehler können zusätzliche Header enthalten.
            response = getattr(
                error,
                "response",
                None
            )

            if response is not None:

                try:

                    log_rate_limits(
                        response.headers
                    )

                    if (
                        getattr(
                            response,
                            "status_code",
                            None
                        ) == 429
                    ):

                        if wait_for_retry_after(
                            response.headers
                        ):

                            continue

                except Exception as header_error:

                    print(
                        "Rate-Limit-Header konnten "
                        "nicht gelesen werden: "
                        f"{header_error}"
                    )

            return None

    return None


# ============================================================
# GROQ KI - MIT BROWSER SEARCH
# ============================================================

def frage_ki_mit_recherche(
    user_text
):

    print(
        "===================================="
    )

    print(
        "GROQ JARVIS + BROWSER SEARCH"
    )

    max_attempts = 2

    for attempt in range(
        1,
        max_attempts + 1
    ):

        try:

            print(
                f"Recherche-Versuch "
                f"{attempt}/{max_attempts}"
            )

            completion = (
                groq_client
                .chat
                .completions
                .create(
                    model=GROQ_MODEL,

                    messages=[
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
                    ],

                    temperature=0.6,

                    max_completion_tokens=1800,

                    stream=False,

                    include_reasoning=False,

                    tool_choice="required",

                    tools=[
                        {
                            "type":
                                "browser_search"
                        }
                    ],
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
                    "Groq Recherche: "
                    "Leere Antwort."
                )

                return None

            print(
                f"Rechercheantwort: "
                f"{len(answer)} Zeichen"
            )

            return answer.strip()

        except Exception as error:

            print(
                "GROQ RECHERCHE FEHLER:"
            )

            print(
                f"{type(error).__name__}: "
                f"{error}"
            )

            response = getattr(
                error,
                "response",
                None
            )

            if response is not None:

                try:

                    log_rate_limits(
                        response.headers
                    )

                    if (
                        getattr(
                            response,
                            "status_code",
                            None
                        ) == 429
                    ):

                        if wait_for_retry_after(
                            response.headers
                        ):

                            continue

                except Exception as header_error:

                    print(
                        "Rate-Limit-Header konnten "
                        "nicht gelesen werden: "
                        f"{header_error}"
                    )

            return None

    return None


# ============================================================
# GROQ SPRACHE -> TEXT
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
            "https://api.groq.com/openai/v1/audio/transcriptions",
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
            f"{type(error).__name__}: "
            f"{error}"
        )

        return None


# ============================================================
# FISH AUDIO
# ============================================================

def text_zu_sprache(
    text
):

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
            "https://api.fish.audio/v1/tts",
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
            f"{type(error).__name__}: "
            f"{error}"
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
            "Die KI ist gerade am Limit. "
            "Ich warte lieber kurz, statt dir irgendeinen Unsinn "
            "vorzusetzen."
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
            "Keine Fish-Audio-Antwort."
        )

        return

    audio_file = io.BytesIO(
        audio_data
    )

    audio_file.name = (
        "jarvis.mp3"
    )

    await update.message.reply_audio(
        audio=audio_file,
        title="JARVIS",
        performer="JARVIS",
    )

    print(
        "JARVIS: Stimme gesendet."
    )


# ============================================================
# TEXT VERARBEITEN
# ============================================================

async def verarbeite_text(
    update,
    user_text,
):

    recherche = soll_recherchieren(
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
        f"{recherche}"
    )

    if recherche:

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
                f"{type(error).__name__}: "
                f"{error}"
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
                f"{type(error).__name__}: "
                f"{error}"
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
        "Rate-Limit-Schutz: AKTIV"
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
