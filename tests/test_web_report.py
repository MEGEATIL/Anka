from anka.web.research import WebResearcher, WebSource
from anka.core.errors import WebResearchError
import web_bilgi


def test_report_is_short_and_has_sources(monkeypatch):
    sources = [
        WebSource("Birinci kaynak", "https://example.com/one", "A" * 260),
        WebSource("İkinci kaynak", "https://example.org/two", "B" * 260),
    ]
    monkeypatch.setattr(WebResearcher, "search", lambda self, query, max_sources=5: sources)
    report = WebResearcher().report("kısa araştırma")
    assert "Kaynaklar:" in report
    assert "example.com" in report
    assert len(report.split("Kaynaklar:")[0]) <= 430


def test_web_answer_is_synthesized_and_sources_are_appended(monkeypatch):
    sources = [
        WebSource("Veri - Vikipedi", "https://tr.wikipedia.org/wiki/Veri", "Veri, anlam çıkarmak için işlenen ham gözlemlerden oluşur."),
        WebSource("Açıklama", "https://example.org/veri", "Veri karar alma sürecinde kullanılan bilgi parçalarıdır."),
    ]
    monkeypatch.setattr(WebResearcher, "search", lambda self, query, max_sources=5: sources)
    monkeypatch.setattr(web_bilgi, "guvenli_tamamla", lambda *args, **kwargs: ("Veri, gözlem veya ölçümden elde edilen ham değerlerdir.", "test-model"))

    answer, raw = web_bilgi.web_den_ogren_ve_ozetle("veri nedir", client=object())

    assert answer.startswith("Veri, gözlem")
    assert "Kaynaklar:" in answer
    assert "wikipedia.org" in answer
    assert "KAYNAK 1" in raw


def test_web_answer_without_llm_never_returns_raw_search_markup(monkeypatch):
    sources = [
        WebSource("Güvenilir kaynak", "https://example.org", "Veri, gözlem ve ölçümlerin kaydedilmiş halidir. Devam metni."),
    ]
    monkeypatch.setattr(WebResearcher, "search", lambda self, query, max_sources=5: sources)

    answer, _ = web_bilgi.web_den_ogren_ve_ozetle("veri nedir")

    assert "Güvenilir kaynak:" not in answer
    assert answer.startswith("Veri, gözlem")


def test_web_answer_never_claims_research_without_verifiable_sources(monkeypatch):
    monkeypatch.setattr(
        WebResearcher,
        "search",
        lambda self, query, max_sources=5: (_ for _ in ()).throw(WebResearchError("yok")),
    )

    answer, raw = web_bilgi.web_den_ogren_ve_ozetle("veri nedir")

    assert "doğrulanabilir kaynak" in answer
    assert raw == ""
