import tkinter as tk


# here will be app class
class OrganiserGui:
    def __init__(self):  # window builder
        self.root = tk.Tk()  # create window
        self.create_widgets()  # create widgets
        self.root.title('Smart-Organiser')
        self.root.geometry('1000x700')

        self.root.mainloop()

    def create_widgets(self):  # here will be all elements
        self.create_frames()
        self.create_buttons()

    def create_frames(self):
        self.select_folder_frame = tk.LabelFrame(
            self.root,
            text='Выбор папки',
            bg='gray',
            width=1000,
            height=250)
        self.select_folder_frame.pack_propagate(False)
        self.select_folder_frame.pack(
            padx=15,
            pady=5,
            fill=tk.X)

        self.settings_frame = tk.LabelFrame(
            self.root,
            text='Настройки',
            bg='gray',
            width=1000,
            height=100)
        self.settings_frame.pack(
            padx=15,
            pady=5,
            fill=tk.X
        )

        self.log_frame = tk.LabelFrame(
            self.root,
            bg='gray',
            text='Лог',
            width=1000,
            height=650)
        self.log_frame.pack(
            padx=15,
            pady=5,
            expand=1,
            fill=tk.BOTH)

    def create_buttons(self):
        self.select_folder_button = tk.Button(self.select_folder_frame, text='Выбрать папку')
        self.select_folder_button.pack()

        self.start_sorting_button = tk.Button(self.root, text='Запустить сортировку')
        self.start_sorting_button.pack()


    def select_folder(self):
        pass

    def start_sorting(self):
        pass


app = OrganiserGui()
