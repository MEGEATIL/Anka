"""Duygu paylaşımında tekrar eden yanıtları önleyen kısa diyalog durumu."""

from __future__ import annotations

from anka.ai.semantic import SemanticAnalysis


class EmotionalDialog:
    """Duygu bağlamını yalnızca gerekli olduğu bir tur boyunca taşır."""

    _TOPIC_SHIFT_TOKENS = {
        "nasılsın", "nasilsin", "nasılsınız", "nasilsiniz", "iyi", "selam",
        "merhaba", "ne", "kim", "nerede", "hangi", "kaç", "saat", "hava",
    }
    _CANCEL_TOKENS = {"hayır", "hayir", "istemiyorum", "gerek", "sonra", "vazgeç"}

    def __init__(self) -> None:
        self.active_emotion: str | None = None

    @property
    def active(self) -> bool:
        return self.active_emotion is not None

    def respond(self, text: str, analysis: SemanticAnalysis) -> str | None:
        """Yanıt verilecekse metni döndürür, konu değişmişse ``None`` döndürür."""
        tokens = set(analysis.tokens)
        normalized = " ".join(analysis.tokens)

        if analysis.crisis:
            self.active_emotion = None
            return (
                "Bunu duyduğuma üzüldüm. Şu an kendine zarar verme riski varsa lütfen "
                "hemen 112'yi ara veya yanında güvenebileceğin birine haber ver. Şu an güvende misin?"
            )

        # Aktif bağlamda gelen neden/açıklama da olumsuz kelimeler içerebilir.
        # Önce bu tek turu tamamla; aksi halde her açıklama yeni bir başlangıç
        # sayılır ve aynı soru sonsuza kadar tekrar eder.
        if self.active:
            if self._is_topic_shift(text, analysis, tokens):
                self.active_emotion = None
                return None
            if tokens & self._CANCEL_TOKENS or normalized in self._CANCEL_TOKENS:
                self.active_emotion = None
                return "Tamam. Konuşmak istersen buradayım; istersen başka bir şeye de geçebiliriz."

            emotion = self.active_emotion
            self.active_emotion = None  # Aynı kalıp yanıtı sonraki her mesaja taşıma.
            if emotion == "joy":
                if "hediye" in tokens:
                    return "Ne güzel, hediye almak gerçekten sevindirici. Güle güle kullan!"
                return "Bunu paylaşman güzel. Sevincin bol olsun!"
            if emotion == "sadness":
                return "Bunu yaşamak zor gelmiş olabilir. İstersen biraz daha anlat; seni yargılamadan dinliyorum."
            return "Paylaştığın için teşekkür ederim. İstersen devam edebilirsin."

        if analysis.intent == "emotional":
            self.active_emotion = analysis.emotion
            if analysis.emotion == "joy":
                return "Çok güzel, mutlu olduğunu duymak sevindirdi. Seni mutlu eden ne oldu?"
            if "iyi" in tokens and any(token.startswith("değil") or token.startswith("degil") for token in tokens):
                return "Pek iyi olmadığını duyuyorum. Ne oldu, biraz konuşmak ister misin?"
            return "Moralinin bozuk olduğunu duyuyorum. Ne oldu, biraz konuşmak ister misin?"

        if analysis.narrative and not self.active:
            self.active_emotion = "story"
            return "Anlatabilirsin, seni dinliyorum. Sonra ne oldu?"
        return None

    def _is_topic_shift(self, text: str, analysis: SemanticAnalysis, tokens: set[str]) -> bool:
        if analysis.intent in {"action", "question"}:
            return True
        if tokens & self._TOPIC_SHIFT_TOKENS:
            return True
        return text.strip().endswith("?")
