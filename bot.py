import os
import requests
from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    ContextTypes,
    filters,
)

# ============================================================
# KONFIGURATION
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Kostenloses Modell über OpenRouter
MODEL = "openrouter/free"


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
# OPENROUTER
# ============================================================

def frage_ki(user_text: str) -> str:
    """
    Sendet Liams Nachricht an OpenRouter
    und gibt die Antwort der KI zurück.
    """

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://telegram.org",
        "X-Title": "JARVIS Telegram Bot",
    }

    data = {
        "model": MODEL,
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

        answer = result["choices"][0]["message"]["content"]

        return answer

    except requests.exceptions.Timeout:
        return (
            "Die KI lässt sich gerade etwas zu viel Zeit. "
            "Versuch es gleich noch einmal."
        )

    except requests.exceptions.RequestException as error:
        print(f"OpenRouter Fehler: {error}")

        return (
            "Ich kann OpenRouter gerade nicht erreichen. "
            "Sieht nach einem technischen Problem aus."
        )

    except (KeyError, IndexError, TypeError, ValueError) as error:
        print(f"Antwortfehler: {error}")

        return (
            "Ich habe von der KI eine ungültige Antwort bekommen. "
            "Technik. Sie findet immer einen Weg, sich wichtigzumachen."
        )


# ============================================================
# TELEGRAM NACHRICHTEN
# ============================================================

async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Verarbeitet normale Textnachrichten aus Telegram.
    """

    if not update.message:
        return

    user_text = update.message.text

    if not user_text:
        return

    print(f"Liam: {user_text}")

    answer = frage_ki(user_text)

    print(f"JARVIS: {answer}")

    await update.message.reply_text(answer)


# ============================================================
# BOT STARTEN
# ============================================================

def main():

    if not TELEGRAM_TOKEN:
        raise RuntimeError(
            "TELEGRAM_TOKEN wurde nicht gefunden."
        )

    if not OPENROUTER_API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY wurde nicht gefunden."
        )

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        )
    )

    print("====================================")
    print("JARVIS ist online.")
    print("Warte auf Telegram-Nachrichten...")
    print("====================================")

    application.run_polling()


# ============================================================
# PROGRAMMSTART
# ============================================================

if __name__ == "__main__":
    main()
