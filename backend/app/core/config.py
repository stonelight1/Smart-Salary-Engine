"""配置加载 - 启动时加载 YAML 配置"""

from pathlib import Path
from typing import Any

import yaml

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


class ConfigLoader:
    """YAML 配置加载器"""

    def __init__(self) -> None:
        self._configs: dict[str, dict[str, Any]] = {}

    def load_all(self) -> None:
        """启动时加载所有配置文件"""
        config_files = {
            "fields": "fields.yaml",
            "sheet_rules": "sheet_rules.yaml",
            "check_rules": "check_rules.yaml",
            "formula_rules": "formula_rules.yaml",
            "export_templates": "export_templates.yaml",
        }
        for key, filename in config_files.items():
            path = CONFIG_DIR / filename
            if not path.exists():
                raise FileNotFoundError(f"配置文件不存在: {path}")
            with open(path, encoding="utf-8") as f:
                self._configs[key] = yaml.safe_load(f)

    def get(self, key: str) -> dict[str, Any]:
        return self._configs.get(key, {})


config_loader = ConfigLoader()
