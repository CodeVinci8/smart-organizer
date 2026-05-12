import re
# from typing import List, Dict, Optional
from rules import BaseRule, RegexRule, ExtensionRule
# тут будет распределитель правил и их применение


class EngineRules:
    def __init__(self):
        self.rules = []  # тут будет храниться правила сортировки

    def add_rule(self, rule):
        #   метод для добавления правила сортировки
        self.rules.append(rule)

    def get_destination(self, filename):
        # через имя файла получу нахождение того, для чего применю правило
        """Возвращает папку назначения для файла или None, если правило не найдено"""
        for rule in self.rules:
            if rule.match(filename):
                return rule.destination
            return None  # файл не подходит ни под одно правило

    def load_from_config(self, config):
        """Загружает правила из конфигурационного файла (пока заглушка)"""
        pass



