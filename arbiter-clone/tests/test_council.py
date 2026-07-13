"""Council debate machinery — the deterministic parts (no LLM): the Free-MAD
anti-conformity block and the split-detection that decides whether a second
round is even needed."""
import council


class TestFreeMadSuffix:
    def test_contains_anti_conformity_rule(self):
        sfx = council._free_mad_suffix([
            {"role": "advocate", "verdict": "True", "confidence": 70,
             "reasoning": "regulators say safe"}])
        assert "majority opinion is NOT evidence" in sfx
        assert "RETAIN" in sfx

    def test_lists_other_positions(self):
        sfx = council._free_mad_suffix([
            {"role": "skeptic", "verdict": "False", "confidence": 80, "reasoning": "x"},
            {"role": "analyst", "verdict": "Misleading", "confidence": 60, "reasoning": "y"}])
        assert "SKEPTIC" in sfx and "ANALYST" in sfx


class TestSplitDetection:
    """run_council early-stops on unanimous verdicts. We exercise the pure
    label-agreement logic that drives that decision."""

    def test_unanimous_is_not_split(self):
        panel = [{"verdict": "True"}, {"verdict": "True"}, {"verdict": "True"}]
        verdicts = {p["verdict"] for p in panel if p["verdict"] in council._SUBSTANTIVE}
        assert len(verdicts) <= 1  # early-stop path

    def test_disagreement_is_split(self):
        panel = [{"verdict": "True"}, {"verdict": "False"}, {"verdict": "True"}]
        verdicts = {p["verdict"] for p in panel if p["verdict"] in council._SUBSTANTIVE}
        assert len(verdicts) > 1  # triggers round 2 + DART

    def test_errors_ignored_in_split_calc(self):
        panel = [{"verdict": "True"}, {"verdict": "Error"}, {"verdict": "True"}]
        verdicts = {p["verdict"] for p in panel if p["verdict"] in council._SUBSTANTIVE}
        assert len(verdicts) <= 1  # Error is not substantive → still unanimous


class TestDartPairing:
    def test_needs_two_distinct_verdicts(self):
        # only one substantive side → no dispute to search
        one_sided = [{"verdict": "False", "reasoning": "a"},
                     {"verdict": "Error", "reasoning": ""}]
        assert council._dart_search(one_sided) == ""
