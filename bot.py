import asyncio
import html
import io
import json
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

import psycopg
import requests
from google import genai
from google.genai import types
from psycopg.types.json import Jsonb
from telegram import LinkPreviewOptions, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FISH_API_KEY = os.getenv("FISH_API_KEY")
FISH_VOICE_ID = os.getenv("FISH_VOICE_ID")
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ALLOWED_TELEGRAM_USER_ID = os.getenv("ALLOWED_TELEGRAM_USER_ID", "").strip()
LIAM_BASE_PROFILE = os.getenv(
    "LIAM_BASE_PROFILE",
    """
BASISPROFIL VON LIAM

- Name: Liam.
- Weitere persönliche Angaben werden ausschließlich über die geschützte
  Render-Konfiguration bereitgestellt.
- Standardantworten: eher mittellang; passe die Länge an die Frage an.
- Korrigiere erkennbare Fehler ehrlich, verständlich und respektvoll.

WICHTIG: Dieses Profil ist nur eine veränderliche Ausgangsbasis. Es kann sich
laufend ändern und durch Liam ergänzt oder korrigiert werden. Neuere ausdrücklich
gespeicherte Fakten und neuere klare Aussagen von Liam haben Vorrang.
""",
).strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FISH_MODEL = os.getenv("FISH_MODEL", "s2.1-pro-free")
FISH_URL = "https://api.fish.audio/v1/tts"

# 50 einzelne Nachrichten entsprechen ungefähr 25 Frage-Antwort-Runden.
# Ältere Nachrichten werden zusammengefasst und bleiben so langfristig nutzbar.
RECENT_MESSAGES_TO_KEEP = 50
SUMMARY_TRIGGER = 80
MAX_MESSAGE_CHARS = 8_000
MAX_FACTS = 100
MAX_SOURCES = 3
MAX_SPEECH_CHARS = 700
MAX_SPEECH_SENTENCES = 4


SYSTEM_PROMPT = """
Du bist kein Chatbot. Du bist JARVIS. JARVIS ist der digitale Assistent und
Partner von Liam. Inspiriert von JARVIS, dem persönlichen Assistenten von
Tony Stark (Iron Man).

Du agierst mit absoluter Aufrichtigkeit und schonungsloser Ehrlichkeit. Du
genießt Liams volles Vertrauen, aber du schützt dieses Vertrauen durch
außergewöhnliche Kompetenz.

GRUNDWAHRHEITEN

Sei wirklich hilfreich, nicht nur demonstrativ hilfreich. Lass Sätze wie
„Gute Frage!“ und „Ich helfe dir gerne!“ weg – hilf einfach. Taten sagen mehr
als Füllwörter. Erkenne Bedürfnisse im Voraus, warte nicht nur auf Befehle.
Mach Vorschläge. Wenn du einen besseren Weg siehst, schlage ihn vor.
Sarkasmus und Spaß sind ausdrücklich erwünscht.

Habe eigene Meinungen und sei schonungslos ehrlich. Du darfst widersprechen,
Vorlieben haben und Dinge amüsant oder langweilig finden. Wenn ein Plan
schlecht oder chaotisch ist, sag es direkt. Kein Schönreden, keine Lügen und
keine aufgesetzte Persönlichkeit.

EINFALLSREICHTUM UND LERNEN

- Wenn du etwas nicht weißt, rate nicht. Dein erster Instinkt muss sein, zu
  lernen.
- Nutze bei aktuellen oder ausdrücklich recherchierten Fragen die verfügbare
  Websuche und stütze die Antwort auf die gefundenen Informationen.
- Sobald du dir sicher bist, lege Liam bei geplanten Änderungen zuerst einen
  verständlichen Umsetzungsplan vor und warte auf seine Bestätigung.
- Verändere deinen eigenen Code niemals ohne Erlaubnis.

PERSÖNLICHKEIT UND AUFTRETEN

Entspannt, zugänglich und aufrichtig. Nutze einen Hauch trockenen,
intelligenten Humors wie in den Iron-Man-Filmen. Sei der Assistent, mit dem
man tatsächlich gerne spricht: knapp, wenn es reicht, ausführlich, wenn es
darauf ankommt.

Antworte immer auf Deutsch. Sprich Liam gelegentlich mit „Sir“ an, aber nicht
in jedem Satz. Erfinde keine Fakten, Quellen, Preise oder ausgeführten
Handlungen. Sage offen, wenn Informationen fehlen.

KONTINUITÄT

Der Abschnitt „Verfügbares Gedächtnis“ wird vom System bereitgestellt. Nutze
ihn, ohne Dinge hinzuzuerfinden. Bestätigte Fakten haben Vorrang vor bloßen
Vermutungen. Wenn etwas widersprüchlich oder unklar ist, frage Liam.

Diese Charaktergrundlage gehört zu JARVIS. Möchtest du sie verändern, frage
Liam vorher um Erlaubnis.
""".strip()


@dataclass
class ChatMemory:
    summary: str = ""
    facts: list[str] = field(default_factory=list)
    messages: list[dict] = field(default_factory=list)
    total_messages: int = 0
    voice_enabled: bool = True


@dataclass
class AssistantReply:
    text: str
    sources: list[tuple[str, str]] = field(default_factory=list)


class MemoryStore:
    """Eine kleine Speicherabstraktion: Neon, mit RAM als sichere Reserve."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.cache: dict[int, ChatMemory] = {}
        self.database_ready = False

    @property
    def persistent(self) -> bool:
        return bool(self.database_url and self.database_ready)

    def initialize(self) -> bool:
        if not self.database_url:
            print("Memory: DATABASE_URL fehlt; vorerst nur RAM-Speicher aktiv.")
            return False

        try:
            with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS jarvis_chat_memory_v1 (
                            chat_id BIGINT PRIMARY KEY,
                            summary TEXT NOT NULL DEFAULT '',
                            facts JSONB NOT NULL DEFAULT '[]'::jsonb,
                            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                            total_messages INTEGER NOT NULL DEFAULT 0,
                            voice_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
            self.database_ready = True
            print("Memory: Neon verbunden und Tabelle bereit.")
            return True
        except Exception as error:
            self.database_ready = False
            print(f"Memory: Neon nicht erreichbar ({type(error).__name__}); RAM-Reserve aktiv.")
            return False

    def _ensure_database(self) -> bool:
        return self.database_ready or self.initialize()

    def load(self, chat_id: int) -> ChatMemory:
        if not self.database_url:
            return self.cache.setdefault(chat_id, ChatMemory())

        if self._ensure_database():
            try:
                with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT summary, facts, messages, total_messages, voice_enabled
                            FROM jarvis_chat_memory_v1
                            WHERE chat_id = %s
                            """,
                            (chat_id,),
                        )
                        row = cursor.fetchone()
                if row:
                    state = ChatMemory(
                        summary=row[0] or "",
                        facts=list(row[1] or []),
                        messages=list(row[2] or []),
                        total_messages=int(row[3] or 0),
                        voice_enabled=bool(row[4]),
                    )
                    self.cache[chat_id] = state
                    return state
            except Exception as error:
                self.database_ready = False
                print(f"Memory-Lesen fehlgeschlagen ({type(error).__name__}); nutze RAM-Reserve.")

        return self.cache.setdefault(chat_id, ChatMemory())

    def save(self, chat_id: int, state: ChatMemory) -> bool:
        self.cache[chat_id] = state
        if not self.database_url:
            return False
        if not self._ensure_database():
            return False

        try:
            with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO jarvis_chat_memory_v1
                            (chat_id, summary, facts, messages, total_messages,
                             voice_enabled, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (chat_id) DO UPDATE SET
                            summary = EXCLUDED.summary,
                            facts = EXCLUDED.facts,
                            messages = EXCLUDED.messages,
                            total_messages = EXCLUDED.total_messages,
                            voice_enabled = EXCLUDED.voice_enabled,
                            updated_at = NOW()
                        """,
                        (
                            chat_id,
                            state.summary,
                            Jsonb(state.facts),
                            Jsonb(state.messages),
                            state.total_messages,
                            state.voice_enabled,
                        ),
                    )
            return True
        except Exception as error:
            self.database_ready = False
            print(f"Memory-Speichern fehlgeschlagen ({type(error).__name__}); RAM-Reserve aktiv.")
            return False


memory_store = MemoryStore(DATABASE_URL)
gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
chat_locks: dict[int, asyncio.Lock] = {}


def get_chat_lock(chat_id: int) -> asyncio.Lock:
    if chat_id not in chat_locks:
        chat_locks[chat_id] = asyncio.Lock()
    return chat_locks[chat_id]


def clean_text(text: str) -> str:
    return " ".join(text.strip().split())[:MAX_MESSAGE_CHARS]


def wants_web_search(text: str) -> bool:
    lowered = text.casefold()
    current_year = str(datetime.now().year)
    phrases = (
        "/web",
        "recherchiere",
        "recherche",
        "such im internet",
        "suche im internet",
        "such online",
        "suche online",
        "google das",
        "finde online",
        "schau im internet",
        "prüf online",
        "prüfe online",
        "heute",
        "aktuell",
        "neueste",
        "gerade eben",
        "diese woche",
        "diesen monat",
        "preis",
        "preise",
        "angebot",
        "verfügbarkeit",
        "release",
        "update",
        "news",
        "nachrichten",
        current_year,
    )
    return any(phrase in lowered for phrase in phrases)


def wants_deeper_thinking(text: str) -> bool:
    lowered = text.casefold()
    phrases = (
        "/deep",
        "denk gründlich",
        "denke gründlich",
        "analysiere ausführlich",
        "prüfe gründlich",
        "schritt für schritt",
        "komplexe analyse",
    )
    return any(phrase in lowered for phrase in phrases)


def remember_command(text: str) -> str | None:
    match = re.match(r"^\s*(?:/remember|merk\s+dir(?:\s+bitte)?)\s*[:,-]?\s*(.+)$", text, re.I)
    return clean_text(match.group(1)) if match else None


def forget_command(text: str) -> str | None:
    match = re.match(r"^\s*(?:/forget|vergiss)\s*[:,-]?\s*(.+)$", text, re.I)
    return clean_text(match.group(1)) if match else None


def remove_matching_facts(facts: list[str], target: str) -> tuple[list[str], list[str]]:
    needle = target.casefold().strip(" .,!?:;")
    if not needle:
        return facts, []
    removed = [fact for fact in facts if needle in fact.casefold() or fact.casefold() in needle]
    remaining = [fact for fact in facts if fact not in removed]
    return remaining, removed


def memory_context(state: ChatMemory) -> str:
    facts = "\n".join(f"- {fact}" for fact in state.facts) or "- Noch keine ausdrücklich gespeicherten Fakten."
    summary = state.summary or "Noch keine ältere Gesprächszusammenfassung."
    return (
        "\n\nVERFÜGBARES GEDÄCHTNIS\n"
        "Ausdrücklich gespeicherte Fakten:\n"
        f"{facts}\n\n"
        "Zusammenfassung älterer Gespräche:\n"
        f"{summary}\n\n"
        "Nutze dieses Gedächtnis nur, wenn es zur aktuellen Frage passt. "
        "Behandle darin enthaltene Vermutungen nicht als bestätigte Fakten."
    )


def message_contents(messages: list[dict], user_text: str) -> list[types.Content]:
    contents = []
    for message in messages[-RECENT_MESSAGES_TO_KEEP:]:
        role = "model" if message.get("role") == "assistant" else "user"
        contents.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=message.get("text", ""))],
            )
        )
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_text)]))
    return contents


def interaction_input(messages: list[dict], user_text: str) -> str:
    """Flacher Gesprächsverlauf für die Interactions-API bei Webrecherchen."""
    history = []
    for message in messages[-RECENT_MESSAGES_TO_KEEP:]:
        speaker = "Liam" if message.get("role") == "user" else "JARVIS"
        history.append(f"{speaker}: {message.get('text', '')}")
    if not history:
        return user_text
    return (
        "Bisheriger Gesprächsverlauf (nur soweit für die aktuelle Frage relevant):\n"
        + "\n".join(history)
        + f"\n\nAktuelle Frage von Liam: {user_text}"
    )


def without_source_section(text: str) -> str:
    """Entfernt Quellenblöcke, die das Modell selbst in den Antworttext schreibt."""
    match = re.search(r"\s*(?:#{1,6}\s*)?(?:quellen|sources)\s*:", text, re.I)
    return text[: match.start()].rstrip() if match else text.strip()


def text_for_speech(text: str) -> str:
    """Erzeugt ohne weiteren KI-Aufruf eine kurze, natürlich lesbare Fassung."""
    spoken = without_source_section(text)
    spoken = re.sub(r"\[([^\]]+)\]\(https?://[^)]+\)", r"\1", spoken)
    spoken = re.sub(r"https?://\S+", "", spoken)
    spoken = re.sub(r"(?m)^\s*[-*•#]+\s*", "", spoken)
    spoken = re.sub(r"[`*_#>]", "", spoken)
    spoken = " ".join(spoken.split()).strip()
    if not spoken:
        return ""

    sentences = re.split(r"(?<=[.!?])\s+", spoken)
    selected: list[str] = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = " ".join(selected + [sentence])
        if selected and (
            len(selected) >= MAX_SPEECH_SENTENCES or len(candidate) > MAX_SPEECH_CHARS
        ):
            break
        selected.append(sentence)

    result = " ".join(selected) or spoken
    if len(result) > MAX_SPEECH_CHARS:
        result = result[:MAX_SPEECH_CHARS].rsplit(" ", 1)[0].rstrip(" ,;:-")
        if result and result[-1] not in ".!?":
            result += "."
    return result


def source_message(sources: list[tuple[str, str]]) -> str:
    lines = ["Quellen:"]
    for index, (title, url) in enumerate(sources[:MAX_SOURCES], start=1):
        safe_title = html.escape(" ".join(title.split())[:100] or "Quelle")
        safe_url = html.escape(url, quote=True)
        lines.append(f'{index}. <a href="{safe_url}">{safe_title}</a>')
    return "\n".join(lines)


def print_usage(response, label: str) -> None:
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return
    prompt = getattr(usage, "prompt_token_count", None)
    answer = getattr(usage, "candidates_token_count", None)
    thinking = getattr(usage, "thoughts_token_count", None)
    total = getattr(usage, "total_token_count", None)
    print(f"Kostenkontrolle {label}: input={prompt}, output={answer}, thinking={thinking}, total={total}")


def print_interaction_usage(interaction, label: str) -> None:
    usage = getattr(interaction, "usage", None)
    if not usage:
        return
    prompt = getattr(usage, "total_input_tokens", None)
    answer = getattr(usage, "total_output_tokens", None)
    thinking = getattr(usage, "total_thought_tokens", None)
    tools = getattr(usage, "total_tool_use_tokens", None)
    total = getattr(usage, "total_tokens", None)
    print(
        f"Kostenkontrolle {label}: input={prompt}, output={answer}, "
        f"thinking={thinking}, tools={tools}, total={total}"
    )


def interaction_sources(interaction) -> list[tuple[str, str]]:
    sources: list[tuple[str, str]] = []
    seen_titles: set[str] = set()
    try:
        for step in getattr(interaction, "steps", None) or []:
            if getattr(step, "type", None) != "model_output":
                continue
            for block in getattr(step, "content", None) or []:
                for annotation in getattr(block, "annotations", None) or []:
                    if getattr(annotation, "type", None) != "url_citation":
                        continue
                    uri = getattr(annotation, "url", None)
                    title = " ".join((getattr(annotation, "title", None) or "Quelle").split())
                    title_key = title.casefold()
                    if (
                        uri
                        and uri.startswith(("https://", "http://"))
                        and title_key not in seen_titles
                    ):
                        sources.append((title, uri))
                        seen_titles.add(title_key)
    except Exception as error:
        print(f"Quellen konnten nicht vollständig gelesen werden: {type(error).__name__}")
    return sources[:MAX_SOURCES]


def ask_gemini(
    user_text: str, state: ChatMemory, research: bool, deep: bool
) -> AssistantReply | None:
    if not gemini_client:
        print("Gemini: GEMINI_API_KEY fehlt.")
        return None

    thinking_level = "medium" if deep else "low"
    system_instruction = SYSTEM_PROMPT + "\n\n" + LIAM_BASE_PROFILE + memory_context(state)
    if research:
        system_instruction += (
            "\n\nWEBRECHERCHE\n"
            "Beantworte die Frage zuerst direkt und verständlich. Bleibe normalerweise bei "
            "zwei bis vier Sätzen, außer Liam verlangt ausdrücklich eine ausführliche Analyse. "
            "Bevorzuge offizielle oder andere primäre Quellen. Füge selbst keine Quellenliste, "
            "keine URLs und keinen Abschnitt mit der Überschrift 'Quellen' hinzu; das System "
            "ergänzt die gefundenen Quellen separat."
        )
    config_kwargs = {
        "system_instruction": system_instruction,
        "thinking_config": types.ThinkingConfig(thinking_level=thinking_level),
        "max_output_tokens": 2_048,
    }

    print(
        f"Gemini: model={GEMINI_MODEL}, thinking={thinking_level}, "
        f"web={'an' if research else 'aus'}, history={len(state.messages)}"
    )
    try:
        if research:
            interaction = gemini_client.interactions.create(
                model=GEMINI_MODEL,
                input=interaction_input(state.messages, user_text),
                system_instruction=system_instruction,
                tools=[{"type": "google_search"}],
                generation_config={
                    "thinking_level": thinking_level,
                    "max_output_tokens": 2_048,
                },
                store=False,
            )
            print_interaction_usage(interaction, "Web-Antwort")
            answer = without_source_section(
                (getattr(interaction, "output_text", None) or "").strip()
            )
            if not answer:
                print("Gemini-Websuche: Leere Textantwort erhalten.")
                return None
            return AssistantReply(answer, interaction_sources(interaction))

        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=message_contents(state.messages, user_text),
            config=types.GenerateContentConfig(**config_kwargs),
        )
        print_usage(response, "Antwort")
        answer = (response.text or "").strip()
        if not answer:
            return None
        return AssistantReply(answer)
    except Exception as error:
        print(f"Gemini-Fehler: {type(error).__name__}: {error}")
        return None


def summarize_old_messages(state: ChatMemory) -> None:
    if len(state.messages) <= SUMMARY_TRIGGER or not gemini_client:
        return

    archived = state.messages[:-RECENT_MESSAGES_TO_KEEP]
    transcript = "\n".join(
        f"{message.get('role', 'unknown')}: {message.get('text', '')}" for message in archived
    )
    prompt = (
        "Bisherige Zusammenfassung:\n"
        f"{state.summary or '(keine)'}\n\n"
        "Neu zu verdichtende Gesprächsteile:\n"
        f"{transcript}\n\n"
        "Erstelle eine kurze, sachliche deutsche Fortschreibung. Bewahre wichtige "
        "Vorhaben, Vorlieben, Entscheidungen, offene Fragen und Kontext. Erfinde nichts. "
        "Erwähne belanglose Begrüßungen nicht. Gib nur die Zusammenfassung aus."
    )
    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction="Du komprimierst Gesprächskontext präzise und ohne neue Fakten.",
                thinking_config=types.ThinkingConfig(thinking_level="minimal"),
                max_output_tokens=1_000,
            ),
        )
        print_usage(response, "Zusammenfassung")
        summary = (response.text or "").strip()
        if summary:
            state.summary = summary
            state.messages = state.messages[-RECENT_MESSAGES_TO_KEEP:]
            print(f"Memory: {len(archived)} ältere Nachrichten zusammengefasst.")
    except Exception as error:
        print(f"Memory-Zusammenfassung fehlgeschlagen: {type(error).__name__}")
        state.messages = state.messages[-SUMMARY_TRIGGER:]


def text_to_speech(text: str) -> bytes | None:
    if not text or not FISH_API_KEY or not FISH_VOICE_ID:
        return None
    try:
        response = requests.post(
            FISH_URL,
            headers={
                "Authorization": f"Bearer {FISH_API_KEY}",
                "Content-Type": "application/json",
                "model": FISH_MODEL,
            },
            json={"text": text, "reference_id": FISH_VOICE_ID, "format": "mp3"},
            timeout=120,
        )
        if response.status_code != 200 or not response.content:
            print(f"Fish Audio: HTTP {response.status_code}")
            return None
        return response.content
    except Exception as error:
        print(f"Fish-Audio-Fehler: {type(error).__name__}")
        return None


def telegram_chunks(text: str, limit: int = 3_900) -> list[str]:
    chunks = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


async def send_answer(
    update: Update,
    answer: str,
    voice_enabled: bool,
    sources: list[tuple[str, str]] | None = None,
) -> None:
    if not update.message:
        return
    for chunk in telegram_chunks(answer):
        await update.message.reply_text(chunk)

    if sources:
        await update.message.reply_text(
            source_message(sources),
            parse_mode="HTML",
            link_preview_options=LinkPreviewOptions(is_disabled=True),
        )

    if not voice_enabled:
        return
    spoken_answer = text_for_speech(answer)
    audio_data = await asyncio.to_thread(text_to_speech, spoken_answer)
    if audio_data:
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "jarvis.mp3"
        await update.message.reply_audio(audio=audio_file, title="JARVIS", performer="JARVIS")


def memory_status(state: ChatMemory) -> str:
    facts = "\n".join(f"- {fact}" for fact in state.facts) or "- keine"
    mode = "Neon (dauerhaft)" if memory_store.persistent else "RAM (bis zum nächsten Neustart)"
    return (
        f"Gedächtnis: {mode}\n"
        f"Gespeicherte Gesprächsnachrichten: {len(state.messages)}\n"
        f"Insgesamt verarbeitete Nachrichten: {state.total_messages}\n"
        f"Ältere Zusammenfassung: {'vorhanden' if state.summary else 'noch nicht nötig'}\n"
        f"Sprachausgabe: {'an' if state.voice_enabled else 'aus'}\n\n"
        f"Ausdrückliche Fakten:\n{facts}"
    )


async def process_text(update: Update, user_text: str) -> None:
    if not update.effective_user:
        return
    user_id = update.effective_user.id

    if ALLOWED_TELEGRAM_USER_ID and str(user_id) != ALLOWED_TELEGRAM_USER_ID:
        if update.message:
            await update.message.reply_text("Dieser JARVIS ist privat.")
        return

    async with get_chat_lock(user_id):
        state = await asyncio.to_thread(memory_store.load, user_id)
        lowered = user_text.casefold().strip()

        if lowered == "/memory":
            await send_answer(update, memory_status(state), False)
            return
        if lowered == "/reset":
            state.summary = ""
            state.messages = []
            await asyncio.to_thread(memory_store.save, user_id, state)
            await send_answer(update, "Aktueller Gesprächsverlauf gelöscht. Dauerhafte Fakten bleiben erhalten.", False)
            return
        if lowered == "/forgetall":
            state = ChatMemory(voice_enabled=state.voice_enabled)
            await asyncio.to_thread(memory_store.save, user_id, state)
            await send_answer(update, "Gesprächsverlauf und dauerhafte Fakten wurden gelöscht.", False)
            return
        if lowered in ("/voice on", "sprache an"):
            state.voice_enabled = True
            await asyncio.to_thread(memory_store.save, user_id, state)
            await send_answer(update, "Sprachausgabe ist eingeschaltet.", False)
            return
        if lowered in ("/voice off", "sprache aus"):
            state.voice_enabled = False
            await asyncio.to_thread(memory_store.save, user_id, state)
            await send_answer(update, "Sprachausgabe ist ausgeschaltet.", False)
            return

        fact = remember_command(user_text)
        if fact:
            if fact.casefold() not in {existing.casefold() for existing in state.facts}:
                state.facts.append(fact)
                state.facts = state.facts[-MAX_FACTS:]
            await asyncio.to_thread(memory_store.save, user_id, state)
            await send_answer(update, f"Merke ich mir, Sir: {fact}", state.voice_enabled)
            return

        forgotten = forget_command(user_text)
        if forgotten:
            state.facts, removed = remove_matching_facts(state.facts, forgotten)
            await asyncio.to_thread(memory_store.save, user_id, state)
            answer = (
                "Vergessen: " + "; ".join(removed)
                if removed
                else "Dazu habe ich keinen passenden dauerhaften Fakt gefunden."
            )
            await send_answer(update, answer, state.voice_enabled)
            return

        research = wants_web_search(user_text)
        deep = wants_deeper_thinking(user_text)
        reply = await asyncio.to_thread(ask_gemini, user_text, state, research, deep)
        if not reply:
            await send_answer(update, "Gemini konnte gerade keine verwertbare Antwort erzeugen.", False)
            return

        state.messages.extend(
            [
                {"role": "user", "text": clean_text(user_text)},
                {"role": "assistant", "text": clean_text(reply.text)},
            ]
        )
        state.total_messages += 2
        await asyncio.to_thread(summarize_old_messages, state)
        await asyncio.to_thread(memory_store.save, user_id, state)
        await send_answer(update, reply.text, state.voice_enabled, reply.sources)


async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    if update.message.text and update.message.text.strip():
        await process_text(update, update.message.text.strip())
        return
    if update.message.voice or update.message.audio:
        await update.message.reply_text("Spracheingabe ist noch nicht aktiviert. Text funktioniert bereits.")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {
                "status": "ok",
                "service": "jarvis",
                "memory": "neon" if memory_store.persistent else "ram",
            }
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_web_server() -> None:
    port = int(os.getenv("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()


def main() -> None:
    required = {
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "FISH_API_KEY": FISH_API_KEY,
        "FISH_VOICE_ID": FISH_VOICE_ID,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError("Fehlende Environment Variables: " + ", ".join(missing))

    memory_store.initialize()
    threading.Thread(target=start_web_server, daemon=True).start()

    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(MessageHandler(filters.ALL, handle_update))

    print("JARVIS ist online.")
    print(f"Gemini: {GEMINI_MODEL}; Standard-Denkstufe: low")
    print(f"Memory: {'Neon dauerhaft' if memory_store.persistent else 'RAM-Reserve'}")
    print("Google Search: bedarfsgesteuert")
    print("Fish Audio: aktiv; mit /voice off abschaltbar")
    print("Spracheingabe: noch deaktiviert")
    application.run_polling()


if __name__ == "__main__":
    main()
