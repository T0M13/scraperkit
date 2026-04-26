"""Tests for config loading and validation."""
import textwrap
from pathlib import Path

import pytest
import yaml

from scraperkit.core.config import load_config, ProjectConfig


def write_yaml(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "project.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_minimal_config(tmp_path):
    p = write_yaml(tmp_path, """
        name: test_project
        start_urls:
          - https://example.com
    """)
    config = load_config(p)
    assert config.name == "test_project"
    assert config.start_urls == ["https://example.com"]
    assert config.workflow == ["crawl", "export_json"]


def test_shorthand_css_field(tmp_path):
    p = write_yaml(tmp_path, """
        name: test
        start_urls: [https://example.com]
        crawler:
          item_selector: ".item"
          fields:
            title: ".title::text"
            price: ".price::text"
    """)
    config = load_config(p)
    title_field = config.crawler.fields["title"]
    assert title_field.type == "css"
    assert title_field.selector == ".title::text"


def test_xpath_prefix(tmp_path):
    p = write_yaml(tmp_path, """
        name: test
        start_urls: [https://example.com]
        crawler:
          fields:
            name: "xpath=//h1/text()"
    """)
    config = load_config(p)
    field = config.crawler.fields["name"]
    assert field.type == "xpath"
    assert field.selector == "//h1/text()"


def test_workflow_steps(tmp_path):
    p = write_yaml(tmp_path, """
        name: test
        start_urls: [https://example.com]
        workflow:
          - crawl
          - clean
          - deduplicate
          - export_json
          - export_excel
          - compare_previous
          - backup
    """)
    config = load_config(p)
    assert "compare_previous" in config.workflow
    assert "backup" in config.workflow


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.yaml")


def test_unsupported_format(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("name = 'test'")
    with pytest.raises(ValueError, match="Unsupported config format"):
        load_config(p)


def test_name_inferred_from_filename(tmp_path):
    p = tmp_path / "my_project.yaml"
    p.write_text("start_urls:\n  - https://example.com\n")
    config = load_config(p)
    assert config.name == "my_project"
