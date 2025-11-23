import os

import pytest

from config_utils import allow_insecure_defaults, ensure_not_placeholder


def test_ensure_not_placeholder_rejects_default(monkeypatch):
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "false")
    with pytest.raises(RuntimeError):
        ensure_not_placeholder("SECRET_KEY", "changeme", {"changeme"}, required=True)


def test_ensure_not_placeholder_warns_when_allowed(monkeypatch, caplog):
    monkeypatch.setenv("ALLOW_INSECURE_DEFAULTS", "true")
    value = ensure_not_placeholder("SECRET_KEY", "changeme", {"changeme"}, required=True)
    assert value == "changeme"
    assert any("placeholder value" in message for message in caplog.messages)
