import groq_llm


def test_groq_memory_uses_atomic_persistent_storage(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    memory = groq_llm.GroqChatMemory(max_messages=2)
    memory.add_message("user", "birinci")
    memory.add_message("assistant", "ikinci")
    memory.add_message("user", "üçüncü")

    restored = groq_llm.GroqChatMemory(max_messages=2)

    assert [item["content"] for item in restored.get_messages()] == ["ikinci", "üçüncü"]
    assert (tmp_path / "konusma_hafizasi.json").exists()
    assert not (tmp_path / "konusma_hafizasi.tmp").exists()


def test_groq_memory_recovers_from_corrupt_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "konusma_hafizasi.json").write_text("{broken", encoding="utf-8")

    memory = groq_llm.GroqChatMemory()

    assert memory.get_messages() == []


def test_groq_llm_without_provider_returns_safe_message(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    assistant = groq_llm.GroqLLM()

    assert "yapılandırılmamış" in assistant.chat("merhaba")
