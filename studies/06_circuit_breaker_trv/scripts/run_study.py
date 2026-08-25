from pathlib import Path

from pfemt.config import load_yaml
from pfemt.workflows import analyse_fault_sweep, archive_project, run_fault_sweep

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"

if __name__ == "__main__":
    config = load_yaml(CONFIG)
    print(run_fault_sweep(config))
    print(analyse_fault_sweep(config))
    print(archive_project(config))
