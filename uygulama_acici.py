# -*- coding: utf-8 -*-
"""
uygulama_acici.py
------------------
"Visual Studio Code aç", "kamerayı aç", "chrome aç" gibi komutları
sabit kod yazmadan, bilgisayardaki KURULU TÜM programları tarayarak çözer.

Kurulum (Windows):
    pip install pywin32 winshell

Nasıl çalışır:
1) uygulama_listesini_tara() -> Başlat Menüsü kısayollarını (.lnk) ve
   Windows'un "App Paths" registry kaydını tarayarak {isim: yol} sözlüğü
   çıkarır, uygulamalar.json dosyasına kaydeder (her seferinde yeniden
   taramamak için).
2) uygulama_ac(isim) -> Kullanıcının söylediği isme en yakın eşleşen
   uygulamayı bulur (difflib ile bulanık eşleştirme) ve başlatır.

Not: Bu modül Windows'a göre yazıldı çünkü projenizde os.startfile,
shutdown /s /t 0 gibi Windows'a özgü çağrılar var. Mac/Linux için
alternatif kısımlar yorum satırlarında belirtildi.
"""

import os
import json
import platform
import subprocess
import difflib

try:
    import winreg
except ImportError:
    winreg = None

CACHE_DOSYASI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uygulamalar.json")

# Başlat menüsünde kısayolların bulunduğu standart klasörler
BASLAT_MENU_YOLLARI = [
    os.path.join(os.environ.get("PROGRAMDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
    os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"),
]


def _lnk_hedefini_coz(lnk_yolu):
    """.lnk kısayolunun gerçek hedef .exe yolunu döndürür."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        kisayol = shell.CreateShortCut(lnk_yolu)
        return kisayol.Targetpath
    except Exception:
        return None


def _app_paths_registry_tara():
    """HKLM/HKCU ...\\App Paths altında kayıtlı programları döndürür (Chrome, Code.exe vb. çoğu burada kayıtlıdır)."""
    sonuc = {}
    if winreg is None:
        return sonuc
    kok_yol = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
    for kok in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(kok, kok_yol) as anahtar:
                i = 0
                while True:
                    try:
                        alt_ad = winreg.EnumKey(anahtar, i)
                        i += 1
                        with winreg.OpenKey(anahtar, alt_ad) as alt_anahtar:
                            deger, _ = winreg.QueryValueEx(alt_anahtar, None)
                            isim = os.path.splitext(alt_ad)[0]
                            sonuc[isim.lower()] = deger
                    except OSError:
                        break
        except FileNotFoundError:
            continue
    return sonuc


def uygulama_listesini_tara():
    """Başlat menüsü + registry taraması yapıp {isim: yol} sözlüğü oluşturur ve json'a yazar."""
    sonuc = {}

    # 1) Registry (App Paths) - en güvenilir kaynak
    sonuc.update(_app_paths_registry_tara())

    # 2) Başlat menüsü kısayolları (.lnk)
    for klasor in BASLAT_MENU_YOLLARI:
        if not klasor or not os.path.isdir(klasor):
            continue
        for kok, _, dosyalar in os.walk(klasor):
            for dosya in dosyalar:
                if dosya.lower().endswith(".lnk"):
                    isim = os.path.splitext(dosya)[0].lower()
                    tam_yol = os.path.join(kok, dosya)
                    hedef = _lnk_hedefini_coz(tam_yol)
                    if hedef and os.path.exists(hedef):
                        sonuc[isim] = hedef

    with open(CACHE_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    return sonuc


def _listeyi_yukle(yenile=False):
    if not yenile and os.path.exists(CACHE_DOSYASI):
        with open(CACHE_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    return uygulama_listesini_tara()


def uygulama_ac(isim, esik=0.55):
    """Kullanıcının söylediği isme (örn. 'visual studio code', 'chrome') en yakın
    eşleşen uygulamayı bulur ve açar.
    Dönüş: (basarili: bool, mesaj: str)
    """
    liste = _listeyi_yukle()
    if not liste:
        return False, "Kurulu uygulama listesi bulunamadı, önce 'uygulamaları yenile' komutunu çalıştır."

    isim_norm = isim.lower().strip()

    # Tam veya alt-string eşleşme önce denenir (örn. "code" -> "visual studio code")
    for ad, yol in liste.items():
        if isim_norm == ad or isim_norm in ad or ad in isim_norm:
            return _calistir(ad, yol)

    # Bulunamazsa bulanık (fuzzy) eşleşme
    en_yakinlar = difflib.get_close_matches(isim_norm, liste.keys(), n=1, cutoff=esik)
    if en_yakinlar:
        ad = en_yakinlar[0]
        return _calistir(ad, liste[ad])

    return False, f"'{isim}' isimli bir uygulama bulamadım. Tarayıcı listesini yenilemeyi dene: 'uygulamaları yenile'."


def _calistir(ad, yol):
    try:
        executable = os.path.abspath(os.path.expanduser(str(yol)))
        if not os.path.isfile(executable) or os.path.splitext(executable)[1].lower() not in {".exe", ".com"}:
            return False, f"{ad} için güvenilir bir çalıştırılabilir dosya bulunamadı."
        process = subprocess.Popen([executable])
        # Popen başarısı tek başına yeterli değildir: süreç zaten sonlandıysa
        # kullanıcıya uygulamanın başlatıldığını söylemeyiz.
        if process.poll() is not None:
            return False, f"{ad} başlatıldı ancak süreç hemen sonlandı."
        return True, f"{ad} süreci başlatıldı ve çalışıyor olarak doğrulandı."
    except (OSError, ValueError) as exc:
        return False, f"{ad} başlatılamadı: {type(exc).__name__}"
