import logging


from pathlib import Path
from core.cli_parser import setup_parser
from core.engine import load_config, organize_files


def configure_logging(level_name, log_file=None):
    """УМНАЯ СИСТЕМА ЛОГИРОВАНИЯ

    Функция принимает уровень логирования и файл (если передан),
    далее создается root логгер, который имеет один форматтер и два хендлера:
    вывод в консоль (всегда) и вывод в файл (если передан).
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level_name))

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S'
                                  )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)

    if log_file is not None:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


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

    configure_logging(level_name, args.log_file)
    logger = logging.getLogger(__name__)

    try:
        source = Path(args.path)
        config_path = Path(args.config)

        config = load_config(config_path)

        if (not source.exists()) or (not source.is_dir()):
            logger.error("Source path does not exist or is not a directory.")
            return

        organize_files(source, config, args.dry_run)
        logger.info("Sorting completed.")

    except FileNotFoundError as err:
        logger.error(err)
        return

    except ValueError as err:
        logger.error(err)
        return


if __name__ == "__main__":
    main()

    