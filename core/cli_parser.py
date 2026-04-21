import argparse


def setup_parser():
    parser = argparse.ArgumentParser(description="Smart File Organizer.")

    parser.add_argument(
        "--path",
        required=True,
        type = str,
        help="Путь к папке, которую сортируем."
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Путь к JSON-файлу."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Вывод плана действий."
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Включает подробный вывод."
    )

    return parser


if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    print(args)