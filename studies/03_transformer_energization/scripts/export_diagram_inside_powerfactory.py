from pathlib import Path

from pfemt.config import load_yaml
from pfemt.workflows import export_diagram

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"

if __name__ == "__main__":
    config = load_yaml(CONFIG)
    config["connection"]["mode"] = "internal"
    print(export_diagram(config))
