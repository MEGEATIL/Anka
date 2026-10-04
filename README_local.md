# ANKA AI 1.0

ANKA, Türkçe sohbet, kaynaklı web araştırması, belge öğrenme, kalıcı hafıza ve
onaylı bilgisayar görevleri sunan Windows odaklı kişisel asistan projesidir.

## Başlatma

1. Python 3.11 veya 3.12 ile sanal ortam oluşturun.
2. `pip install -r requirements.txt` çalıştırın.
3. `.env.example` dosyasını `.env` olarak kopyalayıp yalnızca kullandığınız
   servislerin değerlerini ekleyin.
4. `python mainyapayzeka1.py` ile masaüstü arayüzünü başlatın.

Kamera yayını isteğe bağlıdır. Çalıştırmadan önce `KAMERA_SIFRE` ve
`NGROK_AUTHTOKEN` tanımlanmalıdır.

## Davranış sınırları

- Sistem, dosya ve uygulama işlemleri izin ve gerektiğinde açık onay ister.
- Web sonuçları kaynaklarıyla birlikte verilir; ağ veya model yoksa ANKA bunu
  başarılı bir araştırma gibi göstermez.
- Dosya öğrenme PDF, DOCX ve TXT ile sınırlıdır.
- Sesli kullanımda mikrofon; kamera görünümünde kamera izni açık olmalıdır.

Mimari, güvenlik ve test ayrıntıları için `ARCHITECTURE.md`, `SECURITY.md` ve
`TESTING.md` dosyalarına bakın.
