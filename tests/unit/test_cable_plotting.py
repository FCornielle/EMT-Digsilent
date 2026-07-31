from pathlib import Path

from pfemt.cable_plotting import generate_cable_design_figures
from pfemt.config import load_yaml


def test_cable_design_figures_are_generated(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_yaml(root / "studies/02_hv_cable_energization/configs/base.yaml")
    figures = generate_cable_design_figures(config, tmp_path)
    assert set(figures) == {
        "parameters",
        "length_sensitivity",
        "bonding_matrix",
        "scenario_coverage",
    }
    for figure in figures.values():
        assert figure.is_file()
        assert figure.stat().st_size > 20_000
