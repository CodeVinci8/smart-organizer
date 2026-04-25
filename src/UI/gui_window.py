from tkinter import *

root = Tk()
root.geometry("800x600")
root.overrideredirect(True)
root['bg'] = '#CCB178'

# шапка
header = Frame(root, bg="black", height=30)
header.pack(fill="x")

Label(header, text="Smart Organizer", bg="black", fg="white").pack(side="left", padx=10)


# --- функции ---
def close():
    root.destroy()


def minimize():
    root.overrideredirect(False)
    root.iconify()


is_maximized = False


def toggle_maximize():
    global is_maximized

    if not is_maximized:
        root.state("zoomed")
        is_maximized = True
    else:
        root.state("normal")
        root.geometry("800x600")
        is_maximized = False


# --- кнопки ---
Button(header, text="—", command=minimize).pack(side="right")
Button(header, text="⬜", command=toggle_maximize).pack(side="right")
Button(header, text="X", bg="red", command=close).pack(side="right")


# движение окна
def start_move(event):
    root.x = event.x
    root.y = event.y


def move_window(event):
    x = event.x_root - root.x
    y = event.y_root - root.y
    root.geometry(f"+{x}+{y}")


header.bind("<Button-1>", start_move)
header.bind("<B1-Motion>", move_window)

root.mainloop()