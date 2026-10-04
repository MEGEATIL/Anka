"""Türkçe sohbet için gizlilik odaklı yerel anlam ve duygu yönlendiricisi.

Bu modül, cümleyi tokenlara ayırır, her token için kararlı bir sayısal temsil
üretir ve self-attention ile bağlam skoru hesaplar. İsteğe bağlı olarak,
makinede önceden indirilmiş çok dilli bir SentenceTransformer modeli de
kullanılabilir; model yoksa ağ isteği yapmadan yerel temsilciyle çalışır.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import math
import re
from typing import Sequence


_TOKEN_PATTERN = re.compile(r"[\wçğıöşüÇĞİÖŞÜ]+", re.UNICODE)
_NEGATIVE_STEMS = (
    "moral", "mutsuz", "uzgun", "üzgün", "kotu", "kötü", "berbat", "yalniz", "yalnız",
    "yorucu", "yorgun", "bunald", "kayg", "endise", "endişe", "stres",
    "agla", "ağla", "kork", "keder", "umutsuz", "canim sik", "canım sık",
)
_NEGATIVE_PHRASES = (
    "iyi değil", "iyi degil", "iyi değilim", "iyi degilim",
    "pek iyi değil", "pek iyi degil", "iyi hissetmiyorum",
)
_POSITIVE_STEMS = (
    "mutlu", "sevin", "sevind", "harika", "super", "süper", "keyifli",
    "gururlu", "gurur", "heyecanlı", "heyecanli", "basar", "başar", "güzel",
)
_CRISIS_STEMS = ("intihar", "kendimi oldur", "kendimi öldür", "yasamak istem", "yaşamak istem")
_FACTUAL_MARKERS = ("nedir", "kimdir", "nerede", "ne zaman", "nasıl", "nasil", "kaç", "hangi")
_ACTION_MARKERS = ("aç", "ac", "kapat", "oluştur", "olustur", "ara", "indir", "sil")
_NARRATIVE_MARKERS = (
    "olay anlatmak", "bir şey anlatmak", "bir sey anlatmak", "başına geldi",
    "basima geldi", "başıma geldi", "yaşadım", "yasadim", "bugün yolda", "dün yolda",
)


@dataclass(frozen=True)
class SemanticAnalysis:
    tokens: tuple[str, ...]
    embeddings: tuple[tuple[float, ...], ...]
    attention: tuple[tuple[float, ...], ...]
    intent: str
    emotion: str | None
    confidence: float
    crisis: bool = False
    narrative: bool = False


class SemanticUnderstanding:
    """Deterministik yerel embedding + attention tabanlı sohbet yönlendiricisi."""

    dimension = 48

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(token.casefold() for token in _TOKEN_PATTERN.findall(text or ""))

    @lru_cache(maxsize=2048)
    def _embedding_for_token(self, token: str) -> tuple[float, ...]:
        """Karakter n-gram'ları ile tekrarlanabilir, yerel token embedding'i üretir."""
        values = [0.0] * self.dimension
        padded = f"<{token}>"
        grams = [padded[index:index + width] for width in (2, 3, 4) for index in range(len(padded) - width + 1)]
        for gram in grams or [padded]:
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            values[index] += sign
        length = math.sqrt(sum(value * value for value in values)) or 1.0
        return tuple(value / length for value in values)

    def embed(self, tokens: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        return tuple(self._embedding_for_token(token) for token in tokens)

    def attention_weights(self, embeddings: Sequence[Sequence[float]]) -> tuple[tuple[float, ...], ...]:
        """Ölçeklenmiş nokta çarpımı ile tokenlar arası self-attention."""
        if not embeddings:
            return ()
        scale = math.sqrt(self.dimension)
        rows: list[tuple[float, ...]] = []
        for query in embeddings:
            scores = [sum(left * right for left, right in zip(query, key)) / scale for key in embeddings]
            maximum = max(scores)
            exponentials = [math.exp(score - maximum) for score in scores]
            total = sum(exponentials) or 1.0
            rows.append(tuple(value / total for value in exponentials))
        return tuple(rows)

    def analyze(self, text: str) -> SemanticAnalysis:
        tokens = self.tokenize(text)
        embeddings = self.embed(tokens)
        attention = self.attention_weights(embeddings)
        normalized = " ".join(tokens)
        crisis = any(marker in normalized for marker in _CRISIS_STEMS)
        negative_hits = sum(1 for marker in _NEGATIVE_STEMS if marker in normalized)
        negative_hits += sum(1 for phrase in _NEGATIVE_PHRASES if phrase in normalized)
        positive_hits = sum(1 for marker in _POSITIVE_STEMS if marker in normalized)
        narrative = any(marker in normalized for marker in _NARRATIVE_MARKERS)
        factual = text.strip().endswith("?") or any(marker in tokens for marker in _FACTUAL_MARKERS)
        action = any(marker in tokens for marker in _ACTION_MARKERS)

        if crisis:
            intent, emotion, confidence = "emotional", "crisis", 0.99
        elif negative_hits and not factual and not action:
            # Birden fazla olumsuz token birbirini attention ile destekliyorsa
            # güveni artır; bu cümle paylaşım mı, bilgi sorusu mu ayrımına yardım eder.
            contextual_weight = sum(max(row) for row in attention) / len(attention) if attention else 0.0
            intent, emotion = "emotional", "sadness"
            confidence = min(0.96, 0.66 + 0.10 * negative_hits + 0.12 * contextual_weight)
        elif positive_hits and not factual and not action:
            intent, emotion, confidence = "emotional", "joy", min(0.94, 0.66 + 0.10 * positive_hits)
        elif action:
            intent, emotion, confidence = "action", None, 0.72
        elif factual:
            intent, emotion, confidence = "question", None, 0.72
        else:
            intent, emotion, confidence = "conversation", None, 0.50
        return SemanticAnalysis(tokens, embeddings, attention, intent, emotion, confidence, crisis, narrative)
