from core.engine import organize_files


def test_organize_files_moves_files_by_config(tmp_path):
    source = tmp_path / "source"
    source.mkdir()

    (source / "text.txt").write_text("text", encoding="utf-8")
    (source / "image.jpg").touch()
    (source / "archive.zip").touch()

    config = {
        ".txt": "Documents",
        ".jpg": "Images",
        ".zip": "Archives"
    }

    organize_files(source, config, dry_run=False)

    assert (source / "Documents" / "text.txt").exists()
    assert (source / "Images" / "image.jpg").exists()
    assert (source / "Archives" / "archive.zip").exists()

    assert not (source / "text.txt").exists()
    assert not (source / "image.jpg").exists()
    assert not (source / "archive.zip").exists()


def test_organize_files_moves_unknown_extensions_to_other(tmp_path):
    source = tmp_path / "source"
    source.mkdir()

    (source / "unknown.exe").touch()

    config = {}

    organize_files(source, config, dry_run=False)

    assert (source / "Other" / "unknown.exe").exists()

    assert not (source / "unknown.exe").exists()


def test_organize_files_dry_run_does_not_move_files(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()

    (source / "text.txt").touch()

    config = {
        ".txt": "Documents"
    }

    organize_files(source, config, dry_run=True)

    captured = capsys.readouterr()

    assert (source / "text.txt").exists()
    assert not (source / "Documents").exists()
    assert not (source / "Documents" / "text.txt").exists()

    assert "[DRY RUN]" in captured.out
    assert "text.txt" in captured.out
    assert "Documents" in captured.out

