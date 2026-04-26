"""
Helper module for running the spider in a subprocess when the Twisted reactor
has already been used in the parent process.

Usage (internal):
    python -m scraperkit._subprocess_spider <config_json_path> <output_json_path>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m scraperkit._subprocess_spider <cfg.json> <out.json>", file=sys.stderr)
        sys.exit(1)

    cfg_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    from scraperkit.core.config import ProjectConfig
    from scraperkit.spider.runner import run_spider

    config = ProjectConfig.model_validate_json(cfg_path.read_text(encoding="utf-8"))
    items = run_spider(config)
    out_path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
