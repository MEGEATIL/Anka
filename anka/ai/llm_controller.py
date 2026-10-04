"""Türkçe LLM sağlayıcıları için parametre ve token bütçesi denetleyicisi."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from anka.core.errors import ModelServiceError
from anka.memory.manager import MemoryManager
from anka.ai.router import InternalModelRouter, TaskType


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float
    max_tokens: int


class LLMController:
    """ANKA AI dahili model yönlendiricisi ile tüm istemleri dinamik parametrelerle işler."""

    def __init__(self, memory: MemoryManager, client: Any = None, local_generator: Callable[..., str] | None = None, token_limit: int = 4_096):
        self.memory = memory
        self.client = client
        self.local_generator = local_generator
        self.token_limit = token_limit
        self.router = InternalModelRouter()

    def config_for(self, task_type: str, user_input: str = "") -> GenerationConfig:
        route_info = self.router.route(task_type, user_input)
        return GenerationConfig(
            temperature=route_info["temperature"],
            max_tokens=route_info["max_tokens"],
        )

    def generate(self, user_input: str, task_type: str = "chat", system_prompt: str = "") -> str:
        config = self.config_for(task_type, user_input)
        messages = self.memory.build_context(user_input, system_prompt)
        input_tokens = sum(self.memory.estimate_tokens(message["content"]) + 4 for message in messages)
        remaining_tokens = self.token_limit - input_tokens
        if remaining_tokens < 64:
            raise ModelServiceError("Bağlam token sınırına ulaştı.")
        max_tokens = min(config.max_tokens, remaining_tokens)
        try:
            if self.local_generator:
                reply = self.local_generator(messages=messages, temperature=config.temperature, max_tokens=max_tokens)
            elif self.client:
                completion = self.client.chat.completions.create(
                    messages=messages, temperature=config.temperature, max_tokens=max_tokens,
                )
                reply = completion.choices[0].message.content
            else:
                raise ModelServiceError("LLM sağlayıcısı yapılandırılmamış.")
        except ModelServiceError:
            raise
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError) as exc:
            raise ModelServiceError("Dil modeli yanıtı alınamadı.") from exc
        reply = str(reply or "").strip()
        if not reply:
            raise ModelServiceError("Dil modeli boş yanıt verdi.")
        self.memory.add_message("user", user_input)
        self.memory.add_message("assistant", reply)
        return reply

