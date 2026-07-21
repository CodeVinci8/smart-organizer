import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from file_atelier import __version__
from file_atelier.config import ConfigError, load_config
from file_atelier.engine import ExecutionSummary, SortingPlan, build_plan
from file_atelier.history import (
    HistoryError,
    UndoPlan,
    apply_plan_with_history,
    build_undo_plan,
    execute_undo,
)


class RussianArgumentParser(argparse.ArgumentParser):
    def format_help(self) -> str:
        return super().format_help().replace("usage:", "использование:", 1)

    def format_usage(self) -> str:
        return super().format_usage().replace("usage:", "использование:", 1)

    def error(self, message: str) -> None:
        translations = (
            ("the following arguments are required:", "не указаны обязательные параметры:"),
            ("unrecognized arguments:", "неизвестные параметры:"),
            ("not allowed with argument", "нельзя использовать вместе с параметром"),
            ("invalid choice:", "недопустимое значение:"),
            ("choose from", "доступные значения"),
            ("expected one argument", "требуется значение"),
            ("argument", "параметр"),
        )
        for original, translated in translations:
            message = message.replace(original, translated)
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: ошибка: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    parser = RussianArgumentParser(
        prog="file-atelier",
        description="Безопасно сортирует файлы по расширениям и правилам из JSON-конфигурации.",
        add_help=False,
    )
    parser._optionals.title = "параметры"
    parser.add_argument(
        "-h", "--help", action="help", help="Показать эту справку и завершить работу."
    )
    parser.add_argument(
        "source",
        nargs="?",
        metavar="КАТАЛОГ",
        help="Исходный каталог; нужен для краткой формы команды отмены.",
    )
    parser.add_argument(
        "-p",
        "--path",
        metavar="КАТАЛОГ",
        help="Каталог, файлы в котором нужно отсортировать.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config.json",
        metavar="ФАЙЛ",
        help="Путь к JSON-конфигурации (по умолчанию: config.json).",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Применить показанный план и переместить файлы.",
    )
    mode.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Явно выбрать предпросмотр без изменений (это режим по умолчанию).",
    )

    parser.add_argument(
        "--undo-last",
        action="store_true",
        help="Построить план отмены последней сортировки выбранного каталога.",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Обрабатывать также файлы во вложенных каталогах.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Включить подробные сообщения журнала.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Явно задать уровень журналирования.",
    )
    parser.add_argument(
        "-f",
        "--log-file",
        metavar="ФАЙЛ",
        help="Дополнительно записывать журнал в указанный файл.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Показать версию и завершить работу.",
    )
    return parser


def configure_logging(level_name: str, log_file: str | None = None) -> None:
    """Заменяет только обработчики File Atelier, чтобы повторный вызов не дублировал записи."""
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        if getattr(handler, "_file_atelier_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    root_logger.setLevel(getattr(logging, level_name))
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    setattr(console_handler, "_file_atelier_handler", True)
    root_logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        setattr(file_handler, "_file_atelier_handler", True)
        root_logger.addHandler(file_handler)


def _display_path(path: Path, source: Path) -> str:
    try:
        return str(path.relative_to(source))
    except ValueError:
        return str(path)


def _print_plan(plan: SortingPlan, apply: bool) -> None:
    mode = "применение" if apply else "предпросмотр; файлы не изменяются"
    print(f"Режим: {mode}.")
    if not plan.operations:
        print("Операций для выполнения нет.")
        return

    print("План операций:")
    for operation in plan.operations:
        source = _display_path(operation.source, plan.source)
        destination = _display_path(operation.destination, plan.source)
        print(f"  {source} -> {destination}")


def _print_summary(summary: ExecutionSummary) -> None:
    print(
        "Сводка: "
        f"запланировано: {summary.planned}; "
        f"перемещено: {summary.moved}; "
        f"пропущено: {summary.skipped}; "
        f"ошибки: {len(summary.errors)}."
    )


def _print_undo_plan(plan: UndoPlan, apply: bool) -> None:
    mode = "применение отмены" if apply else "предпросмотр отмены; файлы не изменяются"
    print(f"Режим: {mode}.")
    print(f"Операция: {plan.operation_id}.")
    print("План обратных перемещений:")
    for operation in plan.operations:
        current = _display_path(operation.current, plan.source)
        original = _display_path(operation.original, plan.source)
        status = f"конфликт: {operation.conflict}" if operation.conflict else "готово"
        print(f"  {current} -> {original} [{status}]")


def _resolve_source(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Path:
    if args.path and args.source:
        parser.error("параметр --path и позиционный КАТАЛОГ нельзя использовать вместе")
    raw_source = args.path or args.source
    if not raw_source:
        parser.error("не указан исходный КАТАЛОГ или параметр --path")
    return Path(raw_source)


def _run_undo(source: Path, apply: bool, logger: logging.Logger) -> int:
    try:
        plan = build_undo_plan(source)
    except HistoryError as error:
        logger.error("Ошибка истории: %s", error)
        return 1

    _print_undo_plan(plan, apply)
    conflict_errors = tuple(
        f"{operation.current}: {operation.conflict}" for operation in plan.conflicts
    )
    if not apply:
        summary = ExecutionSummary(
            len(plan.operations),
            0,
            len(plan.conflicts),
            conflict_errors,
        )
        _print_summary(summary)
        if plan.conflicts:
            print("Отмена заблокирована: устраните перечисленные конфликты.")
        else:
            print("Для выполнения отмены повторите команду с параметром --apply.")
        return 0

    if plan.conflicts:
        for operation in plan.conflicts:
            logger.error("Конфликт отмены: %s: %s", operation.current, operation.conflict)
        _print_summary(
            ExecutionSummary(
                len(plan.operations),
                0,
                len(plan.conflicts),
                conflict_errors,
            )
        )
        return 1

    try:
        summary = execute_undo(plan)
    except HistoryError as error:
        logger.error("Ошибка отмены: %s", error)
        return 1
    for error in summary.errors:
        logger.error("Ошибка обратного перемещения: %s", error)
    _print_summary(summary)
    return 1 if summary.errors else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    source = _resolve_source(parser, args)
    if args.undo_last and args.recursive:
        parser.error("параметр --recursive не используется вместе с --undo-last")
    level_name = args.log_level or ("INFO" if args.verbose else "WARNING")
    try:
        configure_logging(level_name, args.log_file)
    except OSError as error:
        print(f"Ошибка настройки журнала: {error}", file=sys.stderr)
        return 1
    logger = logging.getLogger(__name__)

    if args.undo_last:
        return _run_undo(source, args.apply, logger)

    try:
        config = load_config(Path(args.config))
        logger.info("Конфигурация загружена: %s.", args.config)
        plan = build_plan(source, config, recursive=args.recursive)
        logger.info(
            "План подготовлен: %d операций, пропущено: %d.",
            len(plan.operations),
            plan.skipped,
        )
    except (ConfigError, ValueError, OSError) as error:
        logger.error("Ошибка: %s", error)
        return 1

    _print_plan(plan, args.apply)
    if not args.apply:
        summary = ExecutionSummary(len(plan.operations), 0, plan.skipped, ())
        _print_summary(summary)
        if plan.operations:
            print("Для перемещения файлов повторите команду с параметром --apply.")
        return 0

    try:
        result = apply_plan_with_history(plan, Path(args.config))
    except HistoryError as error:
        logger.error("Ошибка истории: %s", error)
        return 1
    summary = result.summary
    logger.info("Выполнение плана завершено: перемещено %d.", summary.moved)
    if result.history_path is not None:
        print(f"Журнал операции: {result.history_path}")
    for error in summary.errors:
        logger.error("Ошибка перемещения: %s", error)
    _print_summary(summary)
    return 1 if summary.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
