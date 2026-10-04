# Güvenlik Notları

- API anahtarları kaynak koda yazılmamalıdır; `.env` yereldir ve Git'e eklenmez.
- Kamera yayını varsayılan parola veya gömülü ngrok belirteciyle başlamaz.
- Kamera donanımı ve isteğe bağlı bağımlılıklar yoksa sunucu çökmek yerine
  erişilemez durumunu döndürür. Yüz kaydı/yüz girişi oturum koruması ister;
  yüz kodlamaları JSON olarak tutulur. Eski `encodings.pkl` dosyaları güvenlik
  nedeniyle okunmaz; gerekirse yüzler yeniden kaydedilmelidir.
- Kamera oturum çerezleri JavaScript erişimine kapalıdır ve `SameSite=Lax`
  ile gönderilir. Güvenilen ters proxy kullanılmadıkça istemcinin
  `X-Forwarded-For` başlığı IP kimliği olarak kabul edilmez.
- `eval()` kullanılmaz; hesap makinesi izinli AST düğümleriyle çalışır.
- Sistem kapatma/yeniden başlatma, uygulama açma ve dosya işlemleri onay ve
  ilgili izin denetiminden geçer.
- Göreli dosya oluşturma işlemleri `Belgeler/ANKA` altında yapılır. Dosya
  erişimi Masaüstü, Belgeler ve İndirilenler ile sınırlıdır.
- Günlükler erişim anahtarı, token, parola ve şifre gibi tanımlı değerleri
  maskelemeye çalışır. Günlükleri yine de kişisel veri içerebileceği için
  paylaşmadan önce gözden geçirin.

Sıfırlama, kişisel hafıza ve arayüz durumunu siler; kod ve bağımlılıkları silmez.
İşlem geri alınamaz.
