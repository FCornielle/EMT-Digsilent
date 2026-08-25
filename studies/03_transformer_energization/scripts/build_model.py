from pathlib import Path

from pfemt.config import load_yaml
from pfemt.workflows import build

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "base.yaml"

if __name__ == "__main__":
    objects = build(load_yaml(CONFIG))
    print(objects["project"].loc_name)
