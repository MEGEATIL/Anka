from anka.core.logging import redact_sensitive_text


def test_log_redaction_masks_common_secret_assignments():
    text = "api_key=abc123 token: bearer-secret parola=Gizli123 şifre:deneme"

    redacted = redact_sensitive_text(text)

    assert "abc123" not in redacted
    assert "bearer-secret" not in redacted
    assert "Gizli123" not in redacted
    assert "deneme" not in redacted
    assert redacted.count("[MASKELENDİ]") == 4


def test_log_redaction_limits_oversized_messages():
    assert len(redact_sensitive_text("x" * 500, limit=40)) == 40
