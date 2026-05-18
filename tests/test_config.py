import json
import pytest

from core.engine import load_config


def test_load_valid_config(tmp_path):
    data = {
        "Images": [".jpg", "png"],
        "Documents": [".pdf"]
    }

    config_path = tmp_path / "config.json"
    json_data = json.dumps(data)
    config_path.write_text(json_data, encoding="utf-8")

    result = load_config(config_path)

    assert result[".jpg"] == "Images"
    assert result[".png"] == "Images"
    assert result[".pdf"] == "Documents"


def test_load_missing_file(tmp_path):
    missing_path = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        load_config(missing_path)


def test_load_invalid_json(tmp_path):
    invalid_json_path = tmp_path / "invalid.json"
    invalid_json_path.write_text("{bad json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(invalid_json_path)

