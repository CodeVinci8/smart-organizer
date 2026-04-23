# тут класс для файла
class File:
    def __init__(self, file_name):
        self.file_name = file_name


# класс для списка файлов
class FileManager:
    def __init__(self):
        self.files = []  # композиция список объектов File
