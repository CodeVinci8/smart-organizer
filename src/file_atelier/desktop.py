import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from file_atelier import __version__
from file_atelier.engine import ExecutionSummary, SortingPlan
from file_atelier.gui_state import GuiSession, GuiStateError


class DesktopLaunchError(RuntimeError):
    """Ошибка создания системного окна приложения."""


class FileAtelierApp:
    BACKGROUND = "#F5F3EE"
    SURFACE = "#FFFFFF"
    NAVY = "#17324D"
    MUTED = "#607284"
    TEAL = "#168C82"
    TEAL_DARK = "#0F6F68"
    TERRACOTTA = "#B85F43"
    BORDER = "#D9DED9"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.session = GuiSession()
        self.busy = False

        self.source_var = tk.StringVar()
        default_config = Path.cwd() / "config.json"
        self.config_var = tk.StringVar(
            value=str(default_config) if default_config.is_file() else ""
        )
        self.recursive_var = tk.BooleanVar(value=False)
        self.error_var = tk.StringVar(value="Ошибок нет.")
        self.summary_var = tk.StringVar(value="Постройте предпросмотр, чтобы увидеть операции.")
        self.planned_var = tk.StringVar(value="Запланировано: 0")
        self.skipped_var = tk.StringVar(value="Пропущено: 0")
        self.conflicts_var = tk.StringVar(value="Конфликты: 0")

        self._configure_window()
        self._configure_styles()
        self._build_layout()
        self._bind_inputs()
        self._sync_inputs()
        self.source_entry.focus_set()

    def _configure_window(self) -> None:
        self.root.title(f"File Atelier {__version__}")
        self.root.geometry("1120x760")
        self.root.minsize(940, 680)
        self.root.configure(background=self.BACKGROUND)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("App.TFrame", background=self.BACKGROUND)
        style.configure("Card.TFrame", background=self.SURFACE)
        style.configure(
            "Title.TLabel",
            background=self.BACKGROUND,
            foreground=self.NAVY,
            font=("Segoe UI Semibold", 24),
        )
        style.configure(
            "Subtitle.TLabel",
            background=self.BACKGROUND,
            foreground=self.MUTED,
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background=self.SURFACE,
            foreground=self.NAVY,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "Card.TLabel",
            background=self.SURFACE,
            foreground=self.NAVY,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Counter.TLabel",
            background=self.SURFACE,
            foreground=self.NAVY,
            font=("Segoe UI Semibold", 9),
        )
        style.configure(
            "Error.TLabel",
            background="#FFF4EF",
            foreground=self.TERRACOTTA,
            font=("Segoe UI", 9),
            padding=10,
        )
        style.configure(
            "Primary.TButton",
            background=self.TEAL,
            foreground="#FFFFFF",
            bordercolor=self.TEAL,
            focusthickness=3,
            focuscolor=self.NAVY,
            padding=(14, 9),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.TEAL_DARK), ("disabled", "#A8C6C1")],
        )
        style.configure(
            "Secondary.TButton",
            background="#E6F0EE",
            foreground=self.NAVY,
            bordercolor="#AFCBC7",
            focusthickness=3,
            focuscolor=self.NAVY,
            padding=(12, 8),
            font=("Segoe UI", 9),
        )
        style.map("Secondary.TButton", background=[("active", "#D4E7E3")])
        style.configure(
            "Treeview",
            background=self.SURFACE,
            fieldbackground=self.SURFACE,
            foreground=self.NAVY,
            rowheight=28,
            bordercolor=self.BORDER,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background="#E9EFEE",
            foreground=self.NAVY,
            font=("Segoe UI Semibold", 9),
            padding=(8, 7),
        )
        style.map("Treeview", background=[("selected", self.TEAL)])

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame", padding=(28, 22, 28, 22))
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        header = ttk.Frame(container, style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        ttk.Label(header, text="File Atelier", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Безопасная сортировка файлов с обязательным предпросмотром.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(3, 0))

        settings = ttk.Frame(container, style="Card.TFrame", padding=18)
        settings.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        settings.columnconfigure(1, weight=1)
        ttk.Label(settings, text="Параметры сортировки", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 12)
        )

        ttk.Label(settings, text="Исходный каталог", style="Card.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=5
        )
        self.source_entry = ttk.Entry(settings, textvariable=self.source_var, takefocus=True)
        self.source_entry.grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Button(
            settings,
            text="Выбрать…",
            command=self._choose_source,
            style="Secondary.TButton",
            takefocus=True,
        ).grid(row=1, column=2, padx=(10, 0), pady=5)

        ttk.Label(settings, text="JSON-конфигурация", style="Card.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 12), pady=5
        )
        ttk.Entry(settings, textvariable=self.config_var, takefocus=True).grid(
            row=2, column=1, sticky="ew", pady=5
        )
        ttk.Button(
            settings,
            text="Выбрать…",
            command=self._choose_config,
            style="Secondary.TButton",
            takefocus=True,
        ).grid(row=2, column=2, padx=(10, 0), pady=5)

        action_row = ttk.Frame(settings, style="Card.TFrame")
        action_row.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Checkbutton(
            action_row,
            text="Обрабатывать вложенные каталоги",
            variable=self.recursive_var,
            takefocus=True,
        ).pack(side="left")
        self.refresh_button = ttk.Button(
            action_row,
            text="Обновить план",
            command=self._preview,
            style="Secondary.TButton",
            takefocus=True,
        )
        self.refresh_button.pack(side="right")
        self.preview_button = ttk.Button(
            action_row,
            text="Построить предпросмотр",
            command=self._preview,
            style="Primary.TButton",
            takefocus=True,
        )
        self.preview_button.pack(side="right", padx=(0, 8))

        plan_card = ttk.Frame(container, style="Card.TFrame", padding=18)
        plan_card.grid(row=2, column=0, sticky="nsew")
        plan_card.columnconfigure(0, weight=1)
        plan_card.rowconfigure(2, weight=1)

        plan_header = ttk.Frame(plan_card, style="Card.TFrame")
        plan_header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(plan_header, text="План операций", style="CardTitle.TLabel").pack(side="left")
        ttk.Label(plan_header, textvariable=self.conflicts_var, style="Counter.TLabel").pack(
            side="right", padx=(16, 0)
        )
        ttk.Label(plan_header, textvariable=self.skipped_var, style="Counter.TLabel").pack(
            side="right", padx=(16, 0)
        )
        ttk.Label(plan_header, textvariable=self.planned_var, style="Counter.TLabel").pack(
            side="right"
        )

        columns = ("file", "category", "destination", "status")
        self.tree = ttk.Treeview(plan_card, columns=columns, show="headings", takefocus=True)
        self.tree.heading("file", text="Файл")
        self.tree.heading("category", text="Категория")
        self.tree.heading("destination", text="Куда будет перемещён")
        self.tree.heading("status", text="Статус")
        self.tree.column("file", width=190, minwidth=130)
        self.tree.column("category", width=145, minwidth=110)
        self.tree.column("destination", width=420, minwidth=240)
        self.tree.column("status", width=160, minwidth=130)
        self.tree.tag_configure("conflict", foreground=self.TERRACOTTA)

        scrollbar = ttk.Scrollbar(plan_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        scrollbar.grid(row=2, column=1, sticky="ns")

        footer = ttk.Frame(plan_card, style="Card.TFrame")
        footer.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(
            footer,
            textvariable=self.summary_var,
            style="Card.TLabel",
            wraplength=720,
        ).grid(row=0, column=0, sticky="w", padx=(0, 14))
        self.apply_button = ttk.Button(
            footer,
            text="Применить план",
            command=self._apply,
            style="Primary.TButton",
            state="disabled",
            takefocus=True,
        )
        self.apply_button.grid(row=0, column=1, sticky="e")

        ttk.Label(
            container, textvariable=self.error_var, style="Error.TLabel", wraplength=1040
        ).grid(row=3, column=0, sticky="ew", pady=(12, 0))

    def _bind_inputs(self) -> None:
        self.source_var.trace_add("write", self._inputs_changed)
        self.config_var.trace_add("write", self._inputs_changed)
        self.recursive_var.trace_add("write", self._inputs_changed)

    def _sync_inputs(self) -> None:
        self.session.update_inputs(
            self.source_var.get(),
            self.config_var.get(),
            self.recursive_var.get(),
        )

    def _inputs_changed(self, *_args: object) -> None:
        had_plan = self.session.plan is not None
        self._sync_inputs()
        if had_plan and self.session.plan is None:
            self.apply_button.configure(state="disabled")
            self.summary_var.set("Параметры изменены. Обновите план перед применением.")

    def _choose_source(self) -> None:
        selected = filedialog.askdirectory(title="Выберите каталог для сортировки")
        if selected:
            self.source_var.set(selected)

    def _choose_config(self) -> None:
        selected = filedialog.askopenfilename(
            title="Выберите JSON-конфигурацию",
            filetypes=(("JSON-файлы", "*.json"), ("Все файлы", "*.*")),
        )
        if selected:
            self.config_var.set(selected)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.root.configure(cursor="watch" if busy else "")
        self.preview_button.configure(state="disabled" if busy else "normal")
        self.refresh_button.configure(state="disabled" if busy else "normal")
        if busy or not self.session.can_apply:
            self.apply_button.configure(state="disabled")
        else:
            self.apply_button.configure(state="normal")
        self.root.update_idletasks()

    def _clear_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _preview(self) -> None:
        if self.busy:
            return
        self._sync_inputs()
        self._set_busy(True)
        self.error_var.set("Ошибок нет.")
        try:
            plan = self.session.build()
            self._render_plan(plan)
        except (GuiStateError, ValueError, OSError) as error:
            self._clear_table()
            self.error_var.set(f"Ошибка: {error}")
            self.summary_var.set("План не построен. Исправьте параметры и повторите попытку.")
            self.planned_var.set("Запланировано: 0")
            self.skipped_var.set("Пропущено: 0")
            self.conflicts_var.set("Конфликты: 0")
        finally:
            self._set_busy(False)

    def _render_plan(self, plan: SortingPlan) -> None:
        self._clear_table()
        conflict_count = 0
        for index, operation in enumerate(plan.operations):
            if operation.conflict:
                conflict_count += 1
            destination = operation.destination.relative_to(plan.source)
            status = "Будет переименован" if operation.conflict else "Готово"
            tags = ("conflict",) if operation.conflict else ()
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                values=(operation.source.name, operation.category, destination, status),
                tags=tags,
            )

        self.planned_var.set(f"Запланировано: {len(plan.operations)}")
        self.skipped_var.set(f"Пропущено: {plan.skipped}")
        self.conflicts_var.set(f"Конфликты: {conflict_count}")
        if plan.operations:
            self.summary_var.set("Предпросмотр готов. Проверьте назначения перед применением.")
        else:
            self.summary_var.set(
                "Перемещать нечего: каталог уже упорядочен или не содержит файлов."
            )
        self.apply_button.configure(state="normal" if self.session.can_apply else "disabled")

    def _apply(self) -> None:
        if self.busy or not self.session.can_apply or self.session.plan is None:
            self.error_var.set("Ошибка: сначала постройте актуальный непустой план.")
            return

        plan = self.session.plan
        confirmation_text = (
            f"Переместить файлов: {len(plan.operations)}?\n\n"
            "Существующие файлы не будут перезаписаны."
        )
        confirmed = messagebox.askyesno(
            "Подтверждение перемещения",
            confirmation_text,
            parent=self.root,
        )
        if not confirmed:
            return

        self._set_busy(True)
        self.summary_var.set("Выполняется сортировка. Повторный запуск временно заблокирован…")
        self.error_var.set("Ошибок нет.")
        try:
            summary = self.session.apply()
            self._render_execution(plan, summary)
        except (GuiStateError, ValueError, OSError) as error:
            self.error_var.set(f"Ошибка: {error}")
            self.summary_var.set("Сортировка не завершена.")
        finally:
            self._set_busy(False)

    def _render_execution(self, plan: SortingPlan, summary: ExecutionSummary) -> None:
        for index, operation in enumerate(plan.operations):
            failed = any(error.startswith(f"{operation.source} ->") for error in summary.errors)
            self.tree.set(str(index), "status", "Ошибка" if failed else "Перемещён")

        if summary.errors:
            self.error_var.set("Ошибки операций:\n" + "\n".join(summary.errors))
        else:
            self.error_var.set("Ошибок нет.")
        self.summary_var.set(
            f"Готово: запланировано {summary.planned}, перемещено {summary.moved}, "
            f"пропущено {summary.skipped}, ошибок {len(summary.errors)}."
        )
        self.apply_button.configure(state="disabled")


def run_app() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as error:
        raise DesktopLaunchError(str(error)) from error
    FileAtelierApp(root)
    root.mainloop()
