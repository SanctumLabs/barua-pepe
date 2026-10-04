import sys

from app.logger import configure_log_sink


def test_unset_environment_uses_development_file_sink(monkeypatch):
    monkeypatch.delenv("ENV", raising=False)

    assert configure_log_sink("info") == "logs/info.log"


def test_non_development_environment_uses_stdout(monkeypatch):
    monkeypatch.setenv("ENV", "production")

    assert configure_log_sink("info") is sys.stdout
