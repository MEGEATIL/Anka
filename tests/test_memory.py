from anka.memory.store import MemoryStore


def test_memory_can_list_search_forget_and_clear(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.json"))
    store.remember("profile", "Kullanıcının adı Ada")
    store.remember("note", "Pazartesi toplantı var")
    assert len(store.search("ada")) == 1
    assert store.forget("toplantı") == 1
    store.clear()
    assert store.list() == []


def test_empty_forget_or_search_does_not_expose_or_delete_memories(tmp_path):
    store = MemoryStore(str(tmp_path / "memory.json"))
    store.remember("profile", "Kullanıcının adı Ada")

    assert store.search("") == []
    assert store.forget("   ") == 0
    assert len(store.list()) == 1
