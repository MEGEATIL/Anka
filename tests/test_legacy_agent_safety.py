import ajan


def test_agent_does_not_treat_non_json_model_output_as_success(monkeypatch):
    monkeypatch.setattr(ajan, "guvenli_tamamla", lambda *args, **kwargs: ("Spotify açıldı", "test"))
    task_agent = ajan.GorevAjani(client=object())
    task_agent.arac_kaydet("noop", lambda: "ok", "test aracı")

    result = task_agent.gorevi_yurut("Spotify aç")

    assert result == "Görev planı doğrulanamadı; herhangi bir işlem yapılmadı."


def test_agent_requires_tool_observation_before_final_success(monkeypatch):
    responses = iter([
        ('{"eylem":"cevap_ver","eylem_girdi":{"mesaj":"Tamamlandı"}}', "test"),
    ])
    monkeypatch.setattr(ajan, "guvenli_tamamla", lambda *args, **kwargs: next(responses))
    task_agent = ajan.GorevAjani(client=object())
    task_agent.arac_kaydet("noop", lambda: "ok", "test aracı")

    result = task_agent.gorevi_yurut("bir şey yap")

    assert result == "Görevin sonucu doğrulanamadı; herhangi bir araç çalıştırılmadı."


def test_agent_rejects_unexpected_tool_arguments(monkeypatch):
    responses = iter([
        ('{"eylem":"not_al","eylem_girdi":{"metin":"not","komut":"sil"}}', "test"),
        ('{"eylem":"cevap_ver","eylem_girdi":{"mesaj":"Tamamlandı"}}', "test"),
    ])
    monkeypatch.setattr(ajan, "guvenli_tamamla", lambda *args, **kwargs: next(responses))
    task_agent = ajan.GorevAjani(client=object())
    task_agent.arac_kaydet("not_al", lambda metin: "kaydedildi", "not alır")

    result = task_agent.gorevi_yurut("not al")

    assert result == "Görev adımlarından biri başarısız oldu; başarı doğrulanamadı."
