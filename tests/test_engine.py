from pathlib import Path

import pytest

from file_atelier.engine import build_plan, execute_plan


def test_preview_plan_does_not_change_filesystem(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    original = source / "notes.txt"
    original.write_text("текст", encoding="utf-8")

    plan = build_plan(source, {".txt": "Документы"})

    assert len(plan.operations) == 1
    assert original.exists()
    assert not (source / "Документы").exists()


def test_execute_plan_moves_unknown_extension_to_other(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    original = source / "program.bin"
    original.write_bytes(b"data")

    summary = execute_plan(build_plan(source, {}))

    assert summary.moved == 1
    assert not summary.errors
    assert not original.exists()
    assert (source / "Другое" / "program.bin").read_bytes() == b"data"


def test_conflict_gets_next_available_name_without_overwrite(tmp_path):
    source = tmp_path / "source"
    destination = source / "Документы"
    destination.mkdir(parents=True)
    (destination / "notes.txt").write_text("старый", encoding="utf-8")
    (destination / "notes_1.txt").write_text("тоже старый", encoding="utf-8")
    (source / "notes.txt").write_text("новый", encoding="utf-8")

    summary = execute_plan(build_plan(source, {".txt": "Документы"}))

    assert summary.moved == 1
    assert (destination / "notes.txt").read_text(encoding="utf-8") == "старый"
    assert (destination / "notes_1.txt").read_text(encoding="utf-8") == "тоже старый"
    assert (destination / "notes_2.txt").read_text(encoding="utf-8") == "новый"


def test_recursive_scan_requires_explicit_flag(tmp_path):
    source = tmp_path / "source"
    nested = source / "вложенный"
    nested.mkdir(parents=True)
    nested_file = nested / "notes.txt"
    nested_file.write_text("текст", encoding="utf-8")

    direct_plan = build_plan(source, {".txt": "Документы"})
    recursive_plan = build_plan(source, {".txt": "Документы"}, recursive=True)

    assert not direct_plan.operations
    assert [operation.source for operation in recursive_plan.operations] == [nested_file]


def _make_symlink(link: Path, target: Path, directory: bool = False) -> None:
    try:
        link.symlink_to(target, target_is_directory=directory)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"Символические ссылки недоступны в этом окружении: {error}")


def test_symbolic_link_is_skipped(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("не трогать", encoding="utf-8")
    link = source / "link.txt"
    _make_symlink(link, target)

    plan = build_plan(source, {".txt": "Документы"})

    assert not plan.operations
    assert plan.skipped == 1
    assert target.read_text(encoding="utf-8") == "не трогать"


def test_destination_symlink_cannot_escape_source(tmp_path):
    source = tmp_path / "source"
    outside = tmp_path / "outside"
    source.mkdir()
    outside.mkdir()
    (source / "notes.txt").write_text("текст", encoding="utf-8")
    _make_symlink(source / "Документы", outside, directory=True)

    with pytest.raises(ValueError, match="за пределы"):
        build_plan(source, {".txt": "Документы"})


def test_second_run_is_idempotent(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.txt").write_text("текст", encoding="utf-8")
    config = {".txt": "Документы"}

    first_summary = execute_plan(build_plan(source, config))
    second_plan = build_plan(source, config, recursive=True)
    second_summary = execute_plan(second_plan)

    assert first_summary.moved == 1
    assert not second_plan.operations
    assert second_summary.moved == 0
    assert list((source / "Документы").glob("notes*.txt")) == [source / "Документы" / "notes.txt"]


def test_file_appearing_after_planning_is_not_overwritten(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.txt").write_text("новый", encoding="utf-8")
    plan = build_plan(source, {".txt": "Документы"})
    destination = source / "Документы" / "notes.txt"
    destination.parent.mkdir()
    destination.write_text("внешнее изменение", encoding="utf-8")

    summary = execute_plan(plan)

    assert summary.moved == 0
    assert len(summary.errors) == 1
    assert destination.read_text(encoding="utf-8") == "внешнее изменение"
    assert (source / "notes.txt").read_text(encoding="utf-8") == "новый"
