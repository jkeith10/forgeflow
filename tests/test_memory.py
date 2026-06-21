from forgeflow.memory.sqlite import (
    memory_delete,
    memory_get,
    memory_list,
    memory_set,
)


def test_set_get_roundtrip():
    memory_set("refund_policy", "Refunds over $500 require approval")
    assert memory_get("refund_policy") == "Refunds over $500 require approval"


def test_overwrite_updates_value():
    memory_set("k", "v1")
    memory_set("k", "v2")
    assert memory_get("k") == "v2"
    assert len([i for i in memory_list() if i.key == "k"]) == 1


def test_missing_key_returns_none():
    assert memory_get("nope") is None


def test_delete():
    memory_set("temp", "x")
    assert memory_delete("temp") is True
    assert memory_get("temp") is None
    assert memory_delete("temp") is False
