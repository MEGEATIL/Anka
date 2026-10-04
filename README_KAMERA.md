# Yapay Zeka Asistanı - Kamera Sunucusu + Email Entegrasyonu

## Kurulum Adımları

### 1. Gmail Kurulumunu Yap
```bash
python EMAIL_SETUP.py
```

**Gmail Uygulama Şifresi Nasıl Alınır:**
- https://myaccount.google.com/apppasswords adresine git
- Google hesabına giriş yap
- "2-Adımla Doğrulama" etkinse, uygulama şifresi seçeneği görüntülenecek
- "16 karakter boşluksuz şifre" al
- EMAIL_SETUP.py'de istendiğinde yapıştır

### 2. ngrok Kurulumunu Yap (İsteğe Bağlı)
Eğer ngrok tunnel kullanmak istiyorsanız:
```bash
python ngrok_setup.py
```
ngrok authtoken'ını gir: https://dashboard.ngrok.com/auth/your-authtoken

### 3. Programı Çalıştır
```bash
python mainyapayzeka1.py
```

## Otomatik Süreç

1. **mainyapayzeka1.py** çalıştırıldığında:
   - Flask tarafından kameraserver.py otomatik başlatılır
   - ngrok tunnel açılır (eğer ayarlanmışsa)
   - Kamera feed yayınlanmaya başlar
   - ngrok URL kaydedilir

2. **Email Gönderme:**
   - URL otomatik olarak **m.egedik02@gmail.com** adresine gönderilir
   - Email başlığı: "Kamera Server Baslatildi"
   - İçerikte URL ve başlama saati yer alır

3. **URL'ler şu dosyalarda da bulunur:**
   - `ngrok_url.json` - JSON formatında URL
   - `ngrok_url.txt` - Okunması kolay format

## Erişim

Kamera feed'ine şu URL'den erişebilirsin:
```
https://xxxx-xx-xxx-xxx-xxx.ngrok.app/kamera
```

(Bu URL email ile gönderilir)

## Dosyalar

- `mainyapayzeka1.py` - Ana asistan programı (kamera + email entegrasyonu)
- `kameraserver.py` - Flask kamera sunucusu (ngrok entegrasyonlu)
- `EMAIL_SETUP.py` - Gmail kurulum helper'ı
- `ngrok_setup.py` - ngrok kurulum helper'ı
- `ngrok_url.json` - Çalışan ngrok URL'si (otomatik oluşturulur)
- `ngrok_url.txt` - Okunması kolay URL bilgisi (otomatik oluşturulur)

## Sorun Giderme

| Problem | Çözüm |
|---------|-------|
| **Email gönderilemedi** | EMAIL_SETUP.py'yi çalıştır ve kurulum yap |
| **Gmail "Şifre yanlış" hatası** | Uygulama şifresini (normal şifreyi değil) kullan |
| **ngrok bağlantı hatası** | ngrok_setup.py'yi çalıştır, authtoken gir |
| **Kamera başlamıyor** | Web kameranın çalıştığını kontrol et |

## Güvenlik Notu

- Gmail uygulama şifresi sadece email göndermek için kullanılır
- Normal Gmail şifrenizi girmemeyin, uygulama şifresi kullanın
- Bilgisayarın kapalı olduğunda program çalışmaz
