"""
Global registries for workflow steps and extractors.

To add a new step:
    from scraperkit.core.registry import register_step
    @register_step("my_step")
    class MyStep(BaseStep): ...

To add a new extractor:
    from scraperkit.core.registry import register_extractor
    @register_extractor("my_type")
    class MyExtractor(BaseExtractor): ...
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Type

if TYPE_CHECKING:
    from .base import BaseExtractor, BaseStep

WORKFLOW_STEPS: dict[str, Type["BaseStep"]] = {}
EXTRACTORS: dict[str, Type["BaseExtractor"]] = {}


def register_step(name: str) -> Callable:
    def decorator(cls):
        cls.name = name
        WORKFLOW_STEPS[name] = cls
        return cls
    return decorator


def register_extractor(name: str) -> Callable:
    def decorator(cls):
        EXTRACTORS[name] = cls
        return cls
    return decorator


def get_step(name: str) -> Type["BaseStep"]:
    if name not in WORKFLOW_STEPS:
        available = ", ".join(sorted(WORKFLOW_STEPS.keys()))
        raise KeyError(f"Unknown workflow step '{name}'. Available: {available}")
    return WORKFLOW_STEPS[name]


def get_extractor(name: str) -> Type["BaseExtractor"]:
    if name not in EXTRACTORS:
        available = ", ".join(sorted(EXTRACTORS.keys()))
        raise KeyError(f"Unknown extractor '{name}'. Available: {available}")
    return EXTRACTORS[name]
