"""Substance scoring arithmetic — the anti-workslop math. These are the
deterministic components (no LLM): density, fluff, and the final formula.
The design invariant: substance EARNS points, style only SUBTRACTS, so
zero-substance content can never score well."""
import substance


class TestDensityScore:
    def test_zero_units_scores_zero(self):
        assert substance._density_score(0, 100) == 0

    def test_three_units_per_100_words_maxes(self):
        assert substance._density_score(3, 100) == 100

    def test_dense_message_high(self):
        assert substance._density_score(8, 60) == 100  # capped

    def test_empty_text_no_divide_by_zero(self):
        assert substance._density_score(5, 0) == 0

    def test_linear_below_threshold(self):
        # 1.5 units / 100 words = half of the 3/100 max
        assert substance._density_score(3, 200) == 50


class TestFluffScore:
    def test_no_filler_zero_penalty(self):
        score, hits = substance._fluff_score("we shipped v2 on Tuesday", 5)
        assert score == 0
        assert hits == []

    def test_filler_detected(self):
        text = "we should leverage synergies and circle back to touch base"
        score, hits = substance._fluff_score(text, 10)
        assert score > 0
        assert len(hits) >= 2  # "leverage synergies", "circle back", "touch base"

    def test_empty_text(self):
        score, hits = substance._fluff_score("", 0)
        assert score == 0


class TestGrade:
    def test_high_substance(self):
        emoji, label = substance.grade(90)
        assert label == "high substance"

    def test_low_substance(self):
        emoji, label = substance.grade(20)
        assert label == "low substance"

    def test_boundary(self):
        # 45 is the demo threshold; >= 45 is not "low"
        _, label = substance.grade(45)
        assert label != "low substance"


class TestScoringInvariant:
    """The core design guarantee, exercised via the pure component math:
    zero substantive units can never yield a passing score."""

    def test_zero_units_caps_score(self):
        # final = 0.6*density + 0.2*grounded + 0.2*novelty - 0.25*fluff
        # with density=0 (no units), even perfect grounded+novelty caps at 40
        density = substance._density_score(0, 150)
        best = round(0.6 * density + 0.2 * 100 + 0.2 * 100 - 0.25 * 0)
        assert best <= 40  # below the 45 "substance" threshold by construction
