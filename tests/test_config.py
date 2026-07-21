import json

import pytest

from file_atelier.config import ConfigError, load_config, validate_config


def test_load_valid_config_normalizes_extensions(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"Изображения": ["JPG", ".PNG"], "Документы": ["pdf"]}),
        encoding="utf-8",
    )

    assert load_config(config_path) == {
        ".jpg": "Изображения",
        ".png": "Изображения",
        ".pdf": "Документы",
    }


def test_load_config_reports_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="не найден"):
        load_config(tmp_path / "missing.json")


def test_load_config_reports_damaged_json(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(ConfigError, match="Повреждён JSON"):
        load_config(config_path)


@pytest.mark.parametrize("category", ["", ".", "..", "../снаружи", "/tmp/снаружи", "C:\\снаружи"])
def test_rejects_forbidden_category(category):
    with pytest.raises(ConfigError):
        validate_config({category: [".txt"]})


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"Документы": []},
        {"Документы": ".txt"},
        {"Документы": [""]},
        {"Документы": [1]},
    ],
)
def test_rejects_invalid_config_shape(data):
    with pytest.raises(ConfigError):
        validate_config(data)


def test_rejects_extension_assigned_to_different_categories():
    with pytest.raises(ConfigError, match="указано в категориях"):
        validate_config({"Тексты": ["TXT"], "Документы": [".txt"]})
