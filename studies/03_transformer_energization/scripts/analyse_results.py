from pathlib import Path

from pfemt.config import load_yaml
from pfemt.workflows import analyse_transformer_sweep

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"

if __name__ == "__main__":
    print(analyse_transformer_sweep(load_yaml(CONFIG)))
