from pathlib import Path

from pfemt.config import load_yaml
from pfemt.diagram import plot_line_energization_diagram


def test_one_line_diagram_is_generated(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/01_line_energization/configs/base.yaml")
    output = plot_line_energization_diagram(config, tmp_path / "diagram.png")
    assert output.is_file()
    assert output.stat().st_size > 10_000

