from anka.ai.semantic import SemanticUnderstanding


def test_negative_turkish_sentence_is_routed_as_emotional_not_document_question():
    analysis = SemanticUnderstanding().analyze("Dün çok yorucu bir gündü, moralim bozuk.")
    assert analysis.tokens[-2:] == ("moralim", "bozuk")
    assert analysis.intent == "emotional"
    assert analysis.emotion == "sadness"
    assert len(analysis.embeddings) == len(analysis.tokens)
    assert len(analysis.attention) == len(analysis.tokens)
    assert all(abs(sum(row) - 1.0) < 0.00001 for row in analysis.attention)


def test_factual_question_is_not_mistaken_for_an_emotional_message():
    analysis = SemanticUnderstanding().analyze("BMW ilk nerede yapıldı?")
    assert analysis.intent == "question"
    assert analysis.emotion is None


def test_crisis_language_is_escalated():
    analysis = SemanticUnderstanding().analyze("Yaşamak istemiyorum")
    assert analysis.intent == "emotional"
    assert analysis.crisis is True


def test_story_is_not_treated_as_a_document_question():
    analysis = SemanticUnderstanding().analyze("Sana bir olay anlatmak istiyorum. Bugün yolda bir çöp gördüm.")
    assert analysis.intent == "conversation"
    assert analysis.narrative is True


def test_positive_emotion_is_detected():
    analysis = SemanticUnderstanding().analyze("Bugün çok mutluyum!")
    assert analysis.intent == "emotional"
    assert analysis.emotion == "joy"
