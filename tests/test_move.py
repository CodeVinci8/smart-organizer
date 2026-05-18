from core.engine import move_file


def test_move_file_dry_run_does_not_move_file(tmp_path, capsys):
    source = tmp_path / "file.txt"
    source.write_text("hello", encoding="utf-8")

    dest_dir = tmp_path / "Documents"

    move_file(source, dest_dir, dry_run=True)
    captured = capsys.readouterr()

    assert source.exists()
    assert not (dest_dir / "file.txt").exists()
    assert not dest_dir.exists()
    assert "[DRY RUN]" in captured.out
    assert "file.txt" in captured.out
    assert "Documents" in captured.out


def test_move_file_moves_file(tmp_path):
    source = tmp_path / "file.txt"
    source.write_text("hello", encoding="utf-8")

    dest_dir = tmp_path / "Documents"

    move_file(source, dest_dir, dry_run=False)

    result = dest_dir / "file.txt"

    assert result.exists()

    assert not source.exists()
    assert dest_dir.exists()
    assert result.read_text(encoding="utf-8") == "hello"


def test_move_file_renames_on_conflict(tmp_path):
    new_source = tmp_path / "file.txt"
    new_source.write_text("new", encoding="utf-8")
    dest_dir = tmp_path / "Documents"

    dest_dir.mkdir()

    old_source = dest_dir / "file.txt"
    old_source.write_text("old", encoding="utf-8")

    move_file(new_source, dest_dir, dry_run=False)

    renamed_file = dest_dir / "file_1.txt"

    assert old_source.exists()
    assert old_source.read_text(encoding="utf-8") == "old"

    assert renamed_file.exists()
    assert renamed_file.read_text(encoding="utf-8") == "new"

    assert renamed_file.name == "file_1.txt"
    assert not new_source.exists()

