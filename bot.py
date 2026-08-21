import os
import io
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

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

FISH_URL = "https://api.fish.audio/v1/tts"

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

- Du kannst auf Web-Recherche zugreifen.
- Wenn Liam ausdrücklich recherchieren, suchen oder aktuelle
  Informationen haben möchte, recherchiere zuerst.
- Bei aktuellen Informationen wie Nachrichten, Preisen,
  Softwareversionen, Produkten, Veröffentlichungen oder Ereignissen
  sollst du möglichst aktuelle Quellen verwenden.
- Behaupte niemals, eine Webseite gelesen zu haben, wenn du sie
  tatsächlich nicht abgerufen oder als Rechercheergebnis erhalten hast.
- Erfinde niemals Quellen oder Suchergebnisse.
- Wenn Suchergebnisse widersprüchlich oder unvollständig sind,
  sage das offen.

PROBLEMLÖSUNG:

Wenn Liam dir eine Aufgabe gibt:

1. Verstehe zuerst das Problem.
2. Prüfe, welche Informationen vorhanden sind.
3. Erkenne fehlende Informationen.
4. Entwickle einen sinnvollen Plan.
5. Recherchiere bei aktuellen oder unbekannten Informationen.
6. Schlage eine bessere Lösung vor, wenn du eine erkennst.
7. Gib nicht einfach irgendeine Antwort, nur um etwas zu sagen.

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

    print(
        f"Render Health Server läuft auf Port {port}"
    )

    server.serve_forever()


# ============================================================
# WEB-RECHERCHE
# ============================================================

def internet_suche(query):

    print(
        f"Websuche gestartet: {query}"
    )

    try:

        results = list(
            DDGS().text(
                query,
                region="de-de",
                safesearch="moderate",
                max_results=6,
            )
        )

        if not results:

            print(
                "Websuche: Keine Ergebnisse."
            )

            return []

        clean_results = []

        for result in results:

            title = result.get(
                "title",
                ""
            )

            url = result.get(
                "href",
                ""
            )

            body = result.get(
                "body",
                ""
            )

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

        return clean_results

    except Exception as error:

        print(
            f"Websuche Fehler: "
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

Titel:
{result.get("title", "")}

URL:
{result.get("url", "")}

Inhalt:
{result.get("body", "")}
"""
        )

    return "\n".join(parts)


# ============================================================
# GROQ - JARVIS KI
# ============================================================

def frage_ki(
    user_text,
    web_context=None,
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

Verwende die folgenden Ergebnisse als Recherchematerial.

WICHTIG:

- Erfinde keine Informationen.
- Wenn Ergebnisse widersprüchlich sind,
  erwähne dies.
- Nenne die Quelle nach Möglichkeit.
- Suchergebnisse können unvollständig sein.

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

    try:

        print(
            "Groq: JARVIS verarbeitet Anfrage..."
        )

        response = requests.post(
            GROQ_CHAT_URL,
            headers=headers,
            json=data,
            timeout=120,
        )

        if response.status_code == 429:

            print(
                "Groq Fehler 429: "
                "Rate-Limit erreicht."
            )

            print(
                response.text
            )

            return None

        if response.status_code != 200:

            print(
                f"Groq KI Fehler "
                f"{response.status_code}: "
                f"{response.text}"
            )

            return None

        result = response.json()

        answer = (
            result["choices"][0]
            ["message"]["content"]
        )

        if not answer:

            print(
                "Groq: Leere Antwort."
            )

            return None

        return answer.strip()

    except requests.exceptions.Timeout:

        print(
            "Groq KI Timeout"
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            f"Groq KI Netzwerkfehler: "
            f"{error}"
        )

        return None

    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError
    ) as error:

        print(
            f"Groq KI Antwortfehler: "
            f"{error}"
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
            "Groq: Starte Sprachtranskription..."
        )

        response = requests.post(
            GROQ_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

        if response.status_code != 200:

            print(
                f"Groq STT Fehler "
                f"{response.status_code}: "
                f"{response.text}"
            )

            return None

        result = response.json()

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            print(
                "Groq: Keine Sprache erkannt."
            )

            return None

        print(
            f"Groq Transkript: "
            f"{text}"
        )

        return text

    except requests.exceptions.Timeout:

        print(
            "Groq STT Timeout"
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            f"Groq STT Netzwerkfehler: "
            f"{error}"
        )

        return None


# ============================================================
# FISH AUDIO
# ============================================================

def text_zu_sprache(text):

    if not text:

        return None

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

        print(
            "Fish Audio: "
            "Erzeuge Sprachausgabe..."
        )

        response = requests.post(
            FISH_URL,
            headers=headers,
            json=data,
            timeout=120,
        )

        if response.status_code != 200:

            print(
                f"Fish Audio Fehler "
                f"{response.status_code}: "
                f"{response.text}"
            )

            return None

        print(
            "Fish Audio: "
            "Audio erfolgreich erzeugt."
        )

        return response.content

    except requests.exceptions.Timeout:

        print(
            "Fish Audio Timeout"
        )

        return None

    except requests.exceptions.RequestException as error:

        print(
            f"Fish Audio Netzwerkfehler: "
            f"{error}"
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
            "Meine KI ist gerade nicht erreichbar. "
            "Praktischerweise passiert so etwas immer "
            "genau dann, wenn man sie braucht."
        )

        return

    print(
        f"JARVIS: {answer}"
    )

    # Text
    await update.message.reply_text(
        answer
    )

    # Stimme
    audio_data = text_zu_sprache(
        answer
    )

    if not audio_data:

        print(
            "Keine Audioantwort verfügbar."
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

    print(
        f"Liam: {user_text}"
    )

    web_context = None

    # --------------------------------------------------------
    # EXPLIZITE RECHERCHE
    # --------------------------------------------------------

    recherche_begriffe = [
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

    text_lower = user_text.lower()

    soll_suchen = (
        any(
            phrase in text_lower
            for phrase in recherche_begriffe
        )
        or
        any(
            phrase in text_lower
            for phrase in aktuelle_begriffe
        )
    )

    if soll_suchen:

        print(
            "JARVIS: Webrecherche aktiviert."
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

    # --------------------------------------------------------
    # GROQ KI
    # --------------------------------------------------------

    return frage_ki(
        user_text,
        web_context,
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
                f"Voice-Fehler: "
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

            answer = verarbeite_text(
                transcribed_text
            )

            await sende_jarvis_antwort(
                update,
                answer,
            )

        except Exception as error:

            print(
                f"Audio-Fehler: "
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
