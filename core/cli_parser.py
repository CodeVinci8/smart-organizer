import argparse


def setup_parser() -> argparse.ArgumentParser:
    """РАБОТАЕТ С КОМАНДАМИ

    Функция принимает имена команд, работает с путями, файлами и каталогами.
    """
    parser = argparse.ArgumentParser(
        prog="Smart File Organizer",
        description="Умная автоматизация порядка в ваших папках. "
                    "Мгновенно сортирует файлы по категориям, типам и датам."
    )

    parser.add_argument(
        "-p", "--path",
        type=str,
        required=True,
        help="Путь к папке, которую сортируем."
    )

    parser.add_argument(
        "-c", "--config",
        type=str,
        default="config.json",
        help="Путь к JSON-файлу."
    )

    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Вывод плана действий (предпросмотр)."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Включает подробный вывод."
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        type=str,
        help="Логи для настройки или отладки системы."
    )

    parser.add_argument(
        "-f", "--log-file",
        type=str,
        help = "Путь к файлу, куда нужно сохранять логи."
    )
    return parser

