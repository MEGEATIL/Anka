from anka.memory.manager import MemoryManager


def test_sliding_window_respects_token_budget(tmp_path):
    memory = MemoryManager(str(tmp_path / "context.db"), context_token_limit=20)
    memory.add_message("user", "bir iki üç dört beş altı")
    memory.add_message("assistant", "yedi sekiz dokuz on on bir on iki")
    context = memory.build_context("son mesaj")
    total = sum(memory.estimate_tokens(item["content"]) + 4 for item in context)
    assert total <= 20
    assert context[-1]["content"] == "son mesaj"


def test_relevant_persistent_memory_is_injected(tmp_path):
    memory = MemoryManager(str(tmp_path / "context.db"), context_token_limit=200)
    memory.remember("preference", "Kullanıcı sade ve kısa Türkçe yanıtları seviyor.")
    context = memory.build_context("Kısa bir Türkçe cevap ver")
    assert any("kalıcı hafıza" in item["content"].casefold() for item in context)


def test_single_long_input_is_truncated_to_the_budget(tmp_path):
    memory = MemoryManager(str(tmp_path / "context.db"), context_token_limit=12)
    context = memory.build_context(" ".join(f"kelime{i}" for i in range(40)))
    assert sum(memory.estimate_tokens(item["content"]) + 4 for item in context) <= 12


def test_clear_removes_history_and_persistent_memories(tmp_path):
    memory = MemoryManager(str(tmp_path / "context.db"))
    memory.add_message("user", "kalıcı olmayan konuşma")
    memory.remember("note", "silinmesi gereken not")

    memory.clear()

    assert memory.relevant_memories("silinmesi gereken") == []
    assert memory.build_context("yeni soru") == [{"role": "user", "content": "yeni soru"}]
