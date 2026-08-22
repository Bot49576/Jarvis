import unittest
from types import SimpleNamespace
from unittest.mock import patch

import bot

from bot import (
    ChatMemory,
    LIAM_BASE_PROFILE,
    MemoryStore,
    forget_command,
    history_contents,
    interaction_input,
    interaction_sources,
    message_contents,
    pronounce_version_numbers,
    response_diagnostics,
    remember_command,
    remove_matching_facts,
    remove_matching_history_turns,
    remove_matching_summary,
    retry_thinking_level,
    source_message,
    telegram_chunks,
    text_for_speech,
    without_source_section,
    wants_deeper_thinking,
    wants_web_search,
)


class JarvisLogicTests(unittest.TestCase):
    def test_liam_profile_is_explicitly_changeable(self):
        self.assertIn("veränderliche Ausgangsbasis", LIAM_BASE_PROFILE)
        self.assertNotIn("10 Jahre", LIAM_BASE_PROFILE)

    def test_research_detection(self):
        self.assertTrue(wants_web_search("Recherchiere aktuelle Grafikkartenpreise"))
        self.assertTrue(wants_web_search("Was gibt es heute Neues?"))
        self.assertTrue(wants_web_search("Welche neuere Vorabversion gibt es?"))
        self.assertFalse(wants_web_search("Erkläre mir Photosynthese"))

    def test_deeper_thinking_is_explicit(self):
        self.assertTrue(wants_deeper_thinking("Denk gründlich darüber nach"))
        self.assertFalse(wants_deeper_thinking("Wie spät ist es?"))

    def test_remember_and_forget_commands(self):
        self.assertEqual(remember_command("Merk dir: Mein Lieblingsspiel ist Minecraft"),
                         "Mein Lieblingsspiel ist Minecraft")
        self.assertEqual(forget_command("Vergiss Minecraft"), "Minecraft")
        remaining, removed = remove_matching_facts(
            ["Mein Lieblingsspiel ist Minecraft", "Ich mag Pizza"], "Minecraft"
        )
        self.assertEqual(removed, ["Mein Lieblingsspiel ist Minecraft"])
        self.assertEqual(remaining, ["Ich mag Pizza"])

    def test_ram_memory_survives_store_roundtrip(self):
        store = MemoryStore("")
        state = ChatMemory(summary="Test", facts=["Liam mag Technik"])
        self.assertFalse(store.save(123, state))
        loaded = store.load(123)
        self.assertEqual(loaded.summary, "Test")
        self.assertEqual(loaded.facts, ["Liam mag Technik"])

    def test_forgetting_removes_the_complete_matching_history_turn(self):
        messages = [
            {"role": "user", "text": "Wie lautet das Testwort?"},
            {"role": "assistant", "text": "Es lautet Kupferfalke."},
            {"role": "user", "text": "Was ist zwei plus zwei?"},
            {"role": "assistant", "text": "Vier."},
        ]
        remaining, removed = remove_matching_history_turns(messages, "Kupferfalke")
        self.assertEqual(removed, 1)
        self.assertEqual(
            remaining,
            [
                {"role": "user", "text": "Was ist zwei plus zwei?"},
                {"role": "assistant", "text": "Vier."},
            ],
        )

    def test_forgetting_removes_matching_summary_section(self):
        summary, removed = remove_matching_summary(
            "Liam mag Pizza. Das Testwort ist Kupferfalke. Liam mag Fußball.",
            "Kupferfalke",
        )
        self.assertEqual(removed, 1)
        self.assertNotIn("Kupferfalke", summary)
        self.assertIn("Pizza", summary)
        self.assertIn("Fußball", summary)

    def test_memory_prompt_does_not_replace_forgotten_fact_with_another(self):
        prompt = bot.memory_context(ChatMemory(facts=["Das Testcodewort ist Nordstern"])).casefold()
        self.assertIn("nenne weder den gelöschten wert", prompt)
        self.assertIn("ersatzweise einen anderen gespeicherten fakt", prompt)

    def test_telegram_messages_are_chunked(self):
        chunks = telegram_chunks("A" * 9_000)
        self.assertGreater(len(chunks), 2)
        self.assertTrue(all(len(chunk) <= 3_900 for chunk in chunks))

    def test_gemini_history_has_valid_roles(self):
        contents = message_contents(
            [
                {"role": "user", "text": "Hallo"},
                {"role": "assistant", "text": "Guten Tag, Sir."},
            ],
            "Was hatten wir besprochen?",
        )
        self.assertEqual([item.role for item in contents], ["user", "model", "user"])

    def test_chat_history_does_not_duplicate_current_question(self):
        history = history_contents(
            [
                {"role": "user", "text": "Hallo"},
                {"role": "assistant", "text": "Guten Tag, Sir."},
            ]
        )
        self.assertEqual([item.role for item in history], ["user", "model"])

    def test_interaction_input_contains_history_and_current_question(self):
        result = interaction_input(
            [
                {"role": "user", "text": "Ich mag Minecraft"},
                {"role": "assistant", "text": "Notiert, Sir."},
            ],
            "Was ist aktuell?",
        )
        self.assertIn("Liam: Ich mag Minecraft", result)
        self.assertIn("JARVIS: Notiert, Sir.", result)
        self.assertIn("Aktuelle Frage von Liam: Was ist aktuell?", result)

    def test_interaction_sources_are_unique(self):
        citation = SimpleNamespace(
            type="url_citation", title="Beispiel", url="https://example.com"
        )
        interaction = SimpleNamespace(
            steps=[
                SimpleNamespace(
                    type="model_output",
                    content=[SimpleNamespace(annotations=[citation, citation])],
                )
            ]
        )
        self.assertEqual(
            interaction_sources(interaction),
            [("Beispiel", "https://example.com")],
        )

    def test_model_source_section_is_removed(self):
        answer = "Die stabile Version ist 26.2.\n\nQuellen:\n- https://example.com"
        self.assertEqual(without_source_section(answer), "Die stabile Version ist 26.2.")

    def test_speech_text_omits_links_sources_and_markdown(self):
        answer = (
            "Die **stabile** Version ist [26.2](https://example.com/version). "
            "Version 26.3 ist noch ein Snapshot.\n\n"
            "Quellen:\n- https://example.com"
        )
        spoken = text_for_speech(answer)
        self.assertEqual(
            spoken,
            "Die stabile Version ist 26 Punkt 2. "
            "Version 26 Punkt 3 ist noch ein Snapshot.",
        )
        self.assertNotIn("http", spoken)
        self.assertNotIn("Quellen", spoken)

    def test_version_pronunciation_does_not_change_dates_or_normal_decimals(self):
        text = "Am 16.06.2026 kostete es 3.5 Euro. Ohne Versionskontext."
        self.assertEqual(pronounce_version_numbers(text), text)

    def test_empty_gemini_answer_is_retried_once(self):
        responses = [
            SimpleNamespace(text="", candidates=[], prompt_feedback=None),
            SimpleNamespace(text="Die zweite Antwort funktioniert.", candidates=[]),
        ]

        class FakeChat:
            def send_message(self, _message):
                return responses.pop(0)

        class FakeChats:
            def __init__(self):
                self.configs = []

            def create(self, **kwargs):
                self.configs.append(kwargs["config"])
                return FakeChat()

        fake_client = SimpleNamespace(chats=FakeChats())
        with patch.object(bot, "gemini_client", fake_client), patch.object(
            bot.time, "sleep"
        ) as sleep:
            reply = bot.ask_gemini("Teste mich", ChatMemory(), False, False)

        self.assertEqual(reply.text, "Die zweite Antwort funktioniert.")
        self.assertEqual(len(fake_client.chats.configs), 2)
        retry_level = fake_client.chats.configs[1].thinking_config.thinking_level
        self.assertEqual(
            str(getattr(retry_level, "value", retry_level)).lower(),
            "minimal",
        )
        sleep.assert_called_once()

    def test_empty_web_answer_is_retried_once(self):
        interactions = [
            SimpleNamespace(output_text="", steps=[]),
            SimpleNamespace(output_text="Die Webantwort funktioniert.", steps=[]),
        ]

        class FakeInteractions:
            def __init__(self):
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                return interactions.pop(0)

        fake_client = SimpleNamespace(interactions=FakeInteractions())
        with patch.object(bot, "gemini_client", fake_client), patch.object(
            bot.time, "sleep"
        ) as sleep:
            reply = bot.ask_gemini("Suche aktuelle Informationen", ChatMemory(), True, False)

        self.assertEqual(reply.text, "Die Webantwort funktioniert.")
        self.assertEqual(len(fake_client.interactions.calls), 2)
        self.assertEqual(
            fake_client.interactions.calls[1]["generation_config"]["thinking_level"],
            "minimal",
        )
        sleep.assert_called_once()

    def test_empty_response_diagnostics_do_not_include_conversation_text(self):
        response = SimpleNamespace(candidates=[], prompt_feedback=None)
        self.assertEqual(response_diagnostics(response), "candidates=0, block=none")

    def test_retry_thinking_level_is_reduced(self):
        self.assertEqual(retry_thinking_level("low"), "minimal")
        self.assertEqual(retry_thinking_level("medium"), "low")

    def test_speech_text_is_shortened_at_sentence_boundary(self):
        answer = " ".join(f"Satz {index}." for index in range(1, 8))
        self.assertEqual(text_for_speech(answer), "Satz 1. Satz 2. Satz 3. Satz 4.")

    def test_source_message_uses_short_clickable_labels(self):
        message = source_message(
            [("minecraft.net", "https://example.com/a-very-long-redirect")]
        )
        self.assertIn('>minecraft.net</a>', message)
        self.assertNotIn("[https://", message)


if __name__ == "__main__":
    unittest.main()
