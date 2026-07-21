from dataclasses import dataclass, field
from pathlib import Path

from file_atelier.config import load_config
from file_atelier.engine import ExecutionSummary, SortingPlan, build_plan
from file_atelier.history import (
    HistoryInfo,
    UndoPlan,
    apply_plan_with_history,
    build_undo_plan,
    execute_undo,
    get_latest_history_info,
)


class GuiStateError(RuntimeError):
    """Ошибка состояния, при котором действие GUI было бы небезопасным."""


@dataclass
class GuiSession:
    source_text: str = ""
    config_text: str = ""
    recursive: bool = False
    plan: SortingPlan | None = None
    undo_plan: UndoPlan | None = None
    _plan_signature: tuple[str, str, bool] | None = field(default=None, init=False, repr=False)

    def _signature(self) -> tuple[str, str, bool]:
        return (self.source_text.strip(), self.config_text.strip(), self.recursive)

    @property
    def is_plan_current(self) -> bool:
        return self.plan is not None and self._plan_signature == self._signature()

    @property
    def can_apply(self) -> bool:
        return self.is_plan_current and bool(self.plan and self.plan.operations)

    def update_inputs(self, source_text: str, config_text: str, recursive: bool) -> None:
        new_signature = (source_text.strip(), config_text.strip(), recursive)
        if new_signature != self._signature():
            self.plan = None
            self.undo_plan = None
            self._plan_signature = None
        self.source_text, self.config_text, self.recursive = new_signature

    def build(self) -> SortingPlan:
        if not self.source_text:
            raise GuiStateError("Выберите исходный каталог.")
        if not self.config_text:
            raise GuiStateError("Выберите JSON-конфигурацию.")

        config = load_config(Path(self.config_text))
        plan = build_plan(Path(self.source_text), config, recursive=self.recursive)
        self.plan = plan
        self._plan_signature = self._signature()
        return plan

    def apply(self) -> ExecutionSummary:
        if not self.can_apply or self.plan is None:
            raise GuiStateError("Сначала постройте актуальный непустой план.")

        result = apply_plan_with_history(self.plan, Path(self.config_text))
        self.plan = None
        self._plan_signature = None
        return result.summary

    def history_info(self) -> HistoryInfo | None:
        if not self.source_text:
            return None
        return get_latest_history_info(Path(self.source_text))

    def build_undo(self) -> UndoPlan:
        if not self.source_text:
            raise GuiStateError("Выберите исходный каталог.")
        self.undo_plan = build_undo_plan(Path(self.source_text))
        return self.undo_plan

    @property
    def can_undo(self) -> bool:
        return bool(self.undo_plan and self.undo_plan.operations and not self.undo_plan.conflicts)

    def undo(self) -> ExecutionSummary:
        if not self.can_undo or self.undo_plan is None:
            raise GuiStateError("Сначала постройте безопасный план отмены без конфликтов.")
        summary = execute_undo(self.undo_plan)
        self.undo_plan = None
        return summary
