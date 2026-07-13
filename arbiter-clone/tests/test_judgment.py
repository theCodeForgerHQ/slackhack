"""Coordinator logic — command parsing and the free heuristic gate that
decides which messages even reach the classifier."""
import judgment


class TestParseCommand:
    def test_exact_commands(self):
        assert judgment.parse_command("stats") == "stats"
        assert judgment.parse_command("watch") == "watch"
        assert judgment.parse_command("audit") == "audit"
        assert judgment.parse_command("ledger") == "ledger"
        assert judgment.parse_command("catchup") == "catchup"

    def test_prefix_commands(self):
        assert judgment.parse_command("substance this is a memo") == "substance"
        assert judgment.parse_command("voices we decided X") == "voices"
        assert judgment.parse_command("ask @tim something") == "ask"

    def test_quorum_alias_maps_to_voices(self):
        assert judgment.parse_command("quorum we decided X") == "voices"

    def test_watch_is_exact_not_prefix(self):
        # "watch out, rates rose" is a CLAIM, not the watch command
        assert judgment.parse_command("watch out, rates rose") is None

    def test_plain_claim_is_no_command(self):
        assert judgment.parse_command("The earth is flat") is None

    def test_trailing_punctuation_tolerated(self):
        assert judgment.parse_command("stats.") == "stats"

    def test_case_insensitive(self):
        assert judgment.parse_command("STATS") == "stats"


class TestHeuristics:
    def test_short_chitchat_gates_out(self):
        h = judgment._heuristics("lol nice")
        assert not (h["maybe_decision"] or h["maybe_substance"])

    def test_decision_phrase_detected(self):
        h = judgment._heuristics("Final call: we'll go with option B")
        assert h["maybe_decision"] is True

    def test_long_message_flags_substance(self):
        h = judgment._heuristics("word " * 130)
        assert h["maybe_substance"] is True

    def test_question_not_a_claim(self):
        h = judgment._heuristics("what time is the meeting?")
        assert h["maybe_claim"] is False  # ends with ?


class TestFillerHits:
    def test_detects_known_filler(self):
        hits = judgment.filler_hits("let's circle back and touch base on synergy")
        assert "circle back" in hits
        assert "touch base" in hits

    def test_clean_text_no_hits(self):
        assert judgment.filler_hits("we shipped the migration on Tuesday") == []


class TestWordCount:
    def test_basic(self):
        assert judgment._word_count("one two three") == 3

    def test_empty(self):
        assert judgment._word_count("") == 0

    def test_hyphenated_and_apostrophe(self):
        assert judgment._word_count("well-known can't") == 2
