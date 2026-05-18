import pytest


from core.engine import scan_directory


def test_scan_directory_returns_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "file1.txt").write_text("hello", encoding="utf-8")
    (source / "image.jpg").write_text("hello", encoding="utf-8")

    result = scan_directory(source)

    file_names = {file_path.name for file_path in result}

    assert file_names == {"file1.txt", "image.jpg"}


def test_scan_directory_finds_nested_files(tmp_path):
    source = tmp_path / "source"
    nested = source / "nested"
    source.mkdir()
    nested.mkdir()

    (source / "root.txt").write_text("hello", encoding="utf-8")
    (nested / "inside.pdf").write_text("hello", encoding="utf-8")

    result = scan_directory(source)

    file_names = {file_path.name for file_path in result}

    assert file_names == {"root.txt", "inside.pdf"}


def test_scan_directory_raises_for_missing_path(tmp_path):
    missing_path = tmp_path / "missing"

    with pytest.raises(FileNotFoundError):
        scan_directory(missing_path)

