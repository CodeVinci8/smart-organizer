import json
import subprocess
import sys

import pytest
import tomllib

from file_atelier.config import ConfigError
from file_atelier.engine import ExecutionSummary
from file_atelier.gui_state import GuiSession, GuiStateError


def _write_config(path):
    path.write_text(json.dumps({"Документы": [".txt"]}), encoding="utf-8")


def test_gui_session_uses_core_and_invalidates_plan(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.txt").write_text("текст", encoding="utf-8")
    config = tmp_path / "config.json"
    _write_config(config)
    session = GuiSession()

    session.update_inputs(str(source), str(config), False)
    plan = session.build()

    assert len(plan.operations) == 1
    assert plan.operations[0].category == "Документы"
    assert session.can_apply

    session.update_inputs(str(source), str(config), True)

    assert session.plan is None
    assert not session.can_apply


def test_gui_cannot_apply_without_current_plan():
    with pytest.raises(GuiStateError, match="актуальный непустой план"):
        GuiSession().apply()


def test_gui_propagates_config_error(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    config = tmp_path / "config.json"
    config.write_text("{bad", encoding="utf-8")
    session = GuiSession(str(source), str(config))

    with pytest.raises(ConfigError, match="Повреждён JSON"):
        session.build()


def test_gui_apply_uses_shared_execution_engine(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.txt").write_text("текст", encoding="utf-8")
    config = tmp_path / "config.json"
    _write_config(config)
    session = GuiSession(str(source), str(config))
    session.build()

    summary = session.apply()

    assert summary == ExecutionSummary(1, 1, 0, ())
    assert (source / "Документы" / "notes.txt").exists()
    assert not session.can_apply


def test_launch_commands_are_configured_and_cli_import_is_independent():
    project = tomllib.loads(open("pyproject.toml", encoding="utf-8").read())

    assert project["project"]["scripts"]["file-atelier"] == "file_atelier.cli:main"
    assert project["project"]["scripts"]["file-atelier-gui"] == "file_atelier.gui:main"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import file_atelier.cli; assert 'tkinter' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
