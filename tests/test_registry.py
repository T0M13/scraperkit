"""Tests for registry: registration, lookup, unknown step error."""
import scraperkit.steps  # noqa: F401 — triggers registration
import scraperkit.extractors  # noqa: F401

from scraperkit.core.registry import WORKFLOW_STEPS, EXTRACTORS, get_step, get_extractor


def test_builtin_steps_registered():
    expected = {"crawl", "clean", "deduplicate", "export_json", "export_excel",
                "compare_previous", "backup", "notify_slack", "notify_email", "upload_sharepoint"}
    assert expected.issubset(set(WORKFLOW_STEPS.keys()))


def test_builtin_extractors_registered():
    assert set(EXTRACTORS.keys()) == {"css", "xpath", "regex", "json"}


def test_get_step_unknown_raises():
    import pytest
    with pytest.raises(KeyError, match="Unknown workflow step"):
        get_step("does_not_exist")


def test_custom_step_registration():
    from scraperkit.core.base import BaseStep
    from scraperkit.core.registry import register_step

    @register_step("my_custom_step")
    class MyStep(BaseStep):
        def execute(self, ctx):
            return {}

    assert "my_custom_step" in WORKFLOW_STEPS
    assert get_step("my_custom_step") is MyStep
