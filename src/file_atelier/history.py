import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from uuid import uuid4

from file_atelier import __version__
from file_atelier.engine import (
    ExecutionSummary,
    MoveOperation,
    SortingPlan,
    execute_operation,
)

FORMAT_VERSION = 1
SERVICE_DIRECTORY = ".file-atelier"
HISTORY_DIRECTORY = "history"


class HistoryError(RuntimeError):
    """Ошибка безопасного создания, чтения или применения журнала."""


@dataclass(frozen=True)
class ApplyResult:
    summary: ExecutionSummary
    history_path: Path | None


@dataclass(frozen=True)
class UndoOperation:
    current: Path
    original: Path
    conflict: str | None


@dataclass(frozen=True)
class UndoPlan:
    source: Path
    history_path: Path
    operation_id: str
    operations: tuple[UndoOperation, ...]

    @property
    def conflicts(self) -> tuple[UndoOperation, ...]:
        return tuple(operation for operation in self.operations if operation.conflict)


@dataclass(frozen=True)
class HistoryInfo:
    operation_id: str
    created_at: str
    moved: int
    status: str


def file_checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def config_checksum(path: Path) -> str:
    try:
        return file_checksum(path)
    except OSError as error:
        raise HistoryError(
            f"Не удалось вычислить контрольную сумму конфигурации: {error}."
        ) from error


def _history_directory(source: Path, create: bool) -> Path:
    source = source.resolve()
    service = source / SERVICE_DIRECTORY
    history = service / HISTORY_DIRECTORY
    if service.is_symlink() or history.is_symlink():
        raise HistoryError("Служебный каталог истории не должен быть символической ссылкой.")
    try:
        history.resolve(strict=False).relative_to(source)
    except ValueError as error:
        raise HistoryError(
            "Служебный каталог истории выходит за пределы исходного каталога."
        ) from error
    if create:
        try:
            history.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            raise HistoryError(f"Не удалось создать каталог истории: {error}.") from error
    return history


def _write_record(path: Path, record: dict[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as file:
            json.dump(record, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    except OSError as error:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise HistoryError(f"Не удалось сохранить журнал {path}: {error}.") from error


def _relative(path: Path, source: Path) -> str:
    return path.resolve(strict=False).relative_to(source).as_posix()


def _missing_directories(directory: Path, source: Path) -> list[str]:
    missing: list[Path] = []
    current = directory
    while current != source and not current.exists():
        missing.append(current)
        current = current.parent
    if current.is_symlink():
        raise HistoryError(f"Каталог назначения является символической ссылкой: {current}.")
    return [_relative(path, source) for path in reversed(missing)]


def _operation_record(operation: MoveOperation, source: Path) -> dict[str, Any]:
    try:
        size = operation.source.stat().st_size
        checksum = file_checksum(operation.source)
    except OSError as error:
        raise HistoryError(f"Не удалось проверить файл {operation.source}: {error}.") from error
    return {
        "source": _relative(operation.source, source),
        "destination": _relative(operation.destination, source),
        "category": operation.category,
        "size": size,
        "sha256": checksum,
        "created_directories": _missing_directories(operation.destination.parent, source),
    }


def _new_record(plan: SortingPlan, checksum: str) -> tuple[Path, dict[str, Any]]:
    history_directory = _history_directory(plan.source, create=True)
    operation_id = uuid4().hex
    now = datetime.now(timezone.utc)
    filename = f"{now.strftime('%Y%m%dT%H%M%S%fZ')}_{operation_id}.json"
    path = history_directory / filename
    record: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "operation_id": operation_id,
        "app_version": __version__,
        "created_at": now.isoformat(),
        "source_root": str(plan.source),
        "config_sha256": checksum,
        "planned_count": len(plan.operations),
        "operations": [],
        "created_directories": [],
        "pending": None,
        "errors": [],
        "status": "in_progress",
    }
    _write_record(path, record)
    return path, record


def _save_failure(record: dict[str, Any], path: Path, message: str) -> None:
    record["pending"] = None
    record["errors"].append(message)
    moved = len(record["operations"])
    record["status"] = "partial" if moved else "failed"
    try:
        _write_record(path, record)
    except HistoryError:
        pass


def apply_plan_with_history(plan: SortingPlan, config_path: Path) -> ApplyResult:
    """Создаёт журнал до первого перемещения и подтверждает в нём каждую успешную операцию."""
    if not plan.operations:
        return ApplyResult(ExecutionSummary(0, 0, plan.skipped, ()), None)

    checksum = config_checksum(config_path)
    path, record = _new_record(plan, checksum)
    moved = 0
    errors: list[str] = []

    for operation in plan.operations:
        operation_data: dict[str, Any] | None = None
        moved_on_disk = False
        try:
            operation_data = _operation_record(operation, plan.source)
            record["pending"] = operation_data
            _write_record(path, record)
            execute_operation(plan.source, operation)
            moved_on_disk = True
            record["operations"].append(operation_data)
            for directory in operation_data["created_directories"]:
                if directory not in record["created_directories"]:
                    record["created_directories"].append(directory)
            record["pending"] = None
            _write_record(path, record)
            moved += 1
        except (HistoryError, OSError) as error:
            message = f"{operation.source} -> {operation.destination}: {error}"
            if moved_on_disk:
                rollback = MoveOperation(
                    operation.destination,
                    operation.source,
                    "Аварийный откат",
                    False,
                )
                try:
                    execute_operation(plan.source, rollback)
                    if operation_data in record["operations"]:
                        record["operations"].remove(operation_data)
                except OSError as rollback_error:
                    message += f"; аварийный откат не выполнен: {rollback_error}"
                    moved += 1
            errors.append(message)
            _save_failure(record, path, message)
            break

    record["pending"] = None
    record["errors"] = errors
    if errors:
        record["status"] = "partial" if moved else "failed"
    else:
        record["status"] = "completed"
    record["finished_at"] = datetime.now(timezone.utc).isoformat()
    _write_record(path, record)
    return ApplyResult(
        ExecutionSummary(len(plan.operations), moved, plan.skipped, tuple(errors)),
        path,
    )


def _latest_history_path(source: Path) -> Path | None:
    directory = _history_directory(source, create=False)
    if not directory.is_dir():
        return None
    files = [path for path in directory.glob("*.json") if path.is_file() and not path.is_symlink()]
    return max(files, key=lambda path: path.name) if files else None


def _read_record(path: Path, source: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise HistoryError("Файл журнала не должен быть символической ссылкой.")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise HistoryError(f"Журнал повреждён или недоступен: {path}: {error}.") from error

    if not isinstance(record, dict) or record.get("format_version") != FORMAT_VERSION:
        raise HistoryError("Журнал имеет неподдерживаемый формат.")
    required = ("operation_id", "created_at", "source_root", "operations", "status")
    if any(key not in record for key in required) or not isinstance(record["operations"], list):
        raise HistoryError("В журнале отсутствуют обязательные поля.")
    try:
        recorded_source = Path(record["source_root"]).resolve()
    except (OSError, TypeError) as error:
        raise HistoryError("В журнале указан некорректный исходный каталог.") from error
    if recorded_source != source.resolve():
        raise HistoryError("Журнал принадлежит другому исходному каталогу.")
    return record


def _path_from_record(source: Path, raw_path: object, label: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise HistoryError(f"В журнале указан некорректный путь {label}.")
    portable = raw_path.replace("\\", "/")
    windows_path = PureWindowsPath(raw_path)
    if PurePosixPath(portable).is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise HistoryError(f"Абсолютный путь {label} в журнале запрещён: {raw_path!r}.")
    parts = portable.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise HistoryError(f"Путь {label} содержит запрещённый компонент: {raw_path!r}.")
    path = source / Path(*parts)
    try:
        path.resolve(strict=False).relative_to(source)
    except ValueError as error:
        raise HistoryError(f"Путь {label} выходит за пределы исходного каталога.") from error
    return path


def _effective_operations(record: dict[str, Any], source: Path) -> list[dict[str, Any]]:
    operations = list(record["operations"])
    pending = record.get("pending")
    if not isinstance(pending, dict):
        return operations

    original = _path_from_record(source, pending.get("source"), "источника")
    current = _path_from_record(source, pending.get("destination"), "назначения")
    if not os.path.lexists(original) and current.is_file() and not current.is_symlink():
        operations.append(pending)
    return operations


def get_latest_history_info(source: Path) -> HistoryInfo | None:
    source = source.resolve()
    path = _latest_history_path(source)
    if path is None:
        return None
    record = _read_record(path, source)
    return HistoryInfo(
        str(record["operation_id"]),
        str(record["created_at"]),
        len(record["operations"]),
        str(record["status"]),
    )


def build_undo_plan(source: Path) -> UndoPlan:
    """Проверяет последний журнал и файловую систему, ничего не изменяя."""
    if source.is_symlink() or not source.exists() or not source.is_dir():
        raise HistoryError(f"Исходный каталог недоступен или является ссылкой: {source}.")
    source = source.resolve()
    path = _latest_history_path(source)
    if path is None:
        raise HistoryError("Для выбранного каталога история операций не найдена.")
    record = _read_record(path, source)
    if record["status"] == "undone":
        raise HistoryError("Последняя операция уже отменена.")

    operation_records = _effective_operations(record, source)
    if not operation_records:
        raise HistoryError("В последнем журнале нет выполненных перемещений.")

    operations: list[UndoOperation] = []
    for operation_record in reversed(operation_records):
        if not isinstance(operation_record, dict):
            raise HistoryError("Журнал содержит некорректную запись операции.")
        original = _path_from_record(source, operation_record.get("source"), "источника")
        current = _path_from_record(source, operation_record.get("destination"), "назначения")
        conflict: str | None = None
        if current.is_symlink():
            conflict = "итоговый путь является символической ссылкой"
        elif not current.exists():
            conflict = "перемещённый файл отсутствует"
        elif not current.is_file():
            conflict = "итоговый путь больше не является обычным файлом"
        else:
            try:
                if current.stat().st_size != operation_record.get("size"):
                    conflict = "размер перемещённого файла изменён"
                elif file_checksum(current) != operation_record.get("sha256"):
                    conflict = "содержимое перемещённого файла изменено"
                elif os.path.lexists(original):
                    conflict = "исходный путь уже занят"
            except OSError as error:
                conflict = f"не удалось проверить перемещённый файл: {error}"
        operations.append(UndoOperation(current, original, conflict))

    return UndoPlan(source, path, str(record["operation_id"]), tuple(operations))


def _remove_empty_created_directories(record: dict[str, Any], source: Path) -> None:
    raw_directories = record.get("created_directories", [])
    if not isinstance(raw_directories, list):
        return
    directories = [_path_from_record(source, raw, "созданного каталога") for raw in raw_directories]
    for directory in sorted(directories, key=lambda path: len(path.parts), reverse=True):
        try:
            directory.rmdir()
        except OSError:
            continue


def execute_undo(plan: UndoPlan) -> ExecutionSummary:
    """Повторно проверяет полный план и отменяет его без перезаписи исходных путей."""
    fresh_plan = build_undo_plan(plan.source)
    if fresh_plan.operation_id != plan.operation_id:
        raise HistoryError("Последняя операция изменилась после построения плана отмены.")
    if fresh_plan.conflicts:
        reasons = "; ".join(
            f"{operation.current}: {operation.conflict}" for operation in fresh_plan.conflicts
        )
        raise HistoryError(f"Отмена заблокирована конфликтами: {reasons}.")

    record = _read_record(fresh_plan.history_path, fresh_plan.source)
    moved = 0
    errors: list[str] = []
    for operation in fresh_plan.operations:
        reverse = MoveOperation(operation.current, operation.original, "Отмена", False)
        try:
            execute_operation(fresh_plan.source, reverse)
            moved += 1
        except OSError as error:
            errors.append(f"{operation.current} -> {operation.original}: {error}")
            break

    if errors:
        record["status"] = "undo_failed"
        record["undo_errors"] = errors
        record["undo_moved_count"] = moved
    else:
        record["status"] = "undone"
        record["undone_at"] = datetime.now(timezone.utc).isoformat()
        record["undo_errors"] = []
        record["undo_moved_count"] = moved
    _write_record(fresh_plan.history_path, record)
    if not errors:
        _remove_empty_created_directories(record, fresh_plan.source)

    return ExecutionSummary(len(fresh_plan.operations), moved, 0, tuple(errors))
