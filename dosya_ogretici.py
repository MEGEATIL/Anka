# -*- coding: utf-8 -*-
"""
dosya_ogretici.py
------------------
Asistana dosya (pdf, docx, txt) yükleyip "öğretme" ve daha sonra o dosyayla
ilgili soru sorulduğunda cevap alma modülü.

Kurulum:
    pip install pypdf python-docx

Nasıl çalışır (özet):
1) dosyadan_ogren(dosya_yolu)  -> dosyayı okur, ~800 karakterlik parçalara böler,
   "dosya_parcalari" tablosuna kaydeder.
2) dosya_sorusu_cevapla(soru)  -> tüm parçalar içinde soruyla en çok kelime
   ortaklığı olan 3-4 parçayı bulur, bunları LLM'e (self.client) bağlam olarak
   verip cevap üretir. Embedding/vektör veritabanı YOK - basit ama işe yarayan
   bir yöntem. İleride istersen bunu embedding tabanlı arama ile değiştirebiliriz.
"""

import os
import re
import sqlite3
from datetime import datetime
from llm_yardimci import guvenli_tamamla

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

try:
    import docx  # python-docx
except ImportError:
    docx = None


def _tabloyu_hazirla(cursor, conn):
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dosya_parcalari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dosya_adi TEXT,
        parca_no INTEGER,
        icerik TEXT,
        tarih TEXT
    )
    """)
    conn.commit()


def _dosyadan_metin_cikar(dosya_yolu):
    """Dosya uzantısına göre ham metni çıkarır."""
    uzanti = os.path.splitext(dosya_yolu)[1].lower()

    if uzanti == ".pdf":
        if PdfReader is None:
            raise RuntimeError("pypdf kurulu değil: pip install pypdf")
        metin = ""
        reader = PdfReader(dosya_yolu)
        for sayfa in reader.pages:
            metin += (sayfa.extract_text() or "") + "\n"
        return metin

    elif uzanti == ".docx":
        if docx is None:
            raise RuntimeError("python-docx kurulu değil: pip install python-docx")
        d = docx.Document(dosya_yolu)
        return "\n".join(p.text for p in d.paragraphs)

    elif uzanti in (".txt", ".md", ".csv"):
        with open(dosya_yolu, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    else:
        raise RuntimeError(f"Desteklenmeyen dosya türü: {uzanti}")


def _parcala(metin, parca_uzunlugu=800, ortakl=100):
    """Uzun metni örtüşmeli parçalara böler (bağlamı koparmamak için ortak_uzunluk kadar üst üste biner)."""
    metin = re.sub(r"\s+", " ", metin).strip()
    parcalar = []
    i = 0
    while i < len(metin):
        parcalar.append(metin[i:i + parca_uzunlugu])
        i += parca_uzunlugu - ortakl
    return [p for p in parcalar if p.strip()]


def dosyadan_ogren(cursor, conn, dosya_yolu):
    """Dosyayı okur, parçalara böler ve veritabanına kaydeder.
    Dönüş: (basarili: bool, mesaj: str)
    """
    _tabloyu_hazirla(cursor, conn)
    try:
        metin = _dosyadan_metin_cikar(dosya_yolu)
    except (OSError, ValueError, RuntimeError):
        return False, "Dosya okunamadı veya dosya biçimi desteklenmiyor."
    except Exception:
        # Harici PDF/DOCX ayrıştırıcılarının farklı istisnalarını teknik
        # ayrıntı sızdırmadan kullanıcıya anlaşılır şekilde bildir.
        return False, "Dosya ayrıştırılamadı; dosya bozuk olabilir."

    if not metin or not metin.strip():
        return False, "Dosyadan metin çıkarılamadı (taranmış görsel PDF olabilir, OCR gerekebilir)."

    parcalar = _parcala(metin)
    dosya_adi = os.path.basename(dosya_yolu)

    # Aynı dosya tekrar yüklenirse eski parçaları temizle (güncel kalsın)
    cursor.execute("DELETE FROM dosya_parcalari WHERE dosya_adi = ?", (dosya_adi,))

    simdi = datetime.now().isoformat()
    for i, parca in enumerate(parcalar):
        cursor.execute(
            "INSERT INTO dosya_parcalari (dosya_adi, parca_no, icerik, tarih) VALUES (?, ?, ?, ?)",
            (dosya_adi, i, parca, simdi)
        )
    conn.commit()
    return True, f"'{dosya_adi}' öğrenildi ({len(parcalar)} parça çıkarıldı). Artık bu dosyayla ilgili soru sorabilirsin."


def _en_alakali_parcalari_bul(cursor, soru, dosya_adi=None, top_n=4):
    """Basit kelime-ortaklığı skoru ile en alakalı parçaları döndürür."""
    if dosya_adi:
        cursor.execute("SELECT dosya_adi, parca_no, icerik FROM dosya_parcalari WHERE dosya_adi = ?", (dosya_adi,))
    else:
        cursor.execute("SELECT dosya_adi, parca_no, icerik FROM dosya_parcalari")

    satirlar = cursor.fetchall()
    if not satirlar:
        return []

    soru_kelimeleri = set(re.findall(r"\w+", soru.lower()))
    skorlu = []
    for d_adi, parca_no, icerik in satirlar:
        icerik_kelimeleri = set(re.findall(r"\w+", icerik.lower()))
        ortak = len(soru_kelimeleri & icerik_kelimeleri)
        if ortak > 0:
            skorlu.append((ortak, d_adi, parca_no, icerik))

    skorlu.sort(key=lambda x: x[0], reverse=True)
    return skorlu[:top_n]


def _cumlelere_ayir(metin):
    """Metni cümlelere böler; PDF çıkarımından kalan tekil harf/bullet
    kırıntılarını (örn. başta kalan yalnız 'b' karakteri) temizler."""
    parcalar = re.split(r"(?<=[.!?])\s+", metin.strip())
    temiz = []
    for p in parcalar:
        p = p.strip()
        # Başta kalan tek harflik bullet kırıntısını temizle (örn. "b Canlılar...")
        p = re.sub(r"^[^\wşçöğüıİŞÇÖĞÜ]{0,3}\b[a-zA-Z]\b\s+", "", p)
        if p:
            temiz.append(p)
    return temiz


def _en_alakali_cumleyi_bul(parca_metni, soru, top_n=2):
    """Bir parça içinden soruyla en çok kelime ortaklığı olan 1-2 cümleyi
    döndürür. LLM olmadan da kısa/net cevap vermek için kullanılır."""
    soru_kelimeleri = set(re.findall(r"\w+", soru.lower()))
    cumleler = _cumlelere_ayir(parca_metni)
    if not cumleler:
        return None

    skorlu = []
    for cumle in cumleler:
        cumle_kelimeleri = set(re.findall(r"\w+", cumle.lower()))
        ortak = len(soru_kelimeleri & cumle_kelimeleri)
        if ortak > 0:
            skorlu.append((ortak, cumle))

    if not skorlu:
        return cumleler[0]

    skorlu.sort(key=lambda x: x[0], reverse=True)
    secilenler = [c for _, c in skorlu[:top_n]]
    return " ".join(secilenler)



def dosya_sorusu_cevapla(cursor, client, soru, dosya_adi=None, model=None):
    """Yüklenmiş dosyalardan bağlam bulup soruyu yanıtlar.
    `client` -> asistanın zaten kullandığı OpenAI uyumlu client (self.client).
    `client` None ise (LLM bağlantısı yoksa) en alakalı ham metin parçası
    doğrudan döndürülür - böylece HF_TOKEN ayarlanmamış olsa bile dosya
    soruları tamamen cevapsız kalmaz.
    Dönüş: cevap metni (str)
    """
    parcalar = _en_alakali_parcalari_bul(cursor, soru, dosya_adi=dosya_adi)
    if not parcalar:
        return "Bu konuda öğretilmiş bir dosya bulamadım. Önce ilgili dosyayı bana yükleyip öğretmen gerekiyor."

    baglam = "\n---\n".join(p[3] for p in parcalar)
    kaynaklar = ", ".join(sorted(set(p[1] for p in parcalar)))

    if not client:
        kisa_cevap = _en_alakali_cumleyi_bul(parcalar[0][3], soru)
        if not kisa_cevap:
            kisa_cevap = parcalar[0][3].strip()
        return f"{kisa_cevap}\n\n(Kaynak: {kaynaklar})"

    prompt = (
        "Aşağıda kullanıcının yüklediği dosyalardan alınmış metin parçaları var. "
        "Sadece bu parçalardaki bilgiye dayanarak soruyu Türkçe, TEK CÜMLEYLE, "
        "çok kısa ve net cevapla (gereksiz giriş/tekrar yapma, doğrudan tanım/cevabı ver). "
        "Eğer cevap bu parçalarda yoksa 'Dosyada bu bilgiyi bulamadım' de.\n\n"
        f"METIN PARÇALARI:\n{baglam}\n\nSORU: {soru}"
    )

    try:
        cevap, _kullanilan_model = guvenli_tamamla(
            client, [{"role": "user", "content": prompt}], tercih_edilen_model=model
        )
        return f"{cevap}\n\n(Kaynak: {kaynaklar})"
    except Exception:
        # LLM çağrısı başarısız olursa ham parçaya değil, kısa cümleye düş.
        kisa_cevap = _en_alakali_cumleyi_bul(parcalar[0][3], soru)
        if not kisa_cevap:
            kisa_cevap = parcalar[0][3].strip()
        return f"{kisa_cevap}\n\n(Kaynak: {kaynaklar})"
