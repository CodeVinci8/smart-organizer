from pathlib import Path
from core.cli_parser import setup_parser
from core.engine import load_config, organize_files


def main():
    """ЗАПУСК ПРОГРАММЫ

    Создаёт парсер команд, далее читает команды пользователя, папка которую передал пользователь
    преобразуется в объект Path (то же самое с config) и начинает сортировку.
    """
    parser = setup_parser()
    args = parser.parse_args()

    source = Path(args.path)
    config_path = Path(args.config)

    config = load_config(config_path)

    organize_files(source, config, args.dry_run)


if __name__ == "__main__":
    main()