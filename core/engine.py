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
    """ПЕРЕМЕЩАЕТ ФАЙЛЫ

    Функция перемещает файл в папку назначения
    """
    if not src.is_file():
        raise ValueError("Указанный путь не ведёт к файлу.")

    destination = dest_dir / src.name

    if dry_run:
        print(f"[DRY RUN] {src} -> {destination}")
        return

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(destination))


def load_config(path: Path) -> dict:
    """УМНОЕ ЧТЕНИЕ JSON-КОНФИГУРАЦИИ

    Функция принимает путь к файлу с конфигурацией, читает ее и возвращает словарь.
    Из-за сложности прописания каждого Ключа - расширения, вида: Папка: ["Список расширений"],
    написан скрипт, который не только читает конфиг, но и перезаписывает конфиг в виде:
    Расширение: Папка"""
    if not path.exists():
        raise FileNotFoundError("Директория или файл конфига не найдены.")

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


def organize_files(source: Path, config: dict, dry_run: bool) -> None:
    """ОРГАНИЗОВЫВАЕТ И СОРТИРУЕТ ФАЙЛЫ ПО РАСШИРЕНИЯМ

    Функция получает путь к каталогу, идет по нему и достает список абсолютных
    путей к каждому файлу, принимает Конфиг, далее если в конфиге есть у расширения: папка,
    то добавляет файл туда, если нет то создает папку "Другое" если файл уже есть в папке, то пропускает.
    """
    if not source.exists():
        raise FileNotFoundError("Директория не найдена.")
    elif not source.is_dir():
        raise ValueError("Путь ведёт не к каталогу.")

    files = scan_directory(source)

    for file_path in files:
        extension = file_path.suffix.lower()
        target_folder = config.get(extension)

        if target_folder is None:
            target_folder = "Other"

        dest_dir = source.resolve() / target_folder

        if file_path.parent == dest_dir:
            continue

        move_file(file_path, dest_dir, dry_run)

