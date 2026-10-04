# Testler

Standart kurulumdan sonra:

```powershell
python -m pytest -q
```

Testler hesap makinesi güvenliğini, görev onayını, izin kalıcılığını, dosya
doğrulamasını, hafızayı, web kaynak raporlarını, duygu yönlendirmesini,
kullanıcı yolu sınırlarını, araç şemalarını, kamera giriş sınırını, atomik
durum yazımını ve hotword başlatıcısını kapsar.

Masaüstü WebView, mikrofon, kamera ve gerçek harici servisler cihaz bağımlı
olduğundan ayrıca manuel doğrulama gerektirir. Ağ, API anahtarı veya donanım
yoksa başarılı sonuç beklenmemelidir; kullanıcıya durum hatası gösterilmelidir.

Geliştirici amaçlı veritabanı silme betiği onaysız çalışmaz:

```powershell
python reset_db.py --confirm-reset
```
