import logging


from pathlib import Path
from core.cli_parser import setup_parser
from core.engine import load_config, organize_files


def main():
    """ЗАПУСК ПРОГРАММЫ

    Создаёт парсер команд, далее читает команды пользователя, папка которую передал пользователь
    преобразуется в объект Path (то же самое с config) и начинает сортировку.
    * Смотрит установлен ли "подробный режим" или уровень логирования, принимает значения и логирует запросы.
    """
    parser = setup_parser()
    args = parser.parse_args()

    if args.log_level:
        level_name = args.log_level
    elif args.verbose:
        level_name = "INFO"
    else:
        level_name = "WARNING"

    logging.basicConfig(level=getattr(logging, level_name))
    logger = logging.getLogger(__name__)

    try:
        source = Path(args.path)
        config_path = Path(args.config)

        config = load_config(config_path)

        if (not source.exists()) or (not source.is_dir()):
            logger.error("Путь не существует, или переданный путь не является директорией.")
            return

        organize_files(source, config, args.dry_run)


        logger.info("Сортировка завершена.")

    except FileNotFoundError as err:
        logger.error(err)
        return

    except ValueError as err:
        logger.error(err)
        return


if __name__ == "__main__":
    main()

    