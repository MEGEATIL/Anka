# -*- coding: utf-8 -*-
"""
llm_yardimci.py
---------------
HF Inference Providers (router.huggingface.co) üzerindeki ücretsiz modeller
sık sık değişip "deprecated" / "model_not_found" hatası veriyor. Tek bir model
adını koda sabitlemek yerine, burada bir ADAY MODEL LİSTESİ tutuyoruz ve
sırayla deneyip ilk çalışanı kullanıyoruz. Böylece bir model kaldırıldığında
kodu değiştirmene gerek kalmaz - otomatik bir sonrakine geçer.

Kullanım:
    from llm_yardimci import guvenli_tamamla
    cevap, kullanilan_model = guvenli_tamamla(client, messages)

Not: Modellerden biri kalıcı olarak çalışmaya başlarsa (veya hepsi
deprecate olursa), bu listeyi güncellemen gerekir. Güncel liste için:
https://huggingface.co/docs/inference-providers
"""

# En yeni/güçlüden en eski/yedeğe doğru sıralı aday model listesi.
# Provider eki (:novita gibi) BİLEREK yazılmadı; böylece HF router o an
# hangi sağlayıcı canlıysa (auto) oraya yönlendiriyor - tek sağlayıcıya
# (novita gibi) bağımlı kalıp onun deprecate kararlarından etkilenmiyoruz.
MODEL_ADAYLARI = [
    "meta-llama/Llama-3.3-70B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-72B-Instruct",
    "microsoft/Phi-3.5-mini-instruct",
]


def guvenli_tamamla(client, messages, tercih_edilen_model=None, **ek_parametreler):
    """Aday modelleri sırayla dener, ilk başarılı olanın cevabını döndürür.

    Dönüş: (cevap_metni: str, kullanilan_model: str)
    Hepsi başarısız olursa RuntimeError fırlatır (son hatayı içerir).
    """
    denenecekler = []
    if tercih_edilen_model:
        denenecekler.append(tercih_edilen_model)
    for m in MODEL_ADAYLARI:
        if m not in denenecekler:
            denenecekler.append(m)

    son_hata = None
    for model in denenecekler:
        try:
            completion = client.chat.completions.create(
                model=model, messages=messages, **ek_parametreler
            )
            return completion.choices[0].message.content, model
        except Exception as e:
            son_hata = e
            continue

    raise RuntimeError("Dil modeli şu an yanıt veremiyor. Bağlantıyı veya API ayarlarını kontrol edin.") from son_hata
