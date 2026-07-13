"""Delegate identity-matching — the safety-critical logic that decides whose
messages the delegate is allowed to quote. A false match = attributing one
person's words to another (the worst delegate failure)."""
import delegate


class TestIsTarget:
    def test_display_name_matches_full_name(self):
        assert delegate._is_target("Tim Smith", ["Tim"]) is True

    def test_full_name_matches_display_name(self):
        assert delegate._is_target("Tim", ["Tim Smith"]) is True

    def test_exact_match(self):
        assert delegate._is_target("Tim Smith", ["Tim Smith"]) is True

    def test_prefix_collision_rejected(self):
        # The bug: "Timothy Jones" must NOT match target "Tim"
        assert delegate._is_target("Timothy Jones", ["Tim"]) is False

    def test_substring_collision_rejected(self):
        assert delegate._is_target("Sammy Lee", ["Sam"]) is False
        assert delegate._is_target("Daniela Cruz", ["Dan"]) is False

    def test_different_person_rejected(self):
        assert delegate._is_target("Rosario Bennet", ["Tim Smith"]) is False

    def test_case_insensitive(self):
        assert delegate._is_target("TIM SMITH", ["tim smith"]) is True

    def test_multiple_known_names(self):
        # display + real name both known; either can match
        assert delegate._is_target("Tim Smith", ["tsmith", "Tim Smith"]) is True

    def test_empty_author_rejected(self):
        assert delegate._is_target("", ["Tim"]) is False

    def test_empty_names_rejected(self):
        assert delegate._is_target("Tim Smith", []) is False


class TestAuthorOf:
    def test_extracts_author_from_rts_title(self):
        assert delegate._author_of({"title": "Tim Smith in #general"}) == "Tim Smith"

    def test_handles_missing_title(self):
        assert delegate._author_of({}) == ""

    def test_no_channel_marker(self):
        assert delegate._author_of({"title": "Tim Smith"}) == "Tim Smith"
