from anka.ai.llm_controller import LLMController
from anka.memory.manager import MemoryManager


def test_task_type_selects_safe_automation_parameters(tmp_path):
    calls = []

    def generator(**kwargs):
        calls.append(kwargs)
        return "tamam"

    controller = LLMController(MemoryManager(str(tmp_path / "context.db")), local_generator=generator)
    assert controller.generate("not al", task_type="automation") == "tamam"
    assert calls[0]["temperature"] == 0.2
    assert calls[0]["max_tokens"] <= 350


def test_chat_uses_warmer_parameters(tmp_path):
    captured = {}

    def generator(**kwargs):
        captured.update(kwargs)
        return "Merhaba"

    controller = LLMController(MemoryManager(str(tmp_path / "context.db")), local_generator=generator)
    controller.generate("nasılsın", task_type="chat")
    assert captured["temperature"] == 0.7
    assert captured["max_tokens"] <= 650
