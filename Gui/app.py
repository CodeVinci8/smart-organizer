from tkinter import Tk


class OrganizerGui:
    def __init__(self):
        self.root = Tk()
        self.root.title("Smart-Organiser")
        self.root.geometry("1250x1080")
        self.root.resizable(False, False)

        self.source_path: str = ''  # тут я буду получать путь к файлу
        self.create_widgets()

    def create_widgets(self):
        pass

    def select_folder(self):
        pass

    def start_sorting(self):
        pass
