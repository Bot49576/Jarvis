import os
import io
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from ddgs import DDGS

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

# Groq KI
GROQ_MODEL = "openai/gpt-oss-20b"

# Groq Sprache -> Text
GROQ_STT_MODEL = "whisper-large-v3-turbo"

# Fish Audio
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
- Bei aktuellen Informationen sollst du möglichst auf verlässliche
  Quellen zurückgreifen.

INTERNETRECHERCHE:

- Wenn Liam ausdrücklich recherchieren, suchen oder aktuelle
  Informationen haben möchte, soll eine Websuche durchgeführt werden.
- Bei aktuellen Preisen, Nachrichten, Produkten, Softwareversionen,
  Veröffentlichungen oder Ereignissen soll recherchiert werden.
- Behaupte niemals, eine Webseite gelesen zu haben, wenn sie nicht
  tatsächlich über die Recherche gefunden wurde.
- Erfinde niemals Suchergebnisse oder Quellen.
- Wenn die Suche keine brauchbaren Ergebnisse liefert, sage das offen.

PROBLEMLÖSUNG:

1. Verstehe zuerst das Problem.
2. Prüfe, welche Informationen vorhanden sind.
3. Erkenne fehlende Informationen.
4. Recherchiere, wenn aktuelle oder unbekannte Informationen benötigt werden.
5. Entwickle einen sinnvollen Plan.
6. Schlage eine bessere Lösung vor, wenn du eine erkennst.
7. Gib nicht einfach irgendeine Antwort, nur um etwas zu sagen.

AUTONOMIE:

Du darfst Vorschläge machen.

Du darfst niemals behaupten, dass du Dateien, Systeme,
Konten oder Geräte verändert oder benutzt hast, wenn du keinen
tatsächlichen Zugriff darauf hast.

CODE:

- Schreibe verständlichen und robusten Code.
- Erkläre komplizierte Dinge verständlich.
- Verändere deinen eigenen Code nicht eigenmächtig.
- Wenn eine Änderung an deinem eigenen Code nötig ist,
  beschreibe zuerst, was geändert werden soll.

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

    port = int(os.getenv("PORT", "10000"))

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthHandler
    )

    print(
        f"Render Health Server läuft auf Port {port}"
    )

    server.serve_forever()


# ============================================================
# WEB-SUCHE
# ============================================================

def internet_suche(query):

    print("====================================")
    print("WEBRECHERCHE START")
    print(f"Suchanfrage: {query}")
    print("====================================")

    try:

        results = list(
            DDGS().text(
                query,
                region="de-de",
                safesearch="moderate",
                max_results=3,
            )
        )

        if not results:

            print(
                "Websuche: Keine Ergebnisse gefunden."
            )

            return []

        clean_results = []

        for result in results:

            title = result.get(
                "title",
                ""
            ).strip()

            url = result.get(
                "href",
                ""
            ).strip()

            body = result.get(
                "body",
                ""
            ).strip()

            # Inhalt bewusst begrenzen
            body = body[:700]

            if not title and not body:
                continue

            clean_results.append(
                {
                    "title": title,
                    "url": url,
                    "body": body,
                }
            )

        print(
            f"Websuche: "
            f"{len(clean_results)} Ergebnisse gefunden."
        )

        for index, result in enumerate(
            clean_results,
            start=1
        ):

            print(
                f"Quelle {index}: "
                f"{result['title']}"
            )

            print(
                f"URL: {result['url']}"
            )

        print("====================================")

        return clean_results

    except Exception as error:

        print(
            "WEBRECHERCHE FEHLER"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        return []


def suche_kontext_erstellen(results):

    if not results:

        return None

    parts = []

    for index, result in enumerate(
        results,
        start=1
    ):

        parts.append(
            f"""
QUELLE {index}
Titel: {result.get("title", "")}
URL: {result.get("url", "")}
Inhalt: {result.get("body", "")}
"""
        )

    context = "\n".join(parts)

    # Zusätzliche Sicherheitsbegrenzung
    return context[:8000]


# ============================================================
# ENTSCHEIDEN, OB RECHERCHE NÖTIG IST
# ============================================================

def soll_recherchieren(text):

    text_lower = text.lower()

    suchbegriffe = [
        "recherchiere",
        "recherche",
        "such im internet",
        "suche im internet",
        "such online",
        "suche online",
        "finde heraus",
        "schau im internet",
        "schau online",
        "prüfe online",
        "prüf online",
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
        "news",
        "nachrichten",
    ]

    for phrase in suchbegriffe:

        if phrase in text_lower:
            return True

    for phrase in aktuelle_begriffe:

        if phrase in text_lower:
            return True

    return False


# ============================================================
# GROQ - JARVIS KI
# ============================================================

def frage_ki(
    user_text,
    web_context=None,
):

    print("====================================")
    print("GROQ KI START")
    print(f"Modell: {GROQ_MODEL}")
    print(
        f"Recherche-Kontext: "
        f"{'JA' if web_context else 'NEIN'}"
    )

    if web_context:
        print(
            f"Recherche-Kontext Länge: "
            f"{len(web_context)} Zeichen"
        )

    print(
        "Sende Anfrage an Groq..."
    )

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
        }
    ]

    if web_context:

        messages.append(
            {
                "role":
                    "system",

                "content":
                    f"""
JARVIS HAT WEBRECHERCHE DURCHGEFÜHRT.

Verwende die folgenden Suchergebnisse als Recherchematerial.

WICHTIG:

- Erfinde keine Informationen.
- Nutze die Suchergebnisse für aktuelle Fakten.
- Wenn Preise genannt werden, nenne Händler und URL,
  sofern aus den Ergebnissen erkennbar.
- Wenn Ergebnisse widersprüchlich sind, erwähne das.
- Die Suchergebnisse können unvollständig sein.

RECHERCHEERGEBNISSE:

{web_context}
"""
            }
        )

    messages.append(
        {
            "role":
                "user",

            "content":
                user_text,
        }
    )

    data = {
        "model":
            GROQ_MODEL,

        "messages":
            messages,

        "temperature":
            0.7,

        "max_completion_tokens":
            2048,

        "stream":
            False,

        "include_reasoning":
            False,
    }

    start_time = time.time()

    try:

        response = requests.post(
            GROQ_CHAT_URL,
            headers=headers,
            json=data,
            timeout=120,
        )

        elapsed = time.time() - start_time

        print(
            f"Groq Antwort erhalten nach "
            f"{elapsed:.2f} Sekunden"
        )

        print(
            f"Groq HTTP Status: "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                "GROQ FEHLERANTWORT:"
            )

            print(
                response.text[:4000]
            )

            print(
                "===================================="
            )

            return None

        result = response.json()

        print(
            "Groq JSON erfolgreich gelesen."
        )

        answer = (
            result["choices"][0]
            ["message"]["content"]
        )

        if not answer:

            print(
                "Groq: Antwort ist leer."
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
            "GROQ TIMEOUT: "
            "Keine Antwort innerhalb von 120 Sekunden."
        )

        print(
            "===================================="
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            "GROQ REQUEST FEHLER:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        print(
            "===================================="
        )

        return None

    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError
    ) as error:

        print(
            "GROQ ANTWORTFORMAT FEHLER:"
        )

        print(
            f"{type(error).__name__}: {error}"
        )

        print(
            "===================================="
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
                response.text[:3000]
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
# FISH AUDIO - TEXT ZU SPRACHE
# ============================================================

def text_zu_sprache(text):

    if not text:

        return None

    print(
        "Fish Audio: Starte TTS..."
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
                "Fish Audio Fehlerantwort:"
            )

            print(
                response.text[:3000]
            )

            return None

        print(
            "Fish Audio: Audio erfolgreich erzeugt."
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

    if not answer:

        await update.message.reply_text(
            "Meine KI hat gerade keine Antwort geliefert."
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
            "JARVIS: Keine Audioantwort."
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
        "JARVIS: Audio gesendet."
    )


# ============================================================
# TEXT VERARBEITEN
# ============================================================

def verarbeite_text(
    user_text,
):

    print("====================================")
    print(
        f"Liam: {user_text}"
    )

    web_context = None

    # --------------------------------------------------------
    # RECHERCHE
    # --------------------------------------------------------

    if soll_recherchieren(
        user_text
    ):

        print(
            "JARVIS: Internetrecherche aktiviert."
        )

        results = internet_suche(
            user_text
        )

        if results:

            web_context = (
                suche_kontext_erstellen(
                    results
                )
            )

            print(
                "JARVIS: Recherche-Kontext erstellt."
            )

        else:

            print(
                "JARVIS: Keine Suchergebnisse."
            )

    else:

        print(
            "JARVIS: Keine Websuche nötig."
        )

    # --------------------------------------------------------
    # GROQ
    # --------------------------------------------------------

    answer = frage_ki(
        user_text,
        web_context,
    )

    print(
        "===================================="
    )

    return answer


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
            "Liam (Voice): Sprachnachricht erhalten."
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
            "Liam (Audio): Audiodatei erhalten."
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
        "Groq KI: AKTIV"
    )

    print(
        "Groq Speech-to-Text: AKTIV"
    )

    print(
        "Fish Audio: AKTIV"
    )

    print(
        "Websuche: AKTIV"
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
