"""Config sanity: defaults declared once, env-driven, no hardcoded model strings elsewhere."""

from cornercheck.config import Settings


def test_model_defaults_are_pinned() -> None:
    fields = Settings.model_fields
    assert fields["cornercheck_model"].default == "claude-opus-4-8"
    assert fields["cornercheck_model_fallback"].default == "claude-sonnet-4-6"


def test_demo_fallback_defaults_off() -> None:
    assert Settings.model_fields["cornercheck_demo_fallback"].default is False


def test_secrets_default_empty() -> None:
    for name in ("slack_bot_token", "anthropic_api_key", "cornercheck_ledger_hmac_key"):
        assert Settings.model_fields[name].default == ""
