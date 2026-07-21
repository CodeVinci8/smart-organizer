import os
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class MoveOperation:
    source: Path
    destination: Path
    category: str
    conflict: bool


@dataclass(frozen=True)
class SortingPlan:
    source: Path
    operations: tuple[MoveOperation, ...]
    skipped: int


@dataclass(frozen=True)
class ExecutionSummary:
    planned: int
    moved: int
    skipped: int
    errors: tuple[str, ...]


def _scan_files(source: Path, recursive: bool) -> tuple[list[Path], int]:
    files: list[Path] = []
    skipped = 0

    if not recursive:
        for entry in source.iterdir():
            if entry.is_symlink():
                skipped += 1
            elif entry.is_file():
                files.append(entry)
    else:
        for root, directory_names, file_names in os.walk(source, topdown=True, followlinks=False):
            root_path = Path(root)
            safe_directories: list[str] = []
            for name in directory_names:
                directory = root_path / name
                if directory.is_symlink():
                    skipped += 1
                else:
                    safe_directories.append(name)
            directory_names[:] = safe_directories

            for name in file_names:
                file_path = root_path / name
                if file_path.is_symlink():
                    skipped += 1
                elif file_path.is_file():
                    files.append(file_path)

    files.sort(key=lambda path: (str(path.relative_to(source)).casefold(), str(path)))
    return files, skipped


def _target_directory(source: Path, category: str) -> Path:
    relative_category = Path(*PurePosixPath(category).parts)
    destination = (source / relative_category).resolve(strict=False)
    try:
        destination.relative_to(source)
    except ValueError as error:
        raise ValueError(
            f"Категория {category!r} выводит файл за пределы исходного каталога."
        ) from error
    return destination


def _path_key(path: Path) -> str:
    return os.path.normcase(str(path))


def _path_exists(path: Path) -> bool:
    return os.path.lexists(path)


def _available_destination(source: Path, directory: Path, reserved: set[str]) -> tuple[Path, bool]:
    destination = directory / source.name
    counter = 1
    conflict = False
    while _path_exists(destination) or _path_key(destination) in reserved:
        conflict = True
        destination = directory / f"{source.stem}_{counter}{source.suffix}"
        counter += 1
    return destination, conflict


def build_plan(source: Path, config: dict[str, str], recursive: bool = False) -> SortingPlan:
    """Сначала вычисляет все назначения, включая конфликты, не изменяя файловую систему."""
    if source.is_symlink():
        raise ValueError("Исходный каталог не должен быть символической ссылкой.")
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Исходный каталог не найден: {source}.")

    source = source.resolve()
    files, skipped = _scan_files(source, recursive)
    operations: list[MoveOperation] = []
    reserved: set[str] = set()

    for file_path in files:
        category = config.get(file_path.suffix.lower(), "Другое")
        destination_directory = _target_directory(source, category)
        if file_path.parent.resolve() == destination_directory:
            skipped += 1
            continue

        destination, conflict = _available_destination(file_path, destination_directory, reserved)
        reserved.add(_path_key(destination))
        operations.append(MoveOperation(file_path, destination, category, conflict))

    return SortingPlan(source, tuple(operations), skipped)


def _move_without_overwrite(source: Path, destination: Path) -> None:
    """Копирует в эксклюзивно созданный файл и удаляет источник только после успеха."""
    destination_created = False
    try:
        with source.open("rb") as source_file, destination.open("xb") as destination_file:
            destination_created = True
            shutil.copyfileobj(source_file, destination_file)
        shutil.copystat(source, destination, follow_symlinks=False)
        source.unlink()
    except BaseException as error:
        if destination_created:
            try:
                destination.unlink()
            except OSError as rollback_error:
                raise OSError(
                    f"{error}; не удалось удалить незавершённый файл назначения: {rollback_error}"
                ) from error
        raise


def execute_plan(plan: SortingPlan) -> ExecutionSummary:
    """Выполняет неизменяемый план и возвращает каждую ошибку вызывающей стороне."""
    moved = 0
    errors: list[str] = []

    for operation in plan.operations:
        try:
            if operation.source.is_symlink() or not operation.source.is_file():
                raise OSError("источник исчез или перестал быть обычным файлом")

            operation.destination.parent.mkdir(parents=True, exist_ok=True)
            resolved_parent = operation.destination.parent.resolve()
            try:
                resolved_parent.relative_to(plan.source)
            except ValueError as error:
                raise OSError(
                    "каталог назначения оказался за пределами исходного каталога"
                ) from error

            _move_without_overwrite(operation.source, operation.destination)
            moved += 1
        except OSError as error:
            errors.append(f"{operation.source} -> {operation.destination}: {error}")

    return ExecutionSummary(len(plan.operations), moved, plan.skipped, tuple(errors))
