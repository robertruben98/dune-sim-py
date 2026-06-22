"""Unit tests for query-parameter serialization."""

from enum import IntEnum

from dune_sim.client import _serialize_params


class ChainId(IntEnum):
    ETHEREUM = 1
    POLYGON = 137


def test_none_values_dropped():
    assert _serialize_params({"a": None, "b": "x"}) == {"b": "x"}


def test_bool_rendered_as_lowercase_string():
    assert _serialize_params({"flag": True}) == {"flag": "true"}
    assert _serialize_params({"flag": False}) == {"flag": "false"}


def test_int_rendered_as_decimal_string():
    assert _serialize_params({"limit": 50}) == {"limit": "50"}


def test_sequence_joined_with_commas():
    assert _serialize_params({"chain_ids": ["1", "137"]}) == {"chain_ids": "1,137"}


def test_empty_sequence_is_dropped():
    assert _serialize_params({"chain_ids": []}) == {}


def test_int_enum_serializes_to_number_not_member_name():
    # Guards against IntEnum rendering as its name (e.g. "ChainId.ETHEREUM")
    # on Python < 3.11.
    out = _serialize_params({"chain_ids": [ChainId.ETHEREUM, ChainId.POLYGON]})
    assert out == {"chain_ids": "1,137"}


def test_single_int_enum_value():
    assert _serialize_params({"chain_id": ChainId.POLYGON}) == {"chain_id": "137"}
