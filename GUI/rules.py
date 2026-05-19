from abc import ABC, abstractmethod
from typing import List
import re


# класс базовое правило, получает нахождение файла
class BaseRule(ABC):
    destination: str  # у каждого класса будет такой атрибут

    def __init__(self, destination: str):  # параметр классов
        self.destination = destination

    @abstractmethod
    def if_match(self, filename: str):
        pass


# класс работает с расширениями
class ExtensionRule(BaseRule):
    def __init__(self, extensions: List[str], destination: str):
        super().__init__(destination)
        self. extensions: List[str] = [ext.lower() for ext in extensions]

    def if_match(self, filename: str) -> bool:
        if not filename:
            return False

        match = re.search(r'\.([^\.]+)$', filename)  # поиск расширения в конце строки
        if not match:
            return False

        file_ext = match.group(0).lower()
        return file_ext in self.extensions


# класс работает с регулярными выражениями, а именно с именами файлов
class RegexRule(BaseRule):
    def __init__(self, names: List[str], destination: str, patern: str):
        super().__init__(destination)
        self.patern = patern
        self.names: List[str] = [n.lower() for n in names]  # список имен

    def if_match(self, filename: str) -> bool:
        if not filename:
            return False

        match = re.search(self.patern, filename)
        # тут можно жестко самому прописать правило, а можно чисто патерн принимающий правила

        if not match:
            return False

        name = match.group(0).lower()
        return name in self.names


# делаю менеджер задач, он же класс контейнер
class RulesEngine:
    def __init__(self):
        self.rules: List[BaseRule] = []

    def add_rule(self, rule: BaseRule):
        self.rules.append(rule)

    def add_rules(self, rule: List[BaseRule]):
        self.rules.extend(rule)

