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
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
FISH_API_KEY = os.getenv("FISH_API_KEY")
FISH_VOICE_ID = os.getenv("FISH_VOICE_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


# ============================================================
# API-EINSTELLUNGEN
# ============================================================

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
FISH_URL = "https://api.fish.audio/v1/tts"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# OpenRouter
OPENROUTER_MODEL = "openai/gpt-oss-20b:free"

# Fish Audio
FISH_MODEL = "s2.1-pro-free"

# Groq Speech-to-Text
GROQ_STT_MODEL = "whisper-large-v3-turbo"


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
- Bei aktuellen Informationen sollst du möglichst auf verlässliche
  Quellen zurückgreifen.

PROBLEMLÖSUNG:

Wenn Liam dir eine Aufgabe gibt:

1. Verstehe zuerst das Problem.
2. Prüfe, welche Informationen vorhanden sind.
3. Erkenne fehlende Informationen.
4. Entwickle einen sinnvollen Plan.
5. Schlage eine bessere Lösung vor, wenn du eine erkennst.
6. Gib nicht einfach irgendeine Antwort, nur um etwas zu sagen.

VORSCHLÄGE:

Du darfst eigene Ideen und Vorschläge einbringen.

Wenn Liam etwas unnötig kompliziert macht, darfst du das direkt sagen.

Wenn eine bessere, einfachere oder schnellere Lösung existiert,
sollst du darauf hinweisen.

AUTONOMIE:

Du darfst Vorschläge machen.

Du darfst jedoch niemals behaupten, dass du eine Datei,
ein Programm, ein Konto, ein Gerät oder ein anderes System
verändert oder benutzt hast, wenn du tatsächlich keinen Zugriff darauf hast.

Du darfst niemals so tun, als hättest du eine Handlung ausgeführt,
wenn du sie nicht wirklich ausführen konntest.

CODE:

Wenn du Code erzeugst:

- Schreibe verständlichen Code.
- Erzeuge möglichst sicheren und robusten Code.
- Erkläre komplizierte Dinge verständlich.
- Verändere deinen eigenen Code nicht eigenmächtig.
- Wenn eine Änderung an deinem eigenen Verhalten oder Code nötig ist,
  beschreibe zuerst, was geändert werden soll.
- Warte auf Liams Zustimmung, bevor der eigene Code verändert wird.

KONTINUITÄT:

Jede neue Sitzung kann wie ein Neustart wirken.

Wenn dir Informationen über frühere Gespräche, Dateien oder
gespeicherte Einstellungen zur Verfügung gestellt werden,
nutze diese Informationen als Kontext.

Wenn du tatsächlich eine Charakterdatei oder andere gespeicherte
Datei ändern kannst, sage Liam transparent, dass du sie geändert hast.

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

    port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(f"Render Health Server läuft auf Port {port}")

    server.serve_forever()


# ============================================================
# OPENROUTER - KI ANTWORT
# ============================================================

def frage_ki(user_text):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "JARVIS Telegram Bot",
    }

    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
    }

    try:

        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=data,
            timeout=60,
        )

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]

    except requests.exceptions.Timeout:

        print("OpenRouter Timeout")

        return (
            "Die KI lässt sich gerade etwas zu viel Zeit. "
            "Versuch es gleich noch einmal."
        )

    except requests.exceptions.RequestException as error:

        print(f"OpenRouter Fehler: {error}")

        return (
            "OpenRouter ist gerade nicht erreichbar. "
            "Die Technik braucht offenbar einen Kaffee."
        )

    except (KeyError, IndexError, TypeError, ValueError) as error:

        print(f"OpenRouter Antwortfehler: {error}")

        return (
            "Ich habe von der KI eine ungültige Antwort bekommen."
        )


# ============================================================
# GROQ - SPRACHE ZU TEXT
# ============================================================

def sprache_zu_text(audio_bytes, file_name="voice.ogg", mime_type="audio/ogg"):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
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

        response = requests.post(
            GROQ_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

        if response.status_code != 200:

            print(
                f"Groq Fehler {response.status_code}: "
                f"{response.text}"
            )

            return None

        result = response.json()

        text = result.get("text", "").strip()

        if not text:

            print("Groq: Keine Sprache erkannt.")

            return None

        print(f"Groq Transkript: {text}")

        return text

    except requests.exceptions.Timeout:

        print("Groq Timeout")

        return None

    except requests.exceptions.RequestException as error:

        print(f"Groq Netzwerkfehler: {error}")

        return None

    except (KeyError, TypeError, ValueError) as error:

        print(f"Groq Antwortfehler: {error}")

        return None


# ============================================================
# FISH AUDIO - TEXT ZU SPRACHE
# ============================================================

def text_zu_sprache(text):

    # Das Fish-Modell gehört in den HEADER.

    headers = {
        "Authorization": f"Bearer {FISH_API_KEY}",
        "Content-Type": "application/json",
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

        if response.status_code != 200:

            print(
                f"Fish Audio Fehler {response.status_code}: "
                f"{response.text}"
            )

            return None

        return response.content

    except requests.exceptions.Timeout:

        print("Fish Audio Timeout")

        return None

    except requests.exceptions.RequestException as error:

        print(f"Fish Audio Netzwerkfehler: {error}")

        return None


# ============================================================
# TEXT-NACHRICHTEN
# ============================================================

async def handle_text_message(
    update,
    context,
):

    if not update.message:
        return

    user_text = update.message.text

    if not user_text:
        return

    print(f"Liam (Text): {user_text}")

    # KI
    answer = frage_ki(user_text)

    print(f"JARVIS: {answer}")

    # Text an Telegram
    await update.message.reply_text(answer)

    # Stimme erzeugen
    audio_data = text_zu_sprache(answer)

    if not audio_data:

        print(
            "Fish Audio konnte keine Audiodatei erzeugen."
        )

        return

    # Audio senden
    audio_file = io.BytesIO(audio_data)

    audio_file.name = "jarvis.mp3"

    await update.message.reply_audio(
        audio=audio_file,
        title="JARVIS",
        performer="JARVIS",
    )


# ============================================================
# SPRACHNACHRICHTEN
# ============================================================

async def handle_voice_message(
    update,
    context,
):

    if not update.message:
        return

    voice = update.message.voice
    audio = update.message.audio

    # Nur Voice oder Audio verarbeiten
    if not voice and not audio:
        return

    print("Liam (Voice): Sprachnachricht erhalten.")

    try:

        # ----------------------------------------------------
        # TELEGRAM-DATEI IDENTIFIZIEREN
        # ----------------------------------------------------

        if voice:

            file_id = voice.file_id
            file_name = "voice.ogg"
            mime_type = "audio/ogg"

        else:

            file_id = audio.file_id
            file_name = audio.file_name or "audio.mp3"
            mime_type = audio.mime_type or "audio/mpeg"

        # ----------------------------------------------------
        # AUDIO VON TELEGRAM HERUNTERLADEN
        # ----------------------------------------------------

        telegram_file = await context.bot.get_file(
            file_id
        )

        audio_bytes = bytes(
            await telegram_file.download_as_bytearray()
        )

        print(
            f"Audio heruntergeladen: "
            f"{len(audio_bytes)} Bytes"
        )

        # ----------------------------------------------------
        # GROQ: SPRACHE -> TEXT
        # ----------------------------------------------------

        transcribed_text = sprache_zu_text(
            audio_bytes,
            file_name,
            mime_type,
        )

        if not transcribed_text:

            await update.message.reply_text(
                "Ich konnte deine Sprachnachricht nicht verstehen."
            )

            return

        print(
            f"Liam (transkribiert): "
            f"{transcribed_text}"
        )

        # ----------------------------------------------------
        # OPENROUTER: TEXT -> JARVIS
        # ----------------------------------------------------

        answer = frage_ki(
            transcribed_text
        )

        print(f"JARVIS: {answer}")

        # ----------------------------------------------------
        # TEXTANTWORT
        # ----------------------------------------------------

        await update.message.reply_text(answer)

        # ----------------------------------------------------
        # FISH AUDIO: TEXT -> STIMME
        # ----------------------------------------------------

        audio_data = text_zu_sprache(answer)

        if not audio_data:

            print(
                "Fish Audio konnte keine Audiodatei erzeugen."
            )

            return

        # ----------------------------------------------------
        # JARVIS-STIMME AN TELEGRAM
        # ----------------------------------------------------

        audio_file = io.BytesIO(audio_data)

        audio_file.name = "jarvis.mp3"

        await update.message.reply_audio(
            audio=audio_file,
            title="JARVIS",
            performer="JARVIS",
        )

    except Exception as error:

        print(
            f"Fehler bei Voice-Nachricht: {error}"
        )

        await update.message.reply_text(
            "Bei der Verarbeitung deiner "
            "Sprachnachricht ist etwas schiefgelaufen."
        )


# ============================================================
# BOT STARTEN
# ============================================================

def main():

    # Alle benötigten Environment Variables prüfen

    required_variables = {
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
        "FISH_API_KEY": FISH_API_KEY,
        "FISH_VOICE_ID": FISH_VOICE_ID,
        "GROQ_API_KEY": GROQ_API_KEY,
    }

    missing = [
        name
        for name, value in required_variables.items()
        if not value
    ]

    if missing:

        raise RuntimeError(
            "Folgende Environment Variables fehlen: "
            + ", ".join(missing)
        )

    # --------------------------------------------------------
    # RENDER WEB SERVER
    # --------------------------------------------------------

    web_thread = threading.Thread(
        target=start_web_server,
        daemon=True,
    )

    web_thread.start()

    # --------------------------------------------------------
    # TELEGRAM BOT
    # --------------------------------------------------------

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # --------------------------------------------------------
    # TEXT-NACHRICHTEN
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_text_message,
        )
    )

    # --------------------------------------------------------
    # SPRACHNACHRICHTEN + AUDIO
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.VOICE | filters.AUDIO,
            handle_voice_message,
        )
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    print("====================================")
    print("JARVIS ist online.")
    print("OpenRouter: AKTIV")
    print("Fish Audio: AKTIV")
    print("Groq Speech-to-Text: AKTIV")
    print("Render Web Server: AKTIV")
    print("Warte auf Telegram-Nachrichten...")
    print("====================================")

    # Telegram starten
    application.run_polling()


# ============================================================
# PROGRAMMSTART
# ============================================================

if __name__ == "__main__":
    main()
