# Yapılandırma

`.env.example` dosyasını `.env` olarak kopyalayın. Değerleri boş bırakmak,
ilgili isteğe bağlı hizmeti kapalı tutar.

| Değişken | Amaç |
| --- | --- |
| `HF_TOKEN` | Hugging Face uyumlu LLM erişimi |
| `GROQ_API_KEY` | İsteğe bağlı Groq sohbet motoru |
| `KAMERA_SIFRE` | Kamera yayın sunucusu erişim parolası |
| `NGROK_AUTHTOKEN` | Kamera yayını için ngrok hesabı erişimi |
| `APP_SECRET` | Kamera sunucusu oturum imzalama anahtarı |

Hiçbir gizli değeri `requirements.txt`, Python kaynak dosyaları, günlükler veya
Git deposuna eklemeyin. Anahtar sızdıysa sağlayıcı panelinden hemen iptal edip
yeni anahtar oluşturun.
