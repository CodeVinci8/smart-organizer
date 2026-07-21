from dataclasses import dataclass, field
from pathlib import Path

from file_atelier.config import load_config
from file_atelier.engine import ExecutionSummary, SortingPlan, build_plan, execute_plan


class GuiStateError(RuntimeError):
    """Ошибка состояния, при котором действие GUI было бы небезопасным."""


@dataclass
class GuiSession:
    source_text: str = ""
    config_text: str = ""
    recursive: bool = False
    plan: SortingPlan | None = None
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

        summary = execute_plan(self.plan)
        self.plan = None
        self._plan_signature = None
        return summary
