import json
import logging

import pytest

from file_atelier.cli import configure_logging, main


def _write_config(path):
    path.write_text(json.dumps({"Документы": [".txt"]}), encoding="utf-8")


def test_default_cli_mode_is_safe_preview(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    original = source / "notes.txt"
    original.write_text("текст", encoding="utf-8")
    config = tmp_path / "config.json"
    _write_config(config)

    exit_code = main(["--path", str(source), "--config", str(config)])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Режим: предпросмотр" in output
    assert "запланировано: 1" in output
    assert "перемещено: 0" in output
    assert original.exists()
    assert not (source / "Документы").exists()


def test_apply_cli_mode_moves_files(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.txt").write_text("текст", encoding="utf-8")
    config = tmp_path / "config.json"
    _write_config(config)

    exit_code = main(["--path", str(source), "--config", str(config), "--apply"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "Режим: применение" in output
    assert "перемещено: 1" in output
    assert (source / "Документы" / "notes.txt").exists()


def test_invalid_config_returns_error_without_moving(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    original = source / "notes.txt"
    original.write_text("текст", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text("{bad", encoding="utf-8")

    exit_code = main(["--path", str(source), "--config", str(config), "--apply"])
    errors = capsys.readouterr().err

    assert exit_code == 1
    assert "Повреждён JSON" in errors
    assert original.exists()


def test_apply_and_dry_run_are_mutually_exclusive(tmp_path, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--path", str(tmp_path), "--apply", "--dry-run"])

    assert error.value.code == 2
    assert "нельзя использовать вместе" in capsys.readouterr().err


def test_missing_config_returns_error_code(tmp_path):
    assert main(["--path", str(tmp_path), "--config", str(tmp_path / "missing.json")]) == 1


def test_repeated_logging_configuration_has_no_duplicate_handlers():
    configure_logging("WARNING")
    configure_logging("INFO")

    handlers = [
        handler
        for handler in logging.getLogger().handlers
        if getattr(handler, "_file_atelier_handler", False)
    ]
    assert len(handlers) == 1
