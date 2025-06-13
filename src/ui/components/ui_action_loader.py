import yaml
from pathlib import Path

def load_actions_yaml():
    """
    UIアクション定義YAMLを読み込む
    Returns: List[dict]
    """
    path = Path(__file__).parent.parent / "ui_actions.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
