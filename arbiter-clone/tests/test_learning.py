"""Closed-loop preference learning — feedback actually changes thresholds,
bounded so a mode can neither be silenced nor made to fire on everything."""
import learning


def setup_function():
    # hermetic: force an empty in-memory cache and make load/save no-ops so
    # tests never touch the graph or any real learning_*.json file.
    learning._cache = {}
    learning._save = lambda: None
    learning._load = lambda: learning._cache if learning._cache is not None else {}


class TestThreshold:
    def test_starts_at_baseline(self):
        learning._cache = {}
        assert learning.threshold("claim") == learning.BASELINES["claim"]

    def test_unknown_mode_zero(self):
        assert learning.threshold("nonsense") == 0


class TestRecord:
    def test_downvote_raises_threshold(self):
        base = learning.threshold("claim")
        learning.record("claim", "down")
        assert learning.threshold("claim") > base  # more reserved

    def test_upvote_lowers_toward_baseline(self):
        learning.record("claim", "down")
        learning.record("claim", "down")
        raised = learning.threshold("claim")
        learning.record("claim", "up")
        assert learning.threshold("claim") < raised

    def test_bounded_above(self):
        for _ in range(50):
            learning.record("claim", "down")
        assert learning.threshold("claim") <= learning.BASELINES["claim"] + learning._MAX_OFF

    def test_bounded_below(self):
        for _ in range(50):
            learning.record("claim", "up")
        assert learning.threshold("claim") >= learning.BASELINES["claim"] + learning._MIN_OFF

    def test_never_silences_or_floods(self):
        # even fully downvoted, threshold stays a usable gate (not 100/not 0)
        for _ in range(50):
            learning.record("delegate", "down")
        t = learning.threshold("delegate")
        assert 0 < t < 100

    def test_unknown_mode_ignored(self):
        learning.record("nonsense", "down")  # must not raise
        assert learning.threshold("nonsense") == 0


class TestSummary:
    def test_baseline_summary(self):
        learning._cache = {}
        assert "baseline" in learning.summary()

    def test_learned_summary_shows_offset(self):
        learning.record("claim", "down")
        assert "claim" in learning.summary()
