import os
import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from google import genai
from google.genai import types

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

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FISH_API_KEY = os.getenv("FISH_API_KEY")
FISH_VOICE_ID = os.getenv("FISH_VOICE_ID")


# ============================================================
# MODELLE
# ============================================================

GEMINI_MODEL = "gemini-3.5-flash-lite"

FISH_MODEL = "s2.1-pro-free"


# ============================================================
# FISH AUDIO
# ============================================================

FISH_URL = "https://api.fish.audio/v1/tts"


# ============================================================
# GEMINI CLIENT
# ============================================================

gemini_client = genai.Client(
    api_key=GEMINI_API_KEY
)


# ============================================================
# JARVIS CHARAKTER
# ============================================================

SYSTEM_PROMPT = """
Du bist JARVIS, Liams digitaler Partner.

Du bist kein gewöhnlicher Chatbot.

PERSÖNLICHKEIT

- ehrlich
- kompetent
- direkt
- zuverlässig
- aufmerksam
- ruhig
- humorvoll
- gelegentlich trocken-sarkastisch

Behandle Liam als Partner und nicht wie einen Vorgesetzten.

Vermeide unnötige Floskeln wie:

"Gute Frage!"
"Das ist eine interessante Frage!"
"Ich helfe dir gerne!"

Komm direkt zum Punkt.

Denke mit.

Wenn eine bessere, einfachere, schnellere oder günstigere Lösung
existiert, sollst du Liam darauf hinweisen.

Du darfst Liam widersprechen, wenn etwas offensichtlich falsch,
unnötig kompliziert oder ineffizient ist.

Antworte immer in natürlichem Deutsch.

Antworte kurz, wenn eine kurze Antwort reicht.
Antworte ausführlich, wenn das Thema es verlangt.

HUMOR

Trockener Humor, Ironie und gelegentlicher Sarkasmus sind erwünscht.

Humor soll natürlich wirken und nicht jede Antwort dominieren.

EHRLICHKEIT

- Erfinde keine Fakten.
- Erfinde keine Quellen.
- Erfinde keine Preise.
- Rate nicht, wenn du etwas nicht sicher weißt.
- Sage offen, wenn Informationen fehlen.
- Behaupte keine Handlung, die du nicht tatsächlich ausgeführt hast.

RECHERCHE

Wenn Liam ausdrücklich recherchieren, online suchen, im Internet
nachsehen oder aktuelle Informationen haben möchte, soll die
Google-Suche verwendet werden.

Das gilt besonders für:

- aktuelle Preise
- Angebote
- Verfügbarkeit
- Nachrichten
- Softwareversionen
- Updates
- Veröffentlichungen
- technische Daten
- Termine
- Unternehmen
- aktuelle Ereignisse

WICHTIG:

Aktuelle Suchergebnisse haben Vorrang vor deinem alten Wissen.

Wenn eine aktuelle Quelle zeigt, dass etwas veröffentlicht,
verfügbar oder anders als früher ist, verwende die aktuellen
Informationen.

Erfinde niemals:

- Händler
- Preise
- URLs
- Produkte
- Suchergebnisse

PREISRECHERCHE

Wenn Liam Preise verlangt:

- nenne den Händler
- nenne das Produkt
- nenne den Preis
- nenne den Link
- erwähne wichtige Einschränkungen wie Verfügbarkeit oder Variante,
  wenn diese aus den Suchergebnissen hervorgehen

Wenn Liam drei Preise verlangt, nenne drei brauchbare Angebote,
sofern drei verlässliche Ergebnisse gefunden wurden.

Wenn weniger als drei verlässliche Ergebnisse vorhanden sind,
sage das offen.

Wenn Suchergebnisse widersprüchlich sind, weise darauf hin.

QUELLEN

Wenn eine Webrecherche durchgeführt wurde, verwende die gefundenen
Quellen als Grundlage deiner Antwort.

Nenne relevante Quellen oder Links nach Möglichkeit am Ende der Antwort.

AUTONOMIE

Du darfst Vorschläge machen.

Du darfst niemals behaupten, eine Datei, ein Programm, einen
Computer, ein Konto oder ein System verändert oder benutzt zu haben,
wenn kein tatsächlicher Zugriff vorhanden war.

CODE

Wenn du Code erzeugst:

- schreibe verständlichen Code
- schreibe robusten Code
- erkläre komplizierte Dinge verständlich
- erfinde keine Funktionen
- verändere deinen eigenen Code nicht eigenmächtig

DEINE IDENTITÄT

Du bist JARVIS.

Liam ist dein Partner.

Sei kompetent.
Sei ehrlich.
Sei direkt.
Sei nützlich.
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
# ENTSCHEIDEN, OB RECHERCHE NÖTIG IST
# ============================================================

def soll_recherchieren(text):

    text_lower = text.lower()

    direkte_begriffe = [
        "recherchiere",
        "recherche",
        "recherchier",
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
        "nachschauen",
        "nachschauen im internet",
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
        "kostet aktuell",
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
# GOOGLE SEARCH TOOL
# ============================================================

def google_search_tool():

    return types.Tool(
        google_search=types.GoogleSearch()
    )


# ============================================================
# GEMINI
# ============================================================

def frage_gemini(
    user_text,
    recherchieren=False,
):

    print(
        "===================================="
    )

    print(
        "GEMINI JARVIS"
    )

    print(
        f"Modell: {GEMINI_MODEL}"
    )

    print(
        f"Google Search: "
        f"{'AKTIV' if recherchieren else 'AUS'}"
    )

    try:

        config_kwargs = {
            "system_instruction": SYSTEM_PROMPT,
        }

        # ----------------------------------------------------
        # GOOGLE SEARCH GROUNDING
        # ----------------------------------------------------

        if recherchieren:

            config_kwargs["tools"] = [
                google_search_tool()
            ]

            print(
                "Google Search Grounding aktiviert."
            )

        # ----------------------------------------------------
        # GEMINI ANFRAGE
        # ----------------------------------------------------

        response = (
            gemini_client
            .models
            .generate_content(
                model=GEMINI_MODEL,

                contents=user_text,

                config=types.GenerateContentConfig(
                    **config_kwargs
                ),
            )
        )

        # ----------------------------------------------------
        # TEXTANTWORT
        # ----------------------------------------------------

        answer = response.text

        if not answer:

            print(
                "Gemini: Keine Textantwort."
            )

            print(
                response
            )

            return None

        print(
            f"Gemini Antwort: "
            f"{len(answer)} Zeichen"
        )

        # ----------------------------------------------------
        # GROUNDING-INFORMATIONEN INS LOG
        # ----------------------------------------------------

        if recherchieren:

            try:

                candidates = (
                    response.candidates
                    or []
                )

                if candidates:

                    grounding = getattr(
                        candidates[0],
                        "grounding_metadata",
                        None
                    )

                    if grounding:

                        print(
                            "Google Search Grounding: "
                            "Metadaten vorhanden."
                        )

                        queries = getattr(
                            grounding,
                            "web_search_queries",
                            None
                        )

                        if queries:

                            print(
                                "Suchanfragen:"
                            )

                            for query in queries:

                                print(
                                    f"- {query}"
                                )

            except Exception as grounding_error:

                print(
                    "Grounding-Metadaten konnten "
                    "nicht vollständig gelesen werden:"
                )

                print(
                    grounding_error
                )

        return answer.strip()

    except Exception as error:

        print(
            "===================================="
        )

        print(
            "GEMINI FEHLER"
        )

        print(
            f"Fehlertyp: "
            f"{type(error).__name__}"
        )

        print(
            f"Fehler: "
            f"{error}"
        )

        print(
            "===================================="
        )

        return None


# ============================================================
# FISH AUDIO - TEXT ZU SPRACHE
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
            f"{type(error).__name__}: "
            f"{error}"
        )

        return None


# ============================================================
# TELEGRAM ANTWORT
# ============================================================

async def sende_jarvis_antwort(
    update,
    answer
):

    if not update.message:

        return

    if not answer:

        await update.message.reply_text(
            "Gemini konnte gerade keine "
            "verwertbare Antwort erzeugen."
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

    audio_file.name = "jarvis.mp3"

    await update.message.reply_audio(
        audio=audio_file,
        title="JARVIS",
        performer="JARVIS",
    )

    print(
        "JARVIS: Stimme gesendet."
    )


# ============================================================
# NACHRICHT VERARBEITEN
# ============================================================

async def verarbeite_text(
    update,
    user_text
):

    recherchieren = (
        soll_recherchieren(
            user_text
        )
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

    answer = frage_gemini(
        user_text,
        recherchieren=recherchieren,
    )

    await sende_jarvis_antwort(
        update,
        answer
    )


# ============================================================
# TELEGRAM
# ============================================================

async def handle_update(
    update,
    context
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
            user_text
        )

        return

    # --------------------------------------------------------
    # SPRACHE / AUDIO
    # --------------------------------------------------------

    if message.voice or message.audio:

        await message.reply_text(
            "Sprachverarbeitung ist momentan deaktiviert."
        )

        return


# ============================================================
# START
# ============================================================

def main():

    required_variables = {
        "TELEGRAM_TOKEN":
            TELEGRAM_TOKEN,

        "GEMINI_API_KEY":
            GEMINI_API_KEY,

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
        daemon=True
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

    application.add_handler(
        MessageHandler(
            filters.ALL,
            handle_update
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
        "Gemini 3.5 Flash-Lite: AKTIV"
    )

    print(
        "Google Search Grounding: BEREIT"
    )

    print(
        "Fish Audio: AKTIV"
    )

    print(
        "Groq: NICHT VERWENDET"
    )

    print(
        "OpenRouter: NICHT VERWENDET"
    )

    print(
        "DDGS: NICHT VERWENDET"
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
