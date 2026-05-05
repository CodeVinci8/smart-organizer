import json
import shutil


from pathlib import Path


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


def load_config(path: Path) -> dict:
    """Умное чтение json-конфигурации

    Функция принимает путь к файлу с конфигурацией, читает ее и возвращает словарь.
    Из-за сложности прописания каждого Ключа - расширения, вида: Папка: ["Список расширений"],
    написан скрипт, который не только читает конфиг, но и перезаписывает конфиг в виде:
    Расширение: Папка"""
    if not path.exists():
        raise FileNotFoundError("Директория или файл не найдены.")

    with open(path, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
            if isinstance(data, dict):
                normalized = {}

                for folder, extension in data.items():
                    if isinstance(folder, str) and isinstance(extension, list):

                        for ext in extension:
                            ext_norm = ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                            normalized[ext_norm] = folder
                    else:
                        raise ValueError("Все значения должны быть списками")
            else:
                raise ValueError("Конфиг JSON не является словарем.")

            return normalized

        except json.JSONDecodeError:
            raise ValueError("В конфиге JSON содержится ошибка.")

