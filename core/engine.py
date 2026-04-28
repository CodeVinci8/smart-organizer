from pathlib import Path
import shutil


def scan_directory(path: Path) -> list[Path]:
    """ВОЗВРАЩАЕТ СПИСОК ФАЙЛОВ

    Функция возвращает список файлов из директории и вложенных папок.
    """
    files_path = []

    if (not path.exists()) or (not path.is_dir()):
        raise FileNotFoundError("Директория не найдена.")

    for i_path in path.rglob("*"):
        if i_path.is_file():
            files_path.append(i_path.resolve())

    return files_path


def move_file(src: Path, dest_dir: Path, dry_run: bool) -> None:
    """Перемещает файлы

    Функция перемещает файл в папку назначения
    """
    if not src.is_file():
        raise ValueError("Указанный путь не ведёт к файлу.")

    dest_dir.mkdir(parents=True, exist_ok=True)
    destination = dest_dir / src.name

    if dry_run:
        print(f"[DRY RUN] {src} -> {destination}")
    else:
        shutil.move(str(src), str(destination))

