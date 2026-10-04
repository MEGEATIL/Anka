from anka.ai.emotional_dialog import EmotionalDialog
from anka.ai.semantic import SemanticUnderstanding


def test_joy_follow_up_does_not_use_a_sadness_reply():
    analyzer = SemanticUnderstanding()
    dialog = EmotionalDialog()
    assert "Seni mutlu eden" in dialog.respond("Bugün çok mutluyum", analyzer.analyze("Bugün çok mutluyum"))
    assert dialog.respond("Bana hediye aldılar", analyzer.analyze("Bana hediye aldılar")) == (
        "Ne güzel, hediye almak gerçekten sevindirici. Güle güle kullan!"
    )
    assert dialog.active is False


def test_topic_change_ends_previous_sadness_context():
    analyzer = SemanticUnderstanding()
    dialog = EmotionalDialog()
    dialog.respond("Mutsuzum", analyzer.analyze("Mutsuzum"))
    assert dialog.respond("Nasılsın", analyzer.analyze("Nasılsın")) is None
    assert dialog.active is False


def test_sadness_follow_up_is_handled_once_not_repeated():
    analyzer = SemanticUnderstanding()
    dialog = EmotionalDialog()
    dialog.respond("Moralim bozuk", analyzer.analyze("Moralim bozuk"))
    assert "Bunu yaşamak zor" in dialog.respond("Bugün kötü geçti", analyzer.analyze("Bugün kötü geçti"))
    assert dialog.respond("Başka bir şey soracağım", analyzer.analyze("Başka bir şey soracağım")) is None


def test_negated_wellbeing_is_sadness_not_a_word_definition():
    analyzer = SemanticUnderstanding()
    dialog = EmotionalDialog()
    reply = dialog.respond("Pek iyi değilim", analyzer.analyze("Pek iyi değilim"))
    assert "Pek iyi olmadığını" in reply
