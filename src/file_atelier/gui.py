import sys
from collections.abc import Sequence

from file_atelier import __version__
from file_atelier.cli import RussianArgumentParser


def build_parser() -> RussianArgumentParser:
    parser = RussianArgumentParser(
        prog="file-atelier-gui",
        description="Запускает графический интерфейс File Atelier.",
        add_help=False,
    )
    parser._optionals.title = "параметры"
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Показать эту справку и завершить работу.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Показать версию и завершить работу.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    try:
        from file_atelier.desktop import DesktopLaunchError, run_app

        run_app()
    except DesktopLaunchError as error:
        print(f"Ошибка запуска интерфейса: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
