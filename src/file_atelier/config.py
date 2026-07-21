import json
from pathlib import Path, PurePosixPath, PureWindowsPath


class ConfigError(ValueError):
    """Ошибка чтения или проверки пользовательской конфигурации."""


def _normalize_category(category: object) -> str:
    if not isinstance(category, str) or not category.strip():
        raise ConfigError("Название категории должно быть непустой строкой.")
    if category != category.strip():
        raise ConfigError(
            f"Название категории не должно начинаться или заканчиваться пробелом: {category!r}."
        )

    portable = category.replace("\\", "/")
    windows_path = PureWindowsPath(category)
    if PurePosixPath(portable).is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise ConfigError(f"Абсолютный путь категории запрещён: {category!r}.")

    parts = portable.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise ConfigError(f"Категория содержит запрещённый компонент пути: {category!r}.")
    if any("\x00" in part for part in parts):
        raise ConfigError(f"Категория содержит недопустимый нулевой символ: {category!r}.")

    return "/".join(parts)


def _normalize_extension(extension: object, category: str) -> str:
    if not isinstance(extension, str) or not extension.strip():
        raise ConfigError(f"В категории {category!r} найдено пустое или нестроковое расширение.")

    normalized = extension.strip().lower()
    if not normalized.startswith("."):
        normalized = f".{normalized}"
    if normalized == "." or normalized.count(".") != 1:
        raise ConfigError(f"Некорректное расширение {extension!r} в категории {category!r}.")
    if any(character.isspace() for character in normalized) or any(
        separator in normalized for separator in ("/", "\\", "\x00")
    ):
        raise ConfigError(f"Некорректное расширение {extension!r} в категории {category!r}.")

    return normalized


def validate_config(data: object) -> dict[str, str]:
    """Проверяет простой JSON-формат и возвращает отображение расширений в категории."""
    if not isinstance(data, dict):
        raise ConfigError("Корень JSON-конфигурации должен быть объектом.")

    normalized: dict[str, str] = {}
    for raw_category, extensions in data.items():
        category = _normalize_category(raw_category)
        if not isinstance(extensions, list) or not extensions:
            raise ConfigError(
                f"Категория {category!r} должна содержать непустой список расширений."
            )

        for extension in extensions:
            normalized_extension = _normalize_extension(extension, category)
            previous_category = normalized.get(normalized_extension)
            if previous_category is not None and previous_category != category:
                raise ConfigError(
                    f"Расширение {normalized_extension!r} указано в категориях "
                    f"{previous_category!r} и {category!r}."
                )
            normalized[normalized_extension] = category

    return normalized


def load_config(path: Path) -> dict[str, str]:
    """Читает JSON только после проверки доступности файла и сообщает точное место ошибки."""
    if not path.exists() or not path.is_file():
        raise ConfigError(f"Файл конфигурации не найден: {path}.")

    try:
        with path.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"Повреждён JSON в файле {path}: строка {error.lineno}, столбец {error.colno}."
        ) from error
    except OSError as error:
        raise ConfigError(f"Не удалось прочитать файл конфигурации {path}: {error}.") from error

    return validate_config(data)
