import asyncio
import hashlib
import hmac
import json
import signal
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable

import psycopg
import tornado.httpserver
import tornado.web
from psycopg.types.json import Jsonb
from telegram import Update


MAX_DASHBOARD_SESSIONS = 20
MAX_SESSION_MESSAGES = 100
MAX_SESSION_TITLE_CHARS = 60
MAX_REQUEST_BYTES = 64 * 1024


def dashboard_access_token(telegram_token: str, owner_id: int) -> str:
    payload = f"liam-jarvis-dashboard-v1:{owner_id}".encode("utf-8")
    return hmac.new(telegram_token.encode("utf-8"), payload, hashlib.sha256).hexdigest()


class DashboardSessionStore:
    """Separate UI-Sessions; die bestehende JARVIS-Memory-Tabelle bleibt unberührt."""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.database_ready = False
        self.cache: dict[str, dict] = {}

    def initialize(self) -> bool:
        if not self.database_url:
            return False
        try:
            with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        CREATE TABLE IF NOT EXISTS jarvis_dashboard_sessions_v1 (
                            session_id UUID PRIMARY KEY,
                            owner_id BIGINT NOT NULL,
                            title TEXT NOT NULL,
                            messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        """
                    )
            self.database_ready = True
            return True
        except Exception as error:
            self.database_ready = False
            print(f"Dashboard-Sessions: Neon nicht erreichbar ({type(error).__name__}); RAM-Reserve aktiv.")
            return False

    def _ensure_database(self) -> bool:
        return self.database_ready or self.initialize()

    @staticmethod
    def _default_session_id(owner_id: int) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"liam-jarvis-main:{owner_id}"))

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = " ".join(str(title).strip().split())[:MAX_SESSION_TITLE_CHARS]
        return cleaned or "Neue Unterhaltung"

    def _cache_session(self, session: dict) -> dict:
        self.cache[session["session_id"]] = session
        return session

    def _upsert(self, session: dict) -> None:
        self._cache_session(session)
        if not self._ensure_database():
            return
        try:
            with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO jarvis_dashboard_sessions_v1
                            (session_id, owner_id, title, messages, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (session_id) DO UPDATE SET
                            title = EXCLUDED.title,
                            messages = EXCLUDED.messages,
                            updated_at = NOW()
                        """,
                        (
                            session["session_id"],
                            session["owner_id"],
                            session["title"],
                            Jsonb(session["messages"]),
                        ),
                    )
        except Exception as error:
            self.database_ready = False
            print(f"Dashboard-Session speichern fehlgeschlagen ({type(error).__name__}); RAM-Reserve aktiv.")

    def get(self, owner_id: int, session_id: str) -> dict | None:
        try:
            normalized_id = str(uuid.UUID(session_id))
        except (ValueError, TypeError, AttributeError):
            return None

        cached = self.cache.get(normalized_id)
        if cached and cached["owner_id"] == owner_id:
            return cached

        if self._ensure_database():
            try:
                with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT session_id::text, owner_id, title, messages
                            FROM jarvis_dashboard_sessions_v1
                            WHERE session_id = %s AND owner_id = %s
                            """,
                            (normalized_id, owner_id),
                        )
                        row = cursor.fetchone()
                if row:
                    return self._cache_session(
                        {
                            "session_id": row[0],
                            "owner_id": int(row[1]),
                            "title": row[2],
                            "messages": list(row[3] or []),
                        }
                    )
            except Exception as error:
                self.database_ready = False
                print(f"Dashboard-Session lesen fehlgeschlagen ({type(error).__name__}); RAM-Reserve aktiv.")
        return None

    def create(self, owner_id: int, title: str = "Neue Unterhaltung", session_id: str | None = None) -> dict:
        sessions = self.list(owner_id, ensure_default=False)
        if len(sessions) >= MAX_DASHBOARD_SESSIONS:
            raise ValueError("Maximal 20 Dashboard-Unterhaltungen sind erlaubt.")
        session = {
            "session_id": session_id or str(uuid.uuid4()),
            "owner_id": owner_id,
            "title": self._clean_title(title),
            "messages": [],
        }
        self._upsert(session)
        return session

    def ensure_default(self, owner_id: int) -> dict:
        session_id = self._default_session_id(owner_id)
        existing = self.get(owner_id, session_id)
        return existing or self.create(owner_id, "Hauptunterhaltung", session_id=session_id)

    def list(self, owner_id: int, ensure_default: bool = True) -> list[dict]:
        sessions: list[dict] = []
        if self._ensure_database():
            try:
                with psycopg.connect(self.database_url, connect_timeout=15) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT session_id::text, owner_id, title, messages
                            FROM jarvis_dashboard_sessions_v1
                            WHERE owner_id = %s
                            ORDER BY updated_at DESC
                            LIMIT %s
                            """,
                            (owner_id, MAX_DASHBOARD_SESSIONS),
                        )
                        rows = cursor.fetchall()
                sessions = [
                    self._cache_session(
                        {
                            "session_id": row[0],
                            "owner_id": int(row[1]),
                            "title": row[2],
                            "messages": list(row[3] or []),
                        }
                    )
                    for row in rows
                ]
            except Exception as error:
                self.database_ready = False
                print(f"Dashboard-Sessions lesen fehlgeschlagen ({type(error).__name__}); RAM-Reserve aktiv.")
        if not sessions:
            sessions = [item for item in self.cache.values() if item["owner_id"] == owner_id]
        if not sessions and ensure_default:
            sessions = [self.ensure_default(owner_id)]
        return sessions

    def append_exchange(self, owner_id: int, session_id: str, user_text: str, assistant_text: str) -> dict:
        session = self.get(owner_id, session_id)
        if not session:
            raise LookupError("Unterhaltung nicht gefunden.")
        session["messages"].extend(
            [
                {"role": "user", "text": user_text},
                {"role": "assistant", "text": assistant_text},
            ]
        )
        session["messages"] = session["messages"][-MAX_SESSION_MESSAGES:]
        self._upsert(session)
        return session


@dataclass
class DashboardContext:
    telegram_application: object
    telegram_token: str
    telegram_webhook_secret: str
    owner_id: int | None
    allowed_origin: str
    session_store: DashboardSessionStore
    process_text: Callable[[int, str], Awaitable[object]]
    status: Callable[[], dict]


class JsonHandler(tornado.web.RequestHandler):
    def initialize(self, context: DashboardContext) -> None:
        self.context = context

    def set_default_headers(self) -> None:
        self.set_header("Cache-Control", "no-store")
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "DENY")
        self.set_header("Referrer-Policy", "no-referrer")

    def write_json(self, payload: dict, status: int = 200) -> None:
        self.set_status(status)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps(payload, ensure_ascii=False))

    def require_auth(self) -> bool:
        if self.context.owner_id is None:
            self.write_json({"error": "Dashboard ist noch nicht für ein Gerät freigegeben."}, 503)
            return False
        origin = self.request.headers.get("Origin", "").rstrip("/")
        if origin and origin != self.context.allowed_origin.rstrip("/"):
            self.write_json({"error": "Unzulässiger Ursprung."}, 403)
            return False
        expected = dashboard_access_token(self.context.telegram_token, self.context.owner_id)
        supplied = self.request.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, f"Bearer {expected}"):
            self.write_json({"error": "Gerät nicht freigegeben."}, 401)
            return False
        return True

    def body_json(self) -> dict:
        if not self.request.body:
            return {}
        try:
            payload = json.loads(self.request.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise ValueError("Ungültige JSON-Daten.") from error
        if not isinstance(payload, dict):
            raise ValueError("JSON-Objekt erwartet.")
        return payload


class HealthHandler(JsonHandler):
    async def get(self) -> None:
        self.write_json({"online": True, "service": "liam-jarvis"})


class TelegramWebhookHandler(JsonHandler):
    async def post(self) -> None:
        supplied = self.request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(supplied, self.context.telegram_webhook_secret):
            self.write_json({"error": "forbidden"}, 403)
            return
        try:
            data = self.body_json()
            update = Update.de_json(data=data, bot=self.context.telegram_application.bot)
            await self.context.telegram_application.update_queue.put(update)
        except (ValueError, TypeError):
            self.write_json({"error": "invalid update"}, 400)
            return
        self.write_json({"ok": True})


class DashboardStatusHandler(JsonHandler):
    async def get(self) -> None:
        if not self.require_auth():
            return
        self.write_json(self.context.status())


class DashboardSessionsHandler(JsonHandler):
    async def get(self) -> None:
        if not self.require_auth():
            return
        sessions = await asyncio.to_thread(self.context.session_store.list, self.context.owner_id)
        self.write_json(
            {
                "sessions": [
                    {"session_id": item["session_id"], "title": item["title"]}
                    for item in sessions
                ]
            }
        )

    async def post(self) -> None:
        if not self.require_auth():
            return
        try:
            payload = self.body_json()
            session = await asyncio.to_thread(
                self.context.session_store.create,
                self.context.owner_id,
                payload.get("title", "Neue Unterhaltung"),
            )
        except ValueError as error:
            self.write_json({"error": str(error)}, 400)
            return
        self.write_json(
            {"session_id": session["session_id"], "title": session["title"], "messages": []},
            201,
        )


class DashboardSessionHandler(JsonHandler):
    async def get(self, session_id: str) -> None:
        if not self.require_auth():
            return
        session = await asyncio.to_thread(
            self.context.session_store.get, self.context.owner_id, session_id
        )
        if not session:
            self.write_json({"error": "Unterhaltung nicht gefunden."}, 404)
            return
        self.write_json(
            {
                "session_id": session["session_id"],
                "title": session["title"],
                "messages": session["messages"],
            }
        )


class DashboardChatHandler(JsonHandler):
    async def post(self) -> None:
        if not self.require_auth():
            return
        try:
            payload = self.body_json()
            session_id = str(payload.get("session_id", ""))
            text = " ".join(str(payload.get("text", "")).strip().split())
            if not text:
                raise ValueError("Eine Nachricht fehlt.")
            if len(text) > 8_000:
                raise ValueError("Die Nachricht ist zu lang.")
            session = await asyncio.to_thread(
                self.context.session_store.get, self.context.owner_id, session_id
            )
            if not session:
                self.write_json({"error": "Unterhaltung nicht gefunden."}, 404)
                return
            reply = await self.context.process_text(self.context.owner_id, text)
            await asyncio.to_thread(
                self.context.session_store.append_exchange,
                self.context.owner_id,
                session_id,
                text,
                reply.text,
            )
        except ValueError as error:
            self.write_json({"error": str(error)}, 400)
            return
        self.write_json(
            {
                "text": reply.text,
                "sources": [
                    {"title": title, "url": url} for title, url in reply.sources
                ],
                "voice_enabled": reply.voice_enabled,
            }
        )


class DashboardStaticHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path: str) -> None:
        self.set_header("X-Content-Type-Options", "nosniff")
        self.set_header("X-Frame-Options", "DENY")
        self.set_header("Referrer-Policy", "no-referrer")
        self.set_header(
            "Content-Security-Policy",
            "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
            "style-src 'self'; script-src 'self'; manifest-src 'self'; "
            "worker-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'",
        )
        if path.endswith("sw.js") or path.endswith("index.html"):
            self.set_header("Cache-Control", "no-cache")


def make_web_application(context: DashboardContext, dashboard_path: Path) -> tornado.web.Application:
    return tornado.web.Application(
        [
            (r"/healthz", HealthHandler, {"context": context}),
            (r"/telegram/webhook", TelegramWebhookHandler, {"context": context}),
            (r"/api/dashboard/status", DashboardStatusHandler, {"context": context}),
            (r"/api/dashboard/sessions", DashboardSessionsHandler, {"context": context}),
            (r"/api/dashboard/sessions/([0-9a-fA-F-]+)", DashboardSessionHandler, {"context": context}),
            (r"/api/dashboard/chat", DashboardChatHandler, {"context": context}),
            (r"/", tornado.web.RedirectHandler, {"url": "/dashboard/", "permanent": False}),
            (
                r"/dashboard/(.*)",
                DashboardStaticHandler,
                {"path": str(dashboard_path), "default_filename": "index.html"},
            ),
        ],
        compress_response=True,
        debug=False,
    )


async def run_dashboard_server(
    context: DashboardContext,
    dashboard_path: Path,
    webhook_url: str,
    port: int,
) -> None:
    web_application = make_web_application(context, dashboard_path)
    server = tornado.httpserver.HTTPServer(
        web_application,
        xheaders=True,
        max_body_size=MAX_REQUEST_BYTES,
    )
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for stop_signal in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(stop_signal, stop_event.set)
        except (NotImplementedError, RuntimeError):
            pass

    async with context.telegram_application:
        for attempt in range(1, 6):
            try:
                await context.telegram_application.bot.set_webhook(
                    url=webhook_url,
                    secret_token=context.telegram_webhook_secret,
                    drop_pending_updates=False,
                    max_connections=4,
                )
                break
            except Exception:
                if attempt == 5:
                    raise
                print(f"Telegram-Webhook: Startversuch {attempt}/5 fehlgeschlagen; neuer Versuch.")
                await asyncio.sleep(min(2**attempt, 8))
        await context.telegram_application.start()
        server.listen(port, address="0.0.0.0")
        print(f"Dashboard: Webdienst auf Port {port} aktiv")
        try:
            await stop_event.wait()
        finally:
            server.stop()
            await context.telegram_application.stop()
