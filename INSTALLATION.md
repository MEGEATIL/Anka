# Kurulum

ANKA için desteklenen Python sürümü 3.11 veya 3.12'dir. Proje dizininde:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q
python mainyapayzeka1.py
```

`HF_TOKEN` olmadan temel yerel güvenlik, hafıza ve arayüz özellikleri açılır;
LLM tabanlı sohbet ve sentezlenmiş araştırma çalışmaz. Kamera yayını kullanımı
ayrıca `KAMERA_SIFRE` ve `NGROK_AUTHTOKEN` gerektirir.

Eski `.venv_new` ortamı taşınmış bir Python yoluna bağlıysa yeni bir `.venv`
oluşturun; bu proje için taşınabilir sanal ortam olarak kabul edilmez.
