# -*- coding: utf-8 -*-
"""
web_bilgi.py
------------
Asistan bir konuyu (ogrenilen_bilgiler tablosunda) bilmiyorsa, DuckDuckGo'nun
API-key gerektirmeyen HTML arama sonuçlarını çekip LLM ile özetleyen modül.
(Google Custom Search API key gerektirdiği için, key istemeyen DuckDuckGo
kullanıldı. İstersen ileride Google Custom Search API'ye çevirebiliriz.)

Kurulum:
    pip install beautifulsoup4
"""

from llm_yardimci import guvenli_tamamla
from anka.core.errors import WebResearchError
from anka.web.research import WebResearcher, WebSource


def _kisa_cevir(metin, limit=280):
    temiz = " ".join(str(metin or "").split())
    if len(temiz) <= limit:
        return temiz
    return temiz[:limit - 3].rsplit(" ", 1)[0] + "..."


def _kaynak_metni(sources: list[WebSource]) -> str:
    """Modelin yalnızca araştırma kanıtlarıyla cevap üretmesi için bağlam oluşturur."""
    return "\n\n".join(
        f"KAYNAK {index}: {source.title}\nAdres: {source.url}\nÖzet: {source.snippet}"
        for index, source in enumerate(sources[:4], start=1)
    )


def _model_cevabini_temizle(cevap: str, limit: int = 430) -> str:
    """Modelin kaynak listesini veya gereksiz uzun açıklamayı tekrar etmesini engeller."""
    temiz = str(cevap or "").strip()
    temiz = temiz.split("Kaynaklar:", 1)[0].strip()
    return _kisa_cevir(temiz, limit)


def web_den_ogren_ve_ozetle(soru, client=None, model=None):
    """İnternetten arama yapıp kısa bir özet cevap üretir.
    `client` verilmezse (None) LLM ile özetleme yapılmaz, bunun yerine en
    alakalı arama sonucu doğrudan döndürülür - böylece HF_TOKEN ayarlanmamış
    olsa bile "bilmediğim konuları Google'da ara" özelliği çalışmaya devam eder.
    Dönüş: (cevap: str, ham_bilgi: str) -> ham_bilgi, öğrenilen_bilgiler tablosuna
    kaydetmek istersen kullanılabilir.
    """
    try:
        sources = WebResearcher().search(soru)
    except WebResearchError:
        return "Araştırma için doğrulanabilir kaynak bulunamadı. Bağlantıyı kontrol edip tekrar deneyin.", ""

    baglam = _kaynak_metni(sources)
    citations = WebResearcher.format_sources(sources)
    if not client:
        return f"{WebResearcher.offline_summary(sources)}\n\nKaynaklar:\n{citations}", baglam

    prompt = (
        "Sen ANKA'nın Türkçe araştırma editörüsün. Kullanıcının sorusuna yalnızca "
        "aşağıdaki kaynak kanıtlarıyla, doğal Türkçe ve en fazla 3 kısa cümleyle cevap ver. "
        "Arama sonucu başlıklarını, lisans metnini veya alakasız ayrıntıları kopyalama. "
        "Kaynaklar çelişiyorsa bunu kısa biçimde belirt; kanıt yoksa açıkça söyle. "
        "Yanıta 'Kaynaklar' başlığı ekleme.\n\n"
        f"SORU: {soru}\n\nKANITLAR:\n{baglam}"
    )
    try:
        cevap, _kullanilan_model = guvenli_tamamla(
            client, [{"role": "user", "content": prompt}], tercih_edilen_model=model,
            temperature=0.25, max_tokens=240,
        )
        temiz_cevap = _model_cevabini_temizle(cevap)
        if len(temiz_cevap) < 12:
            temiz_cevap = WebResearcher.offline_summary(sources)
        return f"{temiz_cevap}\n\nKaynaklar:\n{citations}", baglam
    except Exception:
        # Kaynaklar zaten doğrulandı; model erişilemezse güvenli yerel özetle dön.
        return f"{WebResearcher.offline_summary(sources)}\n\nKaynaklar:\n{citations}", baglam
