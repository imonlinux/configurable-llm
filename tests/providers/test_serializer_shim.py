"""Regression test for the custom-serializer sentinel shim (v1.2.1).

Locks in the HA 2026.9 fix without needing probatio or a 2026.9 tree: a plain
object() stands in for probatio.UNSUPPORTED, so this runs in CI on the pinned
2025.8.1 tree and still guards the 2026.9 behavior.
"""

import voluptuous as vol
from voluptuous_openapi import UNSUPPORTED, convert

from custom_components.configurable_llm.providers.base import (
    adapt_custom_serializer,
)


def _render(schema, serializer):
    """convert() with the shim applied, as the providers do at each call site."""
    return convert(schema, custom_serializer=adapt_custom_serializer(serializer))


def test_foreign_sentinel_falls_back_to_native() -> None:
    """A foreign sentinel (probatio.UNSUPPORTED stand-in) must not reach convert.

    Without the shim, convert() raises TypeError in ensure_default on the foreign
    object. With it, the leaf renders natively.
    """
    foreign = object()  # stands in for probatio.UNSUPPORTED
    schema = vol.Schema({vol.Required("name"): str})

    def serializer(node):
        return foreign if node is str else UNSUPPORTED

    out = _render(schema, serializer)
    assert out["properties"]["name"] == {"type": "string"}
    assert foreign not in out["properties"].values()


def test_none_falls_back_to_native() -> None:
    """A serializer returning None is treated as 'unhandled', not a value."""
    schema = vol.Schema({vol.Required("name"): str})

    def serializer(node):
        return None if node is str else UNSUPPORTED

    out = _render(schema, serializer)
    assert out["properties"]["name"] == {"type": "string"}


def test_real_dict_passes_through_untouched() -> None:
    """A genuine schema dict from the serializer must be preserved verbatim."""
    marker = {"type": "string", "format": "custom-entity-id"}
    schema = vol.Schema({vol.Required("entity"): str})

    def serializer(node):
        return marker if node is str else UNSUPPORTED

    out = _render(schema, serializer)
    assert out["properties"]["entity"] == marker


def test_own_sentinel_still_defers() -> None:
    """voluptuous_openapi's own UNSUPPORTED must keep working (older-HA path)."""
    schema = vol.Schema({vol.Required("name"): str})
    out = _render(schema, lambda node: UNSUPPORTED)
    assert out["properties"]["name"] == {"type": "string"}


def test_wrapper_predicate_directly() -> None:
    """Pin the predicate itself, independent of convert().

    Foreign sentinel / None -> UNSUPPORTED; a real dict -> passed through.
    """
    foreign = object()
    marker = {"type": "string"}
    assert adapt_custom_serializer(lambda n: foreign)("x") is UNSUPPORTED
    assert adapt_custom_serializer(lambda n: None)("x") is UNSUPPORTED
    assert adapt_custom_serializer(lambda n: UNSUPPORTED)("x") is UNSUPPORTED
    assert adapt_custom_serializer(lambda n: marker)("x") == marker
