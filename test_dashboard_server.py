import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from tornado.testing import AsyncHTTPTestCase

from dashboard_server import (
    DashboardContext,
    DashboardSessionStore,
    dashboard_access_token,
    make_web_application,
)
import bot


class DashboardSecurityTests(unittest.TestCase):
    def test_access_token_is_stable_owner_bound_and_does_not_expose_secret(self):
        first = dashboard_access_token("telegram-secret", 123)
        self.assertEqual(first, dashboard_access_token("telegram-secret", 123))
        self.assertNotEqual(first, dashboard_access_token("telegram-secret", 124))
        self.assertNotIn("telegram-secret", first)

    def test_ram_sessions_are_separate_and_bounded(self):
        store = DashboardSessionStore("")
        main = store.ensure_default(123)
        second = store.create(123, "Ideen")
        store.append_exchange(123, second["session_id"], "Hallo", "Guten Tag")
        self.assertEqual(store.get(123, main["session_id"])["messages"], [])
        self.assertEqual(len(store.get(123, second["session_id"])["messages"]), 2)
        self.assertIsNone(store.get(124, second["session_id"]))


class SharedProcessingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_store = bot.memory_store
        bot.memory_store = bot.MemoryStore("")
        bot.chat_locks.clear()

    async def asyncTearDown(self):
        bot.memory_store = self.original_store
        bot.chat_locks.clear()

    async def test_memory_command_returns_channel_neutral_reply(self):
        reply = await bot.process_user_text(123, "/memory")
        self.assertIn("Gedächtnis:", reply.text)
        self.assertFalse(reply.voice_enabled)

    async def test_shared_processing_updates_the_same_memory(self):
        remembered = await bot.process_user_text(123, "Merk dir: Nordstern")
        self.assertIn("Nordstern", remembered.text)
        self.assertIn("Nordstern", bot.memory_store.load(123).facts)

        with patch.object(
            bot,
            "ask_gemini",
            return_value=bot.AssistantReply("Bestätigt, Sir."),
        ):
            answered = await bot.process_user_text(123, "Was war das Codewort?")
        self.assertEqual(answered.text, "Bestätigt, Sir.")
        self.assertEqual(len(bot.memory_store.load(123).messages), 2)


class DashboardHttpTests(AsyncHTTPTestCase):
    def get_app(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        dashboard_path = Path(self.temp_directory.name)
        (dashboard_path / "index.html").write_text("JARVIS", encoding="utf-8")
        self.telegram_token = "test-telegram-token"
        self.owner_id = 7356620618
        self.session_store = DashboardSessionStore("")

        async def process_text(owner_id, text):
            self.assertEqual(owner_id, self.owner_id)
            return SimpleNamespace(
                text=f"Antwort auf: {text}",
                sources=[("Quelle", "https://example.com")],
                voice_enabled=True,
            )

        telegram_application = SimpleNamespace(
            bot=SimpleNamespace(), update_queue=asyncio.Queue()
        )
        context = DashboardContext(
            telegram_application=telegram_application,
            telegram_token=self.telegram_token,
            telegram_webhook_secret="webhook-secret",
            owner_id=self.owner_id,
            allowed_origin="https://jarvis.example",
            session_store=self.session_store,
            process_text=process_text,
            status=lambda: {"online": True, "memory": "neon"},
        )
        return make_web_application(context, dashboard_path)

    def tearDown(self):
        self.temp_directory.cleanup()
        super().tearDown()

    def auth_headers(self, origin=None):
        headers = {
            "Authorization": (
                "Bearer " + dashboard_access_token(self.telegram_token, self.owner_id)
            )
        }
        if origin:
            headers["Origin"] = origin
        return headers

    def decode(self, response):
        return json.loads(response.body.decode("utf-8"))

    def test_health_is_public_but_status_requires_device_token(self):
        health = self.fetch("/healthz")
        self.assertEqual(health.code, 200)
        self.assertTrue(self.decode(health)["online"])
        self.assertEqual(self.fetch("/api/dashboard/status").code, 401)
        status = self.fetch("/api/dashboard/status", headers=self.auth_headers())
        self.assertEqual(status.code, 200)
        self.assertEqual(self.decode(status)["memory"], "neon")

    def test_foreign_browser_origin_is_rejected(self):
        response = self.fetch(
            "/api/dashboard/status",
            headers=self.auth_headers("https://foreign.example"),
        )
        self.assertEqual(response.code, 403)

    def test_sessions_and_chat_use_the_protected_interface(self):
        sessions_response = self.fetch(
            "/api/dashboard/sessions", headers=self.auth_headers()
        )
        sessions = self.decode(sessions_response)["sessions"]
        self.assertEqual(len(sessions), 1)
        session_id = sessions[0]["session_id"]

        chat = self.fetch(
            "/api/dashboard/chat",
            method="POST",
            headers=self.auth_headers("https://jarvis.example"),
            body=json.dumps({"session_id": session_id, "text": "Status?"}),
        )
        self.assertEqual(chat.code, 200)
        self.assertEqual(self.decode(chat)["text"], "Antwort auf: Status?")

        loaded = self.fetch(
            f"/api/dashboard/sessions/{session_id}", headers=self.auth_headers()
        )
        self.assertEqual(len(self.decode(loaded)["messages"]), 2)

    def test_telegram_webhook_rejects_missing_secret(self):
        response = self.fetch("/telegram/webhook", method="POST", body="{}")
        self.assertEqual(response.code, 403)

    def test_dashboard_static_files_have_security_headers(self):
        response = self.fetch("/dashboard/")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertIn("default-src 'self'", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
