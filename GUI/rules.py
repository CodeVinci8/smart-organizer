from abc import ABC, abstractmethod
import re
from pathlib import Path


class BaseRule(ABC):
    """Базовый класс для всех правил сортировки"""

    def __init__(self, destination: str):
        self.destination = destination  # папка, куда будем перемещать файл

    @abstractmethod
    def match(self, filename: str) -> bool:
        """Проверяет, подходит ли файл под это правило"""
        pass


class ExtensionRule(BaseRule):
    """Правило сортировки по расширению (.jpg, .pdf и т.д.)"""

    def __init__(self, extensions: list, destination: str):
        super().__init__(destination)
        # Приводим все расширения к нижнему регистру и добавляем точку
        self.extensions = []
        for ext in extensions:
            if not ext.startswith('.'):
                ext = '.' + ext
            self.extensions.append(ext.lower())

    def match(self, filename: str) -> bool:
        """Проверяем расширение файла"""
        ext = Path(filename).suffix.lower()
        return ext in self.extensions


class RegexRule(BaseRule):
    """Правило сортировки по регулярному выражению"""

    def __init__(self, pattern: str, destination: str):
        super().__init__(destination)
        self.pattern = re.compile(pattern, re.IGNORECASE)  # компилируем регулярку

    def match(self, filename: str) -> bool:
        """Проверяем совпадение по регулярному выражению"""
        return bool(self.pattern.search(filename))

