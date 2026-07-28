from pathlib import Path

import pytest

from pfemt.config import load_yaml, validate_study_config
from pfemt.errors import ConfigurationError


def test_base_study_configuration_is_valid() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/01_line_energization/configs/base.yaml")
    validate_study_config(config)


def test_stop_time_must_follow_start_time(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text(
        """
study: {id: test}
powerfactory: {project: p, study_case: c}
simulation: {start_s: 1.0, stop_s: 0.0, step_s: 0.001}
outputs: {directory: out}
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="stop_s"):
        validate_study_config(load_yaml(path))

