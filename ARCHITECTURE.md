# Mimari

- `mainyapayzeka1.py`: mevcut uygulamanın giriş noktası ve eski özelliklerle
  uyumluluk katmanı. Yeni kod mümkün oldukça `anka/` paketindedir.
- `anka/ai`: LLM parametre kontrolü, Türkçe anlam ve duygu yönlendirmesi.
- `anka/memory`: JSON kalıcı hafıza ve SQLite konuşma bağlamı.
- `anka/security`: izinler, risk politikası ve kullanıcı dosya yolu denetimi.
- `anka/core`: görev yaşam döngüsü, hatalar ve günlükleme.
- `anka/tools`: güvenli hesap makinesi, medya oturumu ve araç kayıt defteri.
- `anka/files`: güvenli PDF/DOCX/TXT okuma.
- `anka/web`: kaynak seçimi ve kaynaklı web özeti.
- `dijidost_entegrasyon.py`: WebView arayüzü ve Python köprüsü.

Görev akışı: istek -> plan -> risk/izin -> gerekirse onay -> çalıştırma ->
sonuç/hata raporu. `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` risk seviyeleri
`anka/security/policy.py` içinde tanımlıdır.
