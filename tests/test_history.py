import json

import pytest

import file_atelier.history as history_module
from file_atelier.cli import main
from file_atelier.config import load_config
from file_atelier.engine import build_plan
from file_atelier.gui_state import GuiSession
from file_atelier.history import (
    FORMAT_VERSION,
    HistoryError,
    apply_plan_with_history,
    build_undo_plan,
    execute_undo,
)


def _prepare_sorting(tmp_path, names=("notes.txt",)):
    source = tmp_path / "source"
    source.mkdir()
    for name in names:
        (source / name).write_text(f"содержимое {name}", encoding="utf-8")
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"Документы": [".txt"]}), encoding="utf-8")
    config = load_config(config_path)
    return source, config_path, config


def _latest_record(source):
    path = max((source / ".file-atelier" / "history").glob("*.json"))
    return path, json.loads(path.read_text(encoding="utf-8"))


def test_preview_does_not_create_history_but_apply_does(tmp_path):
    source, config_path, config = _prepare_sorting(tmp_path)
    plan = build_plan(source, config)

    assert not (source / ".file-atelier").exists()

    result = apply_plan_with_history(plan, config_path)
    history_path, record = _latest_record(source)

    assert result.history_path == history_path
    assert result.summary.moved == 1
    assert record["format_version"] == FORMAT_VERSION
    assert record["config_sha256"]
    assert record["status"] == "completed"
    assert record["operations"][0]["source"] == "notes.txt"
    assert record["operations"][0]["destination"] == "Документы/notes.txt"
    assert "sha256" in record["operations"][0]


def test_service_directory_is_never_sorted(tmp_path):
    source, config_path, config = _prepare_sorting(tmp_path)
    apply_plan_with_history(build_plan(source, config), config_path)
    (source / "new.txt").write_text("новый", encoding="utf-8")

    plan = build_plan(source, config, recursive=True)

    assert [operation.source.name for operation in plan.operations] == ["new.txt"]
    assert all(".file-atelier" not in operation.source.parts for operation in plan.operations)


def test_partial_apply_journals_only_completed_moves(tmp_path, monkeypatch):
    source, config_path, config = _prepare_sorting(tmp_path, ("a.txt", "b.txt"))
    plan = build_plan(source, config)
    real_execute = history_module.execute_operation
    calls = 0

    def fail_second(source_root, operation):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("искусственная ошибка операции")
        real_execute(source_root, operation)

    monkeypatch.setattr(history_module, "execute_operation", fail_second)

    result = apply_plan_with_history(plan, config_path)
    _, record = _latest_record(source)

    assert result.summary.moved == 1
    assert len(result.summary.errors) == 1
    assert [operation["source"] for operation in record["operations"]] == ["a.txt"]
    assert record["status"] == "partial"


def test_undo_preview_changes_nothing_and_apply_restores_file(tmp_path):
    source, config_path, config = _prepare_sorting(tmp_path)
    apply_plan_with_history(build_plan(source, config), config_path)
    moved = source / "Документы" / "notes.txt"

    plan = build_undo_plan(source)

    assert moved.exists()
    assert not (source / "notes.txt").exists()
    assert not plan.conflicts

    summary = execute_undo(plan)
    _, record = _latest_record(source)

    assert summary.moved == 1
    assert (source / "notes.txt").exists()
    assert not moved.exists()
    assert not (source / "Документы").exists()
    assert record["status"] == "undone"


def test_undo_never_overwrites_occupied_original_path(tmp_path):
    source, config_path, config = _prepare_sorting(tmp_path)
    apply_plan_with_history(build_plan(source, config), config_path)
    original = source / "notes.txt"
    original.write_text("новый файл", encoding="utf-8")

    plan = build_undo_plan(source)

    assert plan.conflicts[0].conflict == "исходный путь уже занят"
    with pytest.raises(HistoryError, match="конфликтами"):
        execute_undo(plan)
    assert original.read_text(encoding="utf-8") == "новый файл"
    assert (source / "Документы" / "notes.txt").exists()


@pytest.mark.parametrize("change", ["missing", "modified"])
def test_missing_or_modified_destination_is_a_conflict(tmp_path, change):
    source, config_path, config = _prepare_sorting(tmp_path)
    apply_plan_with_history(build_plan(source, config), config_path)
    moved = source / "Документы" / "notes.txt"
    if change == "missing":
        moved.unlink()
    else:
        moved.write_text("изменено", encoding="utf-8")

    plan = build_undo_plan(source)

    assert len(plan.conflicts) == 1
    assert "отсутствует" in plan.conflicts[0].conflict or "измен" in plan.conflicts[0].conflict


def test_repeated_undo_is_rejected(tmp_path):
    source, config_path, config = _prepare_sorting(tmp_path)
    apply_plan_with_history(build_plan(source, config), config_path)
    execute_undo(build_undo_plan(source))

    with pytest.raises(HistoryError, match="уже отменена"):
        build_undo_plan(source)


def test_damaged_history_is_rejected(tmp_path):
    source = tmp_path / "source"
    history = source / ".file-atelier" / "history"
    history.mkdir(parents=True)
    (history / "broken.json").write_text("{bad", encoding="utf-8")

    with pytest.raises(HistoryError, match="повреждён"):
        build_undo_plan(source)


def test_forged_path_outside_source_is_rejected(tmp_path):
    source = tmp_path / "source"
    history = source / ".file-atelier" / "history"
    history.mkdir(parents=True)
    record = {
        "format_version": FORMAT_VERSION,
        "operation_id": "forged",
        "created_at": "2026-07-21T00:00:00+00:00",
        "source_root": str(source.resolve()),
        "operations": [
            {
                "source": "../outside.txt",
                "destination": "Документы/notes.txt",
                "size": 1,
                "sha256": "0" * 64,
            }
        ],
        "status": "completed",
    }
    (history / "forged.json").write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(HistoryError, match="запрещённый компонент"):
        build_undo_plan(source)


def test_cli_and_gui_use_shared_undo_logic(tmp_path, capsys):
    source, config_path, _config = _prepare_sorting(tmp_path, ("cli.txt",))
    assert main(["--path", str(source), "--config", str(config_path), "--apply"]) == 0

    assert main([str(source), "--undo-last"]) == 0
    assert (source / "Документы" / "cli.txt").exists()
    assert main([str(source), "--undo-last", "--apply"]) == 0
    assert (source / "cli.txt").exists()
    capsys.readouterr()

    (source / "gui.txt").write_text("gui", encoding="utf-8")
    session = GuiSession(str(source), str(config_path))
    session.build()
    session.apply()
    assert session.build_undo().operations
    assert session.undo().moved == 2
    assert (source / "gui.txt").exists()
