import unittest
from types import SimpleNamespace

from bot import (
    ChatMemory,
    LIAM_BASE_PROFILE,
    MemoryStore,
    forget_command,
    interaction_input,
    interaction_sources,
    message_contents,
    remember_command,
    remove_matching_facts,
    telegram_chunks,
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


if __name__ == "__main__":
    unittest.main()
