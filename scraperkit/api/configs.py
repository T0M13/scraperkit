"""
Config manager — CRUD for project YAML config files.

Configs live in a directory (default: ./configs/ relative to cwd).
The API lets the dashboard create, read, update, delete, and validate them.
"""
from __future__ import annotations

from pathlib import Path


class ConfigManager:
    def __init__(self, configs_dir: str | Path = "configs") -> None:
        self.configs_dir = Path(configs_dir)
        self.configs_dir.mkdir(parents=True, exist_ok=True)

    def list_configs(self) -> list[dict]:
        configs = []
        for p in sorted(self.configs_dir.glob("*.yaml")) + sorted(self.configs_dir.glob("*.yml")):
            configs.append({
                "name": p.stem,
                "filename": p.name,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "modified": p.stat().st_mtime,
            })
        return configs

    def read_config(self, name: str) -> str:
        p = self._resolve(name)
        if not p.exists():
            raise FileNotFoundError(f"Config '{name}' not found")
        return p.read_text(encoding="utf-8")

    def write_config(self, name: str, content: str) -> str:
        """Create or overwrite a config. Returns the file path."""
        # Basic safety: no path traversal
        safe_name = Path(name).name
        if not safe_name.endswith((".yaml", ".yml")):
            safe_name = safe_name + ".yaml"
        p = self.configs_dir / safe_name
        # Validate before saving
        self._validate(content)
        p.write_text(content, encoding="utf-8")
        return str(p)

    def delete_config(self, name: str) -> None:
        p = self._resolve(name)
        if not p.exists():
            raise FileNotFoundError(f"Config '{name}' not found")
        p.unlink()

    def validate_config(self, content: str) -> dict:
        """Parse and validate YAML content. Returns parsed config summary or raises."""
        self._validate(content)
        import yaml
        data = yaml.safe_load(content)
        return {
            "valid": True,
            "name": data.get("name", "(unnamed)"),
            "start_urls": data.get("start_urls", []),
            "workflow": data.get("workflow", ["crawl", "export_json"]),
        }

    def _validate(self, content: str) -> None:
        from scraperkit.core.config import ProjectConfig
        import yaml
        try:
            data = yaml.safe_load(content)
        except Exception as exc:
            raise ValueError(f"Invalid YAML: {exc}")
        if not isinstance(data, dict):
            raise ValueError("Config must be a YAML mapping")
        if "name" not in data:
            data = {**data, "name": "_validate"}
        try:
            ProjectConfig.model_validate(data)
        except Exception as exc:
            raise ValueError(f"Config validation error: {exc}")

    def _resolve(self, name: str) -> Path:
        """Find a config file by name (with or without extension)."""
        for ext in (".yaml", ".yml", ""):
            p = self.configs_dir / (name + ext)
            if p.exists():
                return p
        return self.configs_dir / (name + ".yaml")


_manager: ConfigManager | None = None


def get_config_manager(configs_dir: str = "configs") -> ConfigManager:
    global _manager
    if _manager is None:
        _manager = ConfigManager(configs_dir)
    return _manager
