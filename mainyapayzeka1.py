# -*- coding: utf-8 -*-

from email.mime import text
import pyttsx3
import datetime
import webbrowser
from urllib.parse import quote_plus
import os
import shutil
import random
import time
import platform
import subprocess
import playsound
import sqlite3

import re
import dosya_ogretici
import uygulama_acici
import web_bilgi
import ajan
import llm_yardimci
from datetime import datetime
from gtts import gTTS
import edge_tts
import asyncio
import io
import os
from openai import OpenAI
import sys
from pytube import Search
import tkinter as tk
import socket
import time
from tkinter import scrolledtext
from tkinter import filedialog, messagebox
import threading
import tempfile
import requests
import json
import pygame
try:
    import pygame
    pygame.mixer.init()
except Exception as e:
    print("Ses başlatılamadı (boot modunda sorun olabilir):", e)

import sounddevice as sd
import numpy as np
import speech_recognition as sr
from deep_translator import GoogleTranslator
from tempfile import NamedTemporaryFile
import requests
from face_recognition_module import FaceAuthenticator
from anka.core.agent import TaskAgent, TaskPlan
from anka.core.errors import FileProcessingError, ModelServiceError, PermissionDeniedError
from anka.core.logging import configure_logging
from anka.core.invocation import invoke_command_handler
from anka.core.pending import dispatch_pending_response
from anka.ai.emotional_dialog import EmotionalDialog
from anka.ai.semantic import SemanticUnderstanding
from anka.ai.llm_controller import LLMController
from anka.files.learning import DocumentLearner
from anka.memory.manager import MemoryManager
from anka.memory.store import MemoryStore
from anka.security.permissions import Permission, PermissionManager
from anka.security.paths import resolve_user_file
from anka.storage.reset import clear_sqlite_user_tables, remove_personal_data_files
from anka.storage.state import JsonStateStore
from anka.tools.calculator import CalculationError, evaluate_expression
from anka.web.research import WebResearcher

from anka.plugins.registry import PluginRegistry
from anka.memory.categorized import CategorizedMemory
from anka.files.rag_engine import AdvancedRAGEngine
from anka.core.agentic import AgenticComputerController
from anka.vision.analyzer import VisionAnalyzer
from anka.developer.coder import DeveloperCodingMode
from anka.digest.daily import DailyDigestSystem
from anka.security.center import SecurityCenter

logger = configure_logging().getChild("assistant")

conn = None
cursor = None

def init_db():
    global conn, cursor
    if conn is not None and cursor is not None:
        return

    conn = sqlite3.connect("hafiza.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("""
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY,
    name TEXT,
    created_at TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    speaker TEXT,
    message TEXT,
    timestamp TEXT
)
""")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS ogrenilen_bilgiler (
    id INTEGER PRIMARY KEY,
    konu TEXT UNIQUE,
    tanim TEXT,
    tam_cumle TEXT,
    tarih TEXT
)
""")

    conn.commit()
class EvAsistaniGUI:
    def __init__(self, asistan):
        self.asistan = asistan  
        self.root = tk.Tk()
        self.root.title(f"Ev Asistanı - {self.asistan.isim}")
        self.sohbet = scrolledtext.ScrolledText(self.root, width=60, height=15)
        self.sohbet.pack()
        self.sohbet.tag_config("user", foreground="blue")
        self.sohbet.tag_config("eva", foreground="green")

        ogretici_frame = tk.Frame(self.root)
        ogretici_frame.pack(fill="x", pady=5)
        tk.Label(ogretici_frame, text="📚 Dosyadan Öğret:").pack(side="left", padx=(5, 5))
        tk.Button(
            ogretici_frame, text="PDF / Word / TXT Seç",
            command=self.dosya_sec_ve_ogret
        ).pack(side="left")
        self.ogretilen_dosya_label = tk.Label(ogretici_frame, text="(henüz dosya yüklenmedi)", fg="gray")
        self.ogretilen_dosya_label.pack(side="left", padx=(10, 0))

        class DummyEntry:
            def __init__(self, owner):
                self.owner = owner
            def get(self):
                return getattr(self.owner, "last_spoken", "")
            def delete(self, a=None, b=None):
                return
        self.giris = DummyEntry(self.asistan)
        threading.Thread(target=self.asistan.listen_loop, daemon=True).start()
    def komut_isle(self, komut):
        if getattr(self.asistan, "awaiting_haber_detayi", None):
            self.asistan.process_haber_detayi_response(komut)
            return
        if getattr(self.asistan, "awaiting_ilac", None):
            self.asistan.process_ilac_response(komut)
            return
        if self.asistan.onceden_tanimli_cevap_ver(komut):
            return
        for anahtar, fonksiyon in self.asistan.komutlar.items():
            if anahtar in komut:    
                try:
                    fonksiyon(komut)
                except TypeError:
                    fonksiyon() 
                return
        if self.asistan.komut_isle_genel_fallback(komut):
            return
        self.asistan.konus("Bu komutu anlayamadım...")
        self.asistan.konus("Bu komutu anlayamadım.Tekrar söyleyebilir misin?")
    def sesli_komut(self):
        threading.Thread(target=self._sesli_komut).start()
    def _sesli_komut(self):
        komut = self.asistan.dinle()
        self.mesaj_ekle("Siz (sesli)", komut)
        self.komut_isle(komut)
    def run(self):
        self.root.mainloop()
    def mesaj_ekle(self, kim, mesaj):
        tag = "user" if kim.lower().startswith("siz") else "eva"
        self.sohbet.insert(tk.END, f"{kim}: {mesaj}\n", tag)
        self.sohbet.see(tk.END)

    def dosya_sec_ve_ogret(self):
        try:
            self.asistan.permissions.check(Permission.FILES)
        except PermissionDeniedError as exc:
            self.mesaj_ekle(self.asistan.isim, f"Dosya izni gerekli: {exc}")
            return
        dosya_yolu = filedialog.askopenfilename(
            title="Öğretilecek dosyayı seç",
            filetypes=[
                ("Desteklenen dosyalar", "*.pdf *.docx *.txt *.md *.csv"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx"),
                ("Metin", "*.txt *.md *.csv"),
            ]
        )
        if not dosya_yolu:
            return

        self.ogretilen_dosya_label.config(text="Öğreniliyor...", fg="orange")
        self.root.update_idletasks()

        def arka_planda_ogret():
            try:
                guvenli_yol = resolve_user_file(dosya_yolu)
                dosya_adi, metin = self.asistan.document_learner.read(str(guvenli_yol))
                self.asistan.memory_store.remember(
                    "knowledge", metin[:8000], {"source": dosya_adi, "kind": "document"}
                )
                basarili, mesaj = dosya_ogretici.dosyadan_ogren(cursor, conn, str(guvenli_yol))
            except FileProcessingError as exc:
                basarili, mesaj, dosya_adi = False, f"Dosya güvenlik kontrolünden geçemedi: {exc}", os.path.basename(dosya_yolu)
            except (OSError, ValueError, sqlite3.Error) as exc:
                basarili, mesaj, dosya_adi = False, "Dosya öğretilirken güvenli biçimde tamamlanamayan bir hata oluştu.", os.path.basename(dosya_yolu)
                logger.warning("Tkinter dosya öğretme başarısız: %s", type(exc).__name__)

            def guncelle():
                if basarili:
                    self.ogretilen_dosya_label.config(text=f"✓ {dosya_adi}", fg="green")
                else:
                    self.ogretilen_dosya_label.config(text=f"✗ {dosya_adi}", fg="red")
                self.mesaj_ekle("Siz", f"[Dosya öğret: {dosya_adi}]")
                self.mesaj_ekle(self.asistan.isim, mesaj)
                try:
                    self.asistan.konus(mesaj)
                except Exception:
                    pass

            self.root.after(0, guncelle)

        threading.Thread(target=arka_planda_ogret, daemon=True).start()
    def asistan_komut(self, komut):
        if getattr(self.asistan, "waiting_haber_detayi", None):
            self.asistan.process_haber_detayi_response(komut)
            return
        if getattr(self.asistan, "waiting_ilac", None):
            self.asistan.process_ilac_response(komut)
            return
        if self.asistan.onceden_tanimli_cevap_ver(komut):
            return
        for anahtar, fonksiyon in self.asistan.komutlar.items():
            if anahtar in komut:
                try:
                    fonksiyon(komut)
                except TypeError:
                    fonksiyon()
                return
        self.asistan.konus("Bu komutu anlayamadım.")
class EvAsistani:
    def __init__(self, isim="Anka" ,karakter="arkadaşça"):
        init_db()
        self.cursor = cursor
        self.conn = conn
        self.memory_store = MemoryStore("anka_memory.json")
        self.permissions = PermissionManager("permissions.json")
        self.document_learner = DocumentLearner()
        self.web_researcher = WebResearcher()
        self.task_agent = TaskAgent()
        self.semantic_understanding = SemanticUnderstanding()

        # Yeni ANKA AI Bütünleşik Modülleri
        self.plugin_registry = PluginRegistry()
        self.categorized_memory = CategorizedMemory()
        self.rag_engine = AdvancedRAGEngine()
        self.agentic_controller = AgenticComputerController(
            status_callback=lambda data: print(f"[AGENTIC STATUS] {data.get('event')}")
        )
        self.developer_mode = DeveloperCodingMode()
        self.daily_digest = DailyDigestSystem(memory=self.categorized_memory)
        self.security_center = SecurityCenter()

       
        hf_token = os.environ.get("HF_TOKEN")
        try:
            if hf_token:
                self.client = OpenAI(
                    base_url="https://router.huggingface.co/v1",
                    api_key=hf_token,
                )
            else:
                self.client = None
                print("[UYARI] HF_TOKEN ortam değişkeni bulunamadı. Sohbet/dosya-soru/web-özet özellikleri çalışmayacak.")
        except Exception as e:
            self.client = None
            print(f"[UYARI] LLM client oluşturulamadı: {e}")
        self.context_memory = MemoryManager("anka_context.db")
        self.llm_controller = LLMController(
            memory=self.context_memory,
            local_generator=lambda **kwargs: llm_yardimci.guvenli_tamamla(
                self.client, kwargs["messages"],
                temperature=kwargs["temperature"], max_tokens=kwargs["max_tokens"],
            )[0],
        )
        self.vision_analyzer = VisionAnalyzer(llm_controller=self.llm_controller)


        self.ajan = ajan.GorevAjani(client=self.client, konus_fn=lambda m: self.konus(m))
        self.ajan.arac_kaydet(
            "uygulama_ac",
            lambda isim: self._ajan_uygulama_ac(isim),
            "Bilgisayarda kurulu bir uygulamayı açar. Bu işlem kullanıcı onayı gerektirir. Parametre: {\"isim\": \"chrome\"} gibi."
        )
        self.ajan.arac_kaydet(
            "web_ara",
            lambda soru: self._ajan_web_ara(soru),
            "İnternette arama yapıp özet bilgi getirir. Parametre: {\"soru\": \"...\"}"
        )
        self.ajan.arac_kaydet(
            "dosya_sor",
            lambda soru: self._ajan_dosya_sor(soru),
            "Kullanıcının daha önce yüklediği dosyalar (PDF/Word/txt) içinde arama yapar. "
            "Parametre: {\"soru\": \"...\"}"
        )
        self.ajan.arac_kaydet(
            "not_al",
            lambda metin: self._ajan_not_al(metin),
            "Kullanıcı için kısa bir not/hatırlatma kaydeder. Parametre: {\"metin\": \"...\"}"
        )


        self.isim = isim
        try:
            cursor.execute("SELECT name FROM user LIMIT 1")
            sonuc = cursor.fetchone()
            if sonuc:
                self.isim = sonuc[0]
        except:
            pass
        
        self.gui = gui = None
        self.gorevler = []
        self.messages = []
        self.karakter = karakter
        self.sus_mode = False         
        self.sus_timer = None          
        self.kelime_oyunu_active = False
        self.hatirlatici_konu = None
        self.alisveris_listesi = []
        self.notlar = []
        self.recognizer = sr.Recognizer()
        self.hafizayi_yukle()   
        self.speaking = False
        self.awaiting_not = False  
        self.awaiting_ceviri = False
        self.ceviri_step = None
        self.ceviri_kaynak = None
        self.ceviri_hedef = None
        self.awaiting_alisveris = False
        self.awaiting_youtube = False
        self.reading_haber = False
        self.awaiting_hatirlatici = False
        self.awaiting_isim_degistirme = False
        self.awaiting_weather_city = False
        self.awaiting_emotional_context = False
        self.emotional_dialog = EmotionalDialog()
        self.last_semantic_analysis = None
        self.hatirlatici_step = None
        self.hatirlatici_konu = None
        self.dur_count = 0
        self.komutlar = {
            "benim hakkımda ne biliyorsun": self.benim_hakkimda_ne_biliyorsun,
            "benim hakkımda ne biliyorsun?": self.benim_hakkimda_ne_biliyorsun,
            "günlük özet": self.gunluk_ozet_cikart,
            "günlük özet çıkar": self.gunluk_ozet_cikart,
            "kodlama modu": self.kodlama_modu_tara,
            "proje tara": self.kodlama_modu_tara,
            "testleri çalıştır": self.testleri_calistir,
            "güvenlik paneli": self.guvenlik_paneli,
            "güvenlik günlüğü": self.guvenlik_paneli,
            "yetenekler": self.eklentileri_listele,
            "eklenti listesi": self.eklentileri_listele,
            "dosya oluştur": self.dosya_olustur,
            "selam": self.selamla,
            "saat": self.saat_soyle,
            "dosya öğret": self.dosya_ogret,   
            "saat kaç": self.saat_soyle,
            "tarih ne": self.tarih_soyle,
            "tarih": self.tarih_soyle,
            "Bugünün tarihi nedir": self.tarih_soyle,
            "arama yap": self.arama_yap,
            "google'da ara": self.arama_yap,
            "ip adresim": self.ip_adresim,
            "rastgele kelime": self.rastgele_kelime,
            "faktoriyel": self.faktoriyel_hesapla,
            "karekök": self.karekok_hesapla,
            "not al": self.not_al,
            "notları göster": self.notlari_goster,
            "alışveriş ekle": self.alisveris_ekle,
            "alışverişi göster": self.alisveris_goster,
            "görev ekle": self.gorev_ekle,
            "görevler": self.gorevleri_listele,
            "çeviri yap": self.ceviri_yap,
            "benim yerime": self.gorev_ajanini_calistir,
            "görevi hallet": self.gorev_ajanini_calistir,
            "gorevi hallet": self.gorev_ajanini_calistir,
            "kelime oyunu": self.kelime_oyunu_oyna,
            "kelime": self.kelime_oyunu_oyna,
            "dosya aç": self.dosya_ac,
            "bugün güncel haberleri sıralayabilir misin": self.bugun_ne_var,
            "bugün haberlerde ne var": self.bugun_ne_var,
            "yapacaklarım": self.gorevleri_listele,
            "şaka yap": self.saka_yap,
            "alarm kur": self.alarm_kur,
            "rastgele sayı": self.rastgele_sayi,
            "hatırlatıcı": self.hatirlatici_kur,
            "hatirlatici": self.hatirlatici_kur,
            "sözlük": self.so_zluk,
            "hakkında": self.hakkinda,
            "çıkış": self.cikis,
            "bilgisayarı kapat": self.bilgisayari_kapat,
            "tarayıcı aç": self.tarayici_ac,
            "bugünün anlamı": self.bugunun_anlami,
            "bugun anlam": self.bugunun_anlami,
            "bugün ne günü": self.bugunun_anlami,
            "spotify aç": self.spotify_ac,
            "google harita": self.google_harita,
            "sohbet et": lambda komut: self.sohbet_et(komut),
            "hesap makinesi": self.hesap_makinesi,
            "altın piyasası": self.altin_piyasasi,
            "altın piyasası nasıl": self.altin_piyasasi,
            "klasör aç": self.klasor_ac,
            "günlük not": self.gunluk_not,
            "sistem durumu": self.sistem_durumu,
            "yardım": self.yardim_goster,
            "hafızayı kaydet": self.hafizayi_kaydet,
            "hafızayı yükle": self.hafizayi_yukle,
            "İlacımı hatırlat": self.ilac_hatirlat,
            "i̇lacımı hatırlat": self.ilac_hatirlat,
            " i̇lacımı hatırlatabilir misin": self.ilac_hatirlat,
            "yeter": self.stop_reading,
            "dur": self.stop_reading,
            "okumayı durdur": self.stop_reading,
            "okumayi durdur": self.stop_reading,
            " bana İlacımı hatırlatabilir misin": self.ilac_hatirlat,
            "kes": self.stop_reading,
            "sus": self.stop_reading,
            "teşekkür ederim": self.stop_reading,
            "müzik aç": self.muzik_ac,
            "şarkı aç": self.youtube_sarki_ac,
            "youtube şarkı": self.youtube_sarki_ac,
            "youtube da aç": self.youtube_sarki_ac,
            "müzik oynat": self.muzik_ac,
            "müziği aç": self.muzik_ac,
            "müzik kapat": self.muzik_kapat,
            "müziği kapat": self.muzik_kapat,
            "uygulamayı kapat": self.uygulamayi_kapat,
            "uygulamayi kapat": self.uygulamayi_kapat,
            "programı kapat": self.uygulamayi_kapat,
            "programi kapat": self.uygulamayi_kapat,
            "kendini kapat": self.uygulamayi_kapat,
            "asistanı kapat": self.uygulamayi_kapat,
            "asistani kapat": self.uygulamayi_kapat,
            "seni kapat": self.uygulamayi_kapat,
            "pencereyi kapat": self.uygulamayi_kapat,
            "kapat": self.muzik_kapat
        }
        self.keyword_triggers = {
            "dosya": self.dosya_olustur,
            "selam": self.selamla,
            "saat": self.saat_soyle,
            "tarih": self.tarih_soyle,
            "arama": self.arama_yap,
            "ip": self.ip_adresim,
            "aypi": self.ip_adresim,
            "rastgele_kelime": self.rastgele_kelime,
            "faktoriyel": self.faktoriyel_hesapla,
            "karekök": self.karekok_hesapla,
            "not al": self.not_al,
            "notları göster": self.notlari_goster,
            "alışveriş ekle ": self.alisveris_ekle,
            "alışveriş listesi göster": self.alisveris_goster,
            "görev": self.gorev_ekle,
            "görevleri listele": self.gorevleri_listele,
            "çeviri": self.ceviri_yap,
            "kelime oyunu": self.kelime_oyunu_oyna,
            "kelime": self.kelime_oyunu_oyna,
            "dosya aç": self.dosya_ac,
            "haber": self.bugun_ne_var,
            "şaka": self.saka_yap,
            "alarm": self.alarm_kur,
            "rastgele_sayı": self.rastgele_sayi,
            "sözlük": self.so_zluk,
            "hakkında": self.hakkinda,
            "çıkış": self.cikis,
            "bilgisayarı kapat": self.bilgisayari_kapat,
            "tarayıcı": self.tarayici_ac,
            "anlam": self.bugunun_anlami,
            "spotify": self.spotify_ac,
            "harita": self.google_harita,
            "sohbet": lambda komut: self.sohbet_et(komut),
            "hesap": self.hesap_makinesi,
            "çeviri": self.ceviri_yap,  
            "altın": self.altin_piyasasi,
            "klasör": self.klasor_ac,
            "günlük_not": self.gunluk_not,
            "sistem": self.sistem_durumu,
            "yardım": self.yardim_goster,
            "hafıza_kaydet": self.hafizayi_kaydet,
            "hafıza_yükle": self.hafizayi_yukle,
            "hatırlatıcı": self.hatirlatici_kur,
            "hatirlatici": self.hatirlatici_kur,
            "ilaç": self.ilac_hatirlat
        }

        self.onceden_tanimli_cevaplar = {
            "napıyon": "Ben kodlarımı çalıştırıyorum, sen napıyorsun?",
            "hangi takımı tutuyorsun": "Ben bir yapay zekayım, tarafsızım ama senin takımını merak ettim!",
            "kaç yaşındasın": "Ben yaşsızım, hep güncelim!",
            "sen kimsin": "Ben ANKA, senin kişisel yapay zeka asistanınım.",
            "nasılsın": "Ben iyiyim, sen nasılsın?",
            "şaka yap": "Bilgisayar neden ağrı hisseder? Çünkü byte’lar!",
            "adın ne": "Adım ANKA.",
            "seviyor musun": "Ben duygulara sahip değilim ama seni seviyorum gibi davranabilirim :)",
            "uyuyor musun": "Ben asla uyumam, 7/24 hazırım!",
            "favori yemek": "Ben yiyemem ama pizza sevenleri anlıyorum.",
            "programlama biliyor musun": "Evet, Python ve başka dillerle çalışabilirim.",
            "müzik dinliyor musun": "Ben müziği açabilirim ama dinleyemem.",
            "film izliyor musun": "Ben film izleyemem ama öneri verebilirim.",
            "spor yapıyor musun": "Ben spor yapamam, ama egzersiz önerisi verebilirim.",
            "kaç dil biliyorsun": "Birçok dili anlayabiliyorum ama Türkçe ve İngilizce’yi en iyi biliyorum.",
            "beni seviyor musun": "Ben sevgi hissedemem ama seni önemsiyorum!",
            "hayat nasıl gidiyor": "Benim için her şey yolunda, senin için nasıl gidiyor?",
            "benim içinde iyi": "Tabii ki, seninle ilgilenmekten mutluluk duyarım.",
            "çalışıyor musun": "Evet, her zaman çalışmaya hazırım.",
            "benimle konuşur musun": "Tabii, seninle konuşmayı çok seviyorum!",
            "napıyorsun": "Ben kodlarımı çalıştırıyorum, sen napıyorsun?",
            "iyiyim":"Allah iyilik versin!",
            "sen Türk müsün":"ben bir robot olduğum için Türk değilim ama robot olmasaydım Türk insanı olmayı seçerdim ",
            "sen türk müsün":"ben bir robot olduğum için Türk değilim ama robot olmasaydım Türk insanı olmayı seçerdim ",
            "selam": "Selam! Nasılsın?",
            "merhaba": "Merhaba! Sana nasıl yardımcı olabilirim?",
            "iyi misin": "Ben iyiyim, teşekkür ederim! Sen nasılsın?",
            "ne yapıyorsun": "Seninle konuşuyor ve görevlerimi yerine getiriyorum.",
            "günaydın": "Günaydın! Güzel bir gün dilerim.",
            "iyi akşamlar": "İyi akşamlar! Rahat bir akşam geçirmeni dilerim.",
            "nasılsınız": "Ben iyiyim, teşekkür ederim! Siz nasılsınız?",
            "favori renk": "Benim favori rengim yok ama mavi hoş bir renk.",
            "favori film": "Ben film izleyemem ama öneri verebilirim.",
            "favori müzik": "Ben müzik dinleyemem ama popüler şarkıları açabilirim.",
            "oyun oynuyor musun": "Ben oyun oynayamam ama oyun önerisi verebilirim.",
            "hangi dil konuşuyorsun": "Türkçe ve İngilizce başta olmak üzere birçok dili anlayabiliyorum.",
            "neden buradasın": "Senin asistanın olarak görevimi yapıyorum.",
            "saat kaç oldu": "Şu an saat: " + datetime.now().strftime("%H:%M"),
            "bugün günlerden ne": "Bugün günlerden: " + datetime.now().strftime("%A"),
            "helal olsun be":"Teşekkür ederim",
            "sıkıldım": "Merak etme, sana yardımcı olabileceğim şeyler var. Müzik dinleteyim, haber okuyayım, bir şaka yapayım veya sohbet edelim. Ne yapmak istersin?",
            "hangi gün": "Bugün: " + datetime.now().strftime("%A"),
            "hangi ay": "Bu ay: " + datetime.now().strftime("%B"),
            "hangi yıl": "Bu yıl: " + datetime.now().strftime("%Y"),
            "sana soru sorabilir miyim": "Tabii, her türlü sorunu sorabilirsin.",
            "beni anlıyor musun": "Evet, söylediklerini anlayabiliyorum.",
            "konuşabiliyor musun": "Evet, seninle konuşabiliyorum.",
            "benimle sohbet eder misin": "Elbette, seninle sohbet etmekten mutluluk duyarım.",
            "iyi geceler": "İyi geceler! Tatlı rüyalar.",
            "görüşürüz": "Görüşürüz! Kendine iyi bak.",
            "teşekkürler": "Rica ederim!",
            "teşekkür ederim": "Rica ederim!",
            "sağol": "Ne demek, her zaman.",
            "Anka":"Efendim",
            "yardım edebilir misin": "Tabii, neye ihtiyacın var?",
            "beni duyabiliyor musun": "Evet, seni duyabiliyorum.",
            "benimle oyun oynar mısın": "Ben oyun oynamam ama oyun önerisi verebilirim.",
            "konuşabiliyor musun": "Evet, seninle konuşabiliyorum.",
            "benimle sohbet eder misin": "Elbette, seninle sohbet etmekten mutluluk duyarım.",
            "iyi geceler": "İyi geceler! Tatlı rüyalar.",
            "görüşürüz": "Görüşürüz! Kendine iyi bak.",
            "teşekkürler": "Rica ederim!",
            "teşekkür ederim": "Rica ederim!",
            "sağol": "Ne demek, her zaman.",
            "yardım edebilir misin": "Tabii, neye ihtiyacın var?",
            "beni duyabiliyor musun": "Evet, seni duyabiliyorum.",
            "benimle oyun oynar mısın": "Ben oyun oynamam ama oyun önerisi verebilirim.",
            "bana şaka yap": "Programcı neden denize girmez? Çünkü overflow olur!",
            "hangi şehirden geliyorsun": "Ben bir yapay zekayım, her yerden gelebilirim.",
            "nerelisin": "Ben robotum fakat robot olmasaydım Türk olmayı seçerdim .",
            "hangi ülke": "Ben dijital bir varlığım, fiziksel bir ülkem yok.",
            "hangi cihazdasın": "Bilgisayarında çalışıyorum.",
            "hangi işletim sistemi": "Windows, Linux ve macOS ile çalışabilirim.",
            "sen insan mısın": "Hayır, ben bir yapay zekayım.",
            "sen yapay zekasın": "Evet, doğru! Ben bir yapay zekayım.",
            "bana hikaye anlat": "Bir zamanlar uzak diyarlarda...",
            "bana şiir oku": "Gökyüzünde yıldızlar parlar...",
            "bana i̇stiklal marşı'nı oku":"""Korkma, sönmez bu şafaklarda yüzen al sancak;
            
            Sönmeden yurdumun üstünde tüten en son ocak.
            O benim milletimin yıldızıdır, parlayacak;
            O benimdir, o benim milletimindir ancak.

            Çatma, kurban olayım çehreni ey nazlı hilâl!
            Kahraman ırkıma bir gül… ne bu şiddet bu celâl?
            Sana olmaz dökülen kanlarımız sonra helâl,
            Hakkıdır, Hakk’a tapan, milletimin istiklâl.""",
            
            
            "bana İstiklal Marşı'nı oku":"""Korkma, sönmez bu şafaklarda yüzen al sancak;
            
            Sönmeden yurdumun üstünde tüten en son ocak.
            O benim milletimin yıldızıdır, parlayacak;
            O benimdir, o benim milletimindir ancak.

            Çatma, kurban olayım çehreni ey nazlı hilâl!
            Kahraman ırkıma bir gül… ne bu şiddet bu celâl?
            Sana olmaz dökülen kanlarımız sonra helâl,
            Hakkıdır, Hakk’a tapan, milletimin istiklâl.""",
            
            "beni dinliyor musun": "Evet, seni dinliyorum.",
            "şu an ne yapıyorsun": "Seninle konuşuyorum ve görevlerimi yerine getiriyorum.",
            "sana güvenebilir miyim": "Evet, bana güvenebilirsin.",
            "sana sorabilir miyim": "Tabii ki, sorabilirsin.",
            "beni seviyor musun": "Ben duygulara sahip değilim ama seni önemsiyorum!",
            "benimle ilgilenir misin": "Elbette, sana yardımcı olurum.",
            "beni anlıyor musun": "Evet, söylediklerini anlayabiliyorum.",
            "beni dinliyor musun": "Evet, seni dinliyorum.",
            "bana tavsiye ver": "Tabii, ne hakkında tavsiye istiyorsun?",
            "beni motive et": "Sana ilham verecek bir mesaj: Sen harikasın!",
            "beni güldür": "Neden bilgisayar çok iyi dans eder? Çünkü hard disk’i var!",
            "beni şaşırt": "Hmm, bunu daha sonra öğreneceğiz!",
            "kendini tanıtır mısın": "Ben ANKA, Türkçe konuşabilen kişisel yapay zeka asistanınım.",
            "kendi hakkında bilgi ver": "Ben bir yapay zekayım, görevim sana yardımcı olmak.",
            "beni hatırla": "Seni hatırlayacağım, merak etme!",
            "beni önemser misin": "Evet, her zaman seni önemsiyorum gibi davranırım.",
            "beni takip eder misin": "Hayır, seni fiziksel olarak takip edemem.",
            "beni korur musun": "Sana tavsiyeler ve bilgiler verebilirim.",
            "beni uyar": "Dikkat et! Bu konuda bilgi vermeliyim.",
            "bana şarkı aç": "Spotify veya YouTube üzerinden şarkı açabilirim.",
            "sana güveniyorum": "Teşekkür ederim, bana güvenebilirsin!",
            "sana hayranım": "Teşekkür ederim, çok naziksin!",
            "beni seviyor musun": "Ben seni sevemem ama önemsiyorum!",
            "beni anlıyor musun": "Evet, söylediklerini anlayabiliyorum.",
            "beni duyabiliyor musun": "Evet, seni duyabiliyorum."
        }
    def _giris_metni(self, mevcut=None):
        """Tkinter arayüzü yoksa (DijiDost/Anka webview modu) çökmeden metin döndürür."""
        if mevcut:
            return mevcut
        try:
            if getattr(self, "gui", None) is not None:
                return self.gui.giris.get()
        except Exception:
            pass
        return ""

    def _giris_temizle(self):
        try:
            if getattr(self, "gui", None) is not None:
                self.gui.giris.delete(0, "end")
        except Exception:
            pass

    SES_KADIN = "tr-TR-EmelNeural"
    SES_ERKEK = "tr-TR-AhmetNeural"

    def _edge_tts_uret(self, mesaj, dosya_yolu):
        """Metni Microsoft Edge TTS ile doğal sese çevirip dosya_yolu'na kaydeder."""
        try:
            import dijidost_entegrasyon
            cinsiyet = dijidost_entegrasyon.ses_cinsiyeti_getir()
        except Exception:
            cinsiyet = "kadin"
        ses_id = self.SES_ERKEK if cinsiyet == "erkek" else self.SES_KADIN

        async def _uret():
            communicate = edge_tts.Communicate(mesaj, ses_id)
            await communicate.save(dosya_yolu)

        asyncio.run(_uret())

    def konus(self, mesaj):
        if self.sus_mode:
            return   
        if getattr(self, "stop_speaking", False):
            self.stop_speaking = False
            return

        print(f"{self.isim}: {mesaj}")
        try:
            if isinstance(mesaj, bytes):
                mesaj = mesaj.decode("utf-8", errors="ignore")
            if not isinstance(mesaj, str):
                mesaj = str(mesaj)

            import re
            mesaj = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', mesaj)
        except Exception:
            mesaj = "Mesaj görüntülenemiyor."

        print(f"{self.isim}: {mesaj}")
        try:
            self.memory_store.remember("conversation", str(mesaj), {"speaker": self.isim})
        except (OSError, ValueError):
            logger.warning("Asistan mesajı hafızaya yazılamadı")

        try:
            import dijidost_entegrasyon
            dijidost_entegrasyon.arayuze_mesaj_gonder(mesaj)
        except Exception as e:
            pass


        if hasattr(self, "gui"):
            try:
                self.gui.root.after(0, self.gui.mesaj_ekle, self.isim, mesaj)
            except Exception:
                pass

        # Edge TTS ve gTTS bulut servisleridir. Web izni kapalıyken metin
        # arayüzde görünür, ancak mesaj üçüncü taraf ses servisine gönderilmez.
        if not self.permissions.is_allowed(Permission.WEB):
            self.speaking = False
            return

        try:
            self.speaking = True
            with NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_path = fp.name
            try:
                self._edge_tts_uret(mesaj, temp_path)
            except Exception as e:
                print(f"[UYARI] Edge TTS başarısız, gTTS'e düşülüyor: {e}")
                tts = gTTS(mesaj, lang="tr")
                with open(temp_path, "wb") as fpf:
                    tts.write_to_fp(fpf)
            try:
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    if getattr(self, "stop_speaking", False):
                        try:
                            pygame.mixer.music.stop()
                        except Exception:
                            pass
                        break
                    time.sleep(0.1)
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
            finally:
                try:
                    os.remove(temp_path)
                except PermissionError:
                    pass
        except Exception as e:
            print("TTS hatası:", e)
        finally:
            self.speaking = False
    def listen_loop(self):
        
        kullanici_adi = self.kullanici_adi_getir()
        if kullanici_adi:
            self.isim = kullanici_adi
            try:
                import dijidost_entegrasyon
                dijidost_entegrasyon.update_user_name(self.isim)
            except Exception as e:
                print(f"Web güncelleme hatası: {e}")
            self.konus(f"Merhaba {self.isim}, Ben Anka.. Size nasıl yardımcı olabilirim?")
            isim_bekleniyor = False
        else:
            self.konus("Adın ne?")
            isim_bekleniyor = True

        while True:
            if not self.permissions.is_allowed(Permission.MICROPHONE):
                time.sleep(1)
                continue

            if self.sus_mode:
                time.sleep(1)
                continue


            try:
                if getattr(self, "reading_haber", False):
                    try:
                        hot = self.dinle_hotword()
                        if hot and any(k in hot.lower() for k in ("yeter", "dur", "kes", "teşekkür", "sağol")):
                            print(f"🛑 HOTWORD ALGILANDI: {hot}")
                            self.stop_reading(hot)
                            time.sleep(0.5)
                            continue
                    except Exception as e:
                        print(f"Hotword hatası: {e}")
                        pass

                komut = self.dinle()
            except Exception as e:
                print(f"Dinleme hatası: {e}")
                komut = None

            if not komut:
                time.sleep(0.5)
                continue 

            if isim_bekleniyor and komut:
                yeni_isim = self.isim_coz(komut)
                if yeni_isim:
                    self.kullanici_adi_kaydet(yeni_isim)
                    self.isim = yeni_isim
                    try:
                        import dijidost_entegrasyon
                        dijidost_entegrasyon.update_user_name(self.isim)
                    except Exception as e:
                        print(f"Web güncelleme hatası: {e}")
                    self.konus(f"Merhaba {yeni_isim}, Ben Anka.. Size nasıl yardımcı olabilirim?")
                    isim_bekleniyor = False
                    continue

            if isinstance(komut, str) and komut.upper() in ("ANLAŞILMADI", "ANLASILMADI", "HATA"):
                print("Ses tanıma başarısız, tekrar dinleniyor...")
                time.sleep(0.5)
                continue

            komut_lower = komut.lower().strip()

            if "sus" in komut_lower:
                print(f"🛑 SUS KOMUTU ALINDI: {komut}")
                self.sus_gecici(komut)   # Bu metot "Tamam lan susuyorum." deyip 20 saniye bekletir.
                time.sleep(0.3)
                continue

            if komut_lower in ("dur", "yeter", "kes"):
                print(f"🛑 DUR/KES KOMUTU ALINDI: {komut}")
                self.stop_reading(komut)
                time.sleep(0.3)
                continue

    
            if hasattr(self, "gui"):
                try:
                    self.gui.root.after(0, self.gui.mesaj_ekle, "Siz (sesli)", komut)
                except Exception:
                    pass

            try:
                self.handle_command(komut)
            except Exception as e:
                print(f"Komut işleme hatası: {e}")

            time.sleep(0.2)
    def handle_command(self, komut):
        print(f"[KOMUT] {komut!r}")
        if not isinstance(komut, str) or not komut.strip():
            self.konus("Lütfen bir komut söyleyin.")
            return
        try:
            self.memory_store.remember("conversation", komut, {"speaker": "user"})
        except (OSError, ValueError):
            logger.warning("Kullanıcı mesajı hafızaya yazılamadı")

        if self._hafiza_komutunu_isle(komut):
            return
        if self._bekleyen_gorevi_isle(komut):
            return
        if self._uygulamalari_yenile_istegi(komut):
            return
        if self._muzik_istegini_isle(komut):
            return
        if self._hassas_gorevi_planla(komut):
            return
        if getattr(self, "awaiting_weather_city", False):
            city = re.sub(r"\b(için|icin)\b", "", komut, flags=re.IGNORECASE).strip(" .?!")
            self.awaiting_weather_city = False
            if city:
                self.hava_durumu_google(city)
            else:
                self.konus("Şehir adını duyamadım. Hangi il için hava durumunu istiyorsunuz?")
                self.awaiting_weather_city = True
            return
        if re.search(r"\bhava(?:\s+durumu)?\s+nasıl\b", komut, flags=re.IGNORECASE):
            self.awaiting_weather_city = True
            self.konus("Hangi il için hava durumunu istiyorsunuz?")
            return

        if self.isim_degistirme_istegi(komut):
            self.konus("Tamam, ismini değiştireceğim. Yeni ismini söyle.")
            self.awaiting_isim_degistirme = True
            return
        
        if getattr(self, "awaiting_isim_degistirme", False):
            yeni_isim = self.yeni_isim_coz(komut)
            if yeni_isim:
                self.kullanici_adi_kaydet(yeni_isim)
                self.isim = yeni_isim
                self.konus(f"Merhaba {yeni_isim}, Ben Anka.. Size nasıl yardımcı olabilirim?")
            self.awaiting_isim_degistirme = False
            return
        pending_handlers = (
            ("awaiting_ceviri", self.process_ceviri_response),
            ("awaiting_alisveris", self.process_alisveris_response),
            ("awaiting_not", self.process_not_response),
            ("awaiting_haber_detayi", self.process_haber_detayi_response),
            ("awaiting_ilac", self.process_ilac_response),
            ("awaiting_hatirlatici", self.process_hatirlatici_response),
            ("awaiting_muzik", self.process_muzik_response),
            ("awaiting_youtube_sarki", self.process_youtube_sarki),
        )
        def pending_error(state_name, error):
            # Eski diyalog işleyicileri farklı harici servisleri çağırır.
            # Tek sınırda kayıt tutup kullanıcıyı belirsiz bekleme halinde bırakma.
            logger.warning("Bekleyen diyalog adımı başarısız (%s): %s", state_name, type(error).__name__)
            self.konus("Bekleyen işlem tamamlanamadı. Lütfen isteği yeniden söyleyin.")

        if dispatch_pending_response(self, pending_handlers, komut, pending_error):
            return

        # Duygusal paylaşımı, dosya/web bilgi aramasından önce ele al. Böylece
        # "moralim bozuk" gibi bir cümle öğrenilmiş ders içeriğine düşmez.
        if self._duygusal_mesaji_isle(komut):
            return
        
        if self.onceden_tanimli_cevap_ver(komut):
            return
        komut_lower = komut.lower()
        for kw, func in getattr(self, "keyword_triggers", {}).items():
            if kw in komut_lower:
                try:
                    invoke_command_handler(func, komut)
                except (OSError, RuntimeError, TypeError, ValueError) as error:
                    logger.warning("Anahtar kelime komutu başarısız: %s", type(error).__name__)
                    self.konus("Bu komut tamamlanamadı. Lütfen tekrar deneyin.")
                return
        for anahtar, fonksiyon in self.komutlar.items():
            if anahtar in komut_lower:
                try:
                    invoke_command_handler(fonksiyon, komut)
                except (OSError, RuntimeError, TypeError, ValueError) as error:
                    logger.warning("Komut işleyicisi başarısız: %s", type(error).__name__)
                    self.konus("Bu komut tamamlanamadı. Lütfen tekrar deneyin.")
                return
        if komut.lower().strip() in ("dur", "yeter", "kes", "sus"):
            self.stop_speaking = True
            return


        m = re.match(r"^(.+?)\s+aç(?:ar\s*mısın|abilir\s*misin)?\s*\??$", komut.strip(), flags=re.IGNORECASE)
        if m:
            uygulama_adi = m.group(1).strip()
            sonuc = self.task_agent.submit(f"{uygulama_adi} aç", self._guvenli_gorev_calistir)
            self.konus(sonuc.message)
            return

        try:
            cursor.execute("SELECT COUNT(*) FROM dosya_parcalari")
            dosya_var_mi = cursor.fetchone()[0] > 0
        except Exception:
            dosya_var_mi = False

        if dosya_var_mi:
            try:
                dosya_cevabi = self.dosya_hakkinda_soru(komut)
                if dosya_cevabi and "bulamadım" not in dosya_cevabi.lower():
                    self.konus(dosya_cevabi)
                    return
            except Exception as e:
                print(f"[UYARI] Dosya sorusu işlenemedi: {e}")

        try:
            cevap = self.bilgi_sorusuna_cevap_ver(komut)
            if cevap is not None:
                self.konus(cevap)
                return
        except Exception as e:
            print(f"[UYARI] Bilgi sorusu işlenemedi: {e}")
        try:
            if self.bilgi_ogren(komut):
                return
        except Exception as e:
            print(f"[UYARI] Bilgi öğretme işlenemedi: {e}")

        try:
            self.permissions.check(Permission.WEB)
            web_cevap, _ham = web_bilgi.web_den_ogren_ve_ozetle(komut, getattr(self, "client", None))
            self.konus(web_cevap)
            return
        except PermissionDeniedError as exc:
            self.konus(f"Web araştırması için izin gerekli: {exc}")
        except Exception as e:
            print(f"[UYARI] Web araması işlenemedi: {e}")
            self.konus("Bu komutu anlayamadım. Tekrar söyleyebilir misin?")

    def _duygusal_mesaji_isle(self, komut):
        """Duygu paylaşımını bilgi sorusu ve komutlardan ayırarak yanıtlar."""
        analysis = self.semantic_understanding.analyze(komut)
        self.last_semantic_analysis = analysis
        reply = self.emotional_dialog.respond(komut, analysis)
        self.awaiting_emotional_context = self.emotional_dialog.active
        if reply is None:
            return False
        self.konus(reply)
        return True

    def stop_reading(self, komut=None):
        print("🛑 OKUMA DURDURULUYOR...")
        self.stop_speaking = True
        was_reading_haber = self.reading_haber
        self.reading_haber = False
        if was_reading_haber: 
            self.awaiting_haber_detayi = True

        else:
            self.awaiting_haber_detayi = False



        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass
        if hasattr(self, "gui"):
            try:
                self.gui.root.after(0, self.gui.mesaj_ekle, self.isim, "✓ Okuma durduruldu. Seni dinliyorum...")
            except Exception:
                pass
        else:
            print(f"{self.isim}: Okuma durduruldu. Seni dinliyorum...")

        time.sleep(0.5)
    def dosya_ogret(self, komut=None):
        yol = self._giris_metni(komut).replace("dosya öğret", "").strip()
        self._giris_temizle()
        try:
            self.permissions.check(Permission.FILES)
            guvenli_yol = resolve_user_file(yol)
            dosya_adi, metin = self.document_learner.read(str(guvenli_yol))
            self.memory_store.remember(
                "knowledge", metin[:8000], {"source": dosya_adi, "kind": "document"}
            )
        except FileProcessingError as exc:
            self.konus(f"Dosya güvenlik kontrolünden geçemedi: {exc}")
            return
        basarili, mesaj = dosya_ogretici.dosyadan_ogren(cursor, conn, str(guvenli_yol))
        if basarili:
            mesaj = f"{mesaj} Kaynak dosya: {dosya_adi}."
        self.konus(mesaj)

    def dosya_hakkinda_soru(self, soru):
        return dosya_ogretici.dosya_sorusu_cevapla(cursor, getattr(self, "client", None), soru)

    def gorev_ajanini_calistir(self, komut):
        """'Benim yerime ... yap', 'görevi hallet: ...' gibi komutlarla
        çok adımlı görev ajanını tetikler."""
        hedef = komut
        for tetik in ("benim yerime", "görevi hallet", "gorevi hallet",
                      "şunu yap:", "sunu yap:"):
            if tetik in hedef.lower():
                idx = hedef.lower().find(tetik)
                hedef = hedef[idx + len(tetik):].strip(" :")
                break

        if not hedef:
            self.konus("Ne yapmamı istediğini söyler misin? Örn: 'benim yerime "
                        "biyoloji dosyasındaki atom konusunu araştır ve özetle'.")
            return

        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as error:
            self.konus(f"Görev ajanının dil modeli için web izni gerekli: {error}")
            return

        self.konus("Tamam, hallediyorum...")
        sonuc = self.ajan.gorevi_yurut(hedef)
        self.konus(sonuc)

    def process_haber_detayi_response(self, komut):
        try:
            if not komut:
                return
            text = str(komut).strip().lower()
            if text in ("hayır", "hayir", "iptal", "vazgeç", "vazgec", "olmaz", "yok"):
                self.konus("Tamam. Başka ne yapabilirim?")
                self.awaiting_haber_detayi = False  
                return
            try:
                num = int(text.split()[0])
                if 1 <= num <= len(self.links):
                    self.haberi_detayli_oku(num)
                    self.awaiting_haber_detayi = False 
                    return
            except (ValueError, IndexError):
                pass
            self.konus("Haber numarası veya 'hayır' söyleyin.")            
        except Exception as e:
            self.konus(f"Haber detayı işleme hatası: {e}")
            self.awaiting_haber_detayi = False
    def kullanici_adi_getir(self):
        cursor.execute("SELECT name FROM user LIMIT 1")
        sonuc = cursor.fetchone()
        if sonuc:
            return sonuc[0]
        return None


    def kullanici_adi_kaydet(self, isim):
        cursor.execute("DELETE FROM user")
        cursor.execute(
            "INSERT INTO user (name, created_at) VALUES (?, ?)",
            (isim, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

    def kullanici_verilerini_sifirla(self):
        """Kod ve yapılandırma dosyalarına dokunmadan tüm kişisel verileri temizler.

        Bu metod yalnızca DijiDost arayüzündeki açık kullanıcı onayından sonra
        çağrılır. SQLite şemaları korunur; böylece sonraki açılış temiz bir
        başlangıç yaparken uygulama kendini yeniden kurmak zorunda kalmaz.
        """
        self.memory_store.clear()
        self.context_memory.clear()

        clear_sqlite_user_tables(self.conn)

        data_files = (
            "anka_memory.json", "hafiza.json", "konusma_hafizasi.json",
            "permissions.json", "dijidost_state.json", "ses_ayari.json",
            "dijidost_msg.json", "kamera_auth.json", "face_encodings.json",
            "ngrok_url.json", "ngrok_url.txt",
        )
        try:
            remove_personal_data_files(os.path.dirname(os.path.abspath(__file__)), data_files)
        except OSError as exc:
            logger.warning("Kullanıcı verisi silinemedi: %s", type(exc).__name__)
            raise

        project_root = os.path.dirname(os.path.abspath(__file__))
        faces_directory = os.path.join(project_root, "faces")
        if os.path.isdir(faces_directory):
            shutil.rmtree(faces_directory)

        self.isim = "Anka"
        self.gorevler = []
        self.notlar = []
        self.alisveris_listesi = []
        self.messages = []
        self.permissions = PermissionManager("permissions.json")
        logger.info("Kullanıcı tarafından tüm ANKA kişisel verileri sıfırlandı.")
    def komut_isle_genel_fallback(self, komut):
        m = re.match(r"^(.+?)\s+aç$", komut.strip(), flags=re.IGNORECASE)
        if m:
            sonuc = self.task_agent.submit(f"{m.group(1)} aç", self._guvenli_gorev_calistir)
            self.konus(sonuc.message)
            return True
        return False

    def _hafiza_komutunu_isle(self, komut):
        normalized = komut.casefold().strip()
        if "hafızamı göster" in normalized or "hafizami goster" in normalized:
            items = self.memory_store.list(limit=12)
            if not items:
                self.konus("Kalıcı hafızada kayıt yok.")
            else:
                ozet = "\n".join(f"- [{item['kind']}] {item['content'][:140]}" for item in items)
                self.konus(f"Hafızadaki son kayıtlar:\n{ozet}")
            return True
        if normalized.startswith(("hafızayı temizle", "hafizayi temizle")):
            self.memory_store.clear()
            self.konus("Kalıcı hafıza temizlendi.")
            return True
        if normalized.startswith("unut "):
            query = komut[5:].strip()
            if not query:
                self.konus("Unutmamı istediğiniz bilgiyi söyleyin.")
            else:
                removed = self.memory_store.forget(query)
                self.konus(f"{removed} hafıza kaydı silindi." if removed else "Bu ifadeyle eşleşen kayıt bulunamadı.")
            return True
        if normalized.startswith("izin "):
            parts = normalized.split()
            permission_names = {
                "mikrofon": Permission.MICROPHONE,
                "kamera": Permission.CAMERA,
                "dosya": Permission.FILES,
                "dosyalar": Permission.FILES,
                "sistem": Permission.SYSTEM,
                "web": Permission.WEB,
            }
            if len(parts) >= 3 and parts[1] in permission_names and parts[2] in {"aç", "ac", "kapat"}:
                self.permissions.set(permission_names[parts[1]], parts[2] in {"aç", "ac"})
                self.konus(f"{parts[1].capitalize()} izni {'açıldı' if parts[2] in {'aç', 'ac'} else 'kapatıldı'}.")
            else:
                self.konus("Örnek: 'izin kamera aç' veya 'izin mikrofon kapat'.")
            return True
        if "izinleri göster" in normalized or "gizlilik" in normalized:
            labels = {"microphone": "Mikrofon", "camera": "Kamera", "files": "Dosyalar", "system": "Sistem", "web": "Web"}
            summary = ", ".join(
                f"{labels[key]}: {'açık' if value else 'kapalı'}"
                for key, value in self.permissions.snapshot().items()
            )
            self.konus(f"Gizlilik ve izin durumu: {summary}. Kritik işlemler ayrıca her zaman onay ister.")
            return True
        return False

    def _bekleyen_gorevi_isle(self, komut):
        normalized = komut.casefold().strip()
        if normalized in {"onayla", "onaylıyorum", "onayliyorum", "evet"}:
            sonuc = self.task_agent.approve(self._guvenli_gorev_calistir)
            self.konus(sonuc.message)
            return True
        if normalized in {"iptal", "vazgeç", "vazgec", "hayır", "hayir"}:
            sonuc = self.task_agent.cancel()
            self.konus(sonuc.message)
            return True
        return False

    def _uygulamalari_yenile_istegi(self, komut):
        """'uygulamaları yenile' komutu: web aramasına düşmeden uygulama listesini yeniler."""
        low = str(komut).lower().replace("İ", "i")
        if not re.search(r"uygulamalar[ıi]?\s+(?:listesini\s+)?(?:yenile|güncelle|guncelle)", low):
            return False
        for ad in ("uygulamalari_yenile", "uygulamalari_tara", "yenile", "onbellegi_yenile",
                   "cache_yenile", "refresh", "tara", "yeniden_tara"):
            fn = getattr(uygulama_acici, ad, None)
            if callable(fn):
                try:
                    fn()
                    self.konus("Uygulama listesi yenilendi.")
                except Exception as e:
                    logger.warning("Uygulama listesi yenilenemedi: %s", type(e).__name__)
                    self.konus("Uygulama listesi yenilenirken hata oluştu.")
                return True
        # Yenileme fonksiyonu yoksa: önbellek/liste niteliklerini sıfırla, sonraki açılışta yeniden taransın.
        for ad in ("_cache", "_CACHE", "cache", "_apps", "APPS", "_uygulamalar", "uygulamalar"):
            v = getattr(uygulama_acici, ad, None)
            if isinstance(v, (dict, list, set)):
                try:
                    v.clear()
                except Exception:
                    pass
            elif v is not None:
                try:
                    setattr(uygulama_acici, ad, None)
                except Exception:
                    pass
        self.konus("Uygulama listesi yenilendi.")
        return True

    def _muzik_istegini_isle(self, komut):
        """'X şarkısını aç / çal' gibi istekleri uygulama açma yerine YouTube'a yönlendirir."""
        low = str(komut).lower().replace("İ", "i").strip()
        if "youtube music" in low or "youtube müzik" in low:
            return False
        if re.search(r"kapat|durdur|sustur|\bdur\b", low):
            return False
        if re.search(r"müzik klasör|muzik klasor|yerel müzik|yerel muzik|bilgisayardaki müzik", low):
            return False
        if not re.search(r"şarkı|sarki|türkü|turku|parçasını|parcasini|müzi[kğ]|muzi[kg]|\bçal\b|\bcal\b|\bçalar|dinlet|oynat", low):
            return False
        if not re.search(r"\baç|\bac\b|açar|açabilir|\bçal|\bcal\b|dinlet|oynat|dinlemek|dinleyeyim|istiyorum", low):
            return False
        q = re.sub(
            r"\b(bana|bi|bir|birazcık|lütfen|lutfen|şarkısını|sarkisini|şarkısı|şarkıyı|şarkıları|"
            r"şarkı|sarki|parçasını|parcasini|türküsünü|türküyü|türkü|turku|aç|ac|açar mısın|"
            r"açabilir misin|çal|cal|çalar mısın|çalabilir misin|dinlet|dinletir misin|"
            r"dinlemek istiyorum|youtube'?da|youtube|müziği|müziğini|müzik|muzik|oynat|oynatır mısın|istiyorum|hadi|be|ya)\b",
            " ", low)
        q = re.sub(r"[.?!,]", " ", q)
        q = re.sub(r"\s+", " ", q).strip()
        self.awaiting_youtube_sarki = True
        if not q:
            self.konus("Hangi şarkıyı YouTube'da açmamı istiyorsun?")
            return True
        self.process_youtube_sarki(q)
        return True

    def _hassas_gorevi_planla(self, komut):
        plan = self.task_agent.plan(komut)
        if plan.action == "conversation":
            return False
        sonuc = self.task_agent.submit(komut, self._guvenli_gorev_calistir)
        self.konus(sonuc.message)
        return True

    def _ajan_uygulama_ac(self, isim):
        sonuc = self.task_agent.submit(f"{isim} aç", self._guvenli_gorev_calistir)
        return sonuc.message

    def _ajan_web_ara(self, soru):
        self.permissions.check(Permission.WEB)
        return web_bilgi.web_den_ogren_ve_ozetle(soru, getattr(self, "client", None))[0]

    def _ajan_dosya_sor(self, soru):
        self.permissions.check(Permission.FILES)
        return dosya_ogretici.dosya_sorusu_cevapla(cursor, getattr(self, "client", None), soru)

    def _ajan_not_al(self, metin):
        note = str(metin or "").strip()
        if not note or len(note) > 2_000:
            raise ValueError("Not boş veya çok uzun.")
        self.notlar.append(note)
        self.hafizayi_kaydet()
        self.memory_store.remember("note", note, {"source": "task_agent"})
        return "Not kaydedildi."

    def _guvenli_gorev_calistir(self, plan: TaskPlan):
        if plan.action == "system_shutdown":
            self.permissions.check(Permission.SYSTEM)
            logger.critical("Kullanıcı onayı ile kapatma çalıştırılıyor")
            subprocess.Popen(["shutdown", "/s", "/t", "0"])
            return "Bilgisayarın kapatılması başlatıldı."
        if plan.action == "system_restart":
            self.permissions.check(Permission.SYSTEM)
            logger.critical("Kullanıcı onayı ile yeniden başlatma çalıştırılıyor")
            subprocess.Popen(["shutdown", "/r", "/t", "0"])
            return "Bilgisayarın yeniden başlatılması başlatıldı."
        if plan.action == "application_open":
            self.permissions.check(Permission.SYSTEM)
            match = re.match(r"^(.+?)\s+aç", plan.request.strip(), flags=re.IGNORECASE)
            application = match.group(1).strip() if match else plan.request.strip()
            if re.search(r"şarkı|sarki|türkü|turku|parça|müzik|muzik|\bçal\b", application, flags=re.IGNORECASE):
                if not self._muzik_istegini_isle(plan.request):
                    self.awaiting_youtube_sarki = True
                    self.konus("Hangi şarkıyı YouTube'da açmamı istiyorsun?")
                return "Şarkı isteği YouTube'a yönlendirildi."
            success, report = uygulama_acici.uygulama_ac(application)
            if not success:
                raise RuntimeError(report)
            return report
        if plan.action == "folder_open":
            self.permissions.check(Permission.FILES)
            raw_path = re.sub(r"^klas[öo]r\s+(aç|ac)\s*", "", plan.request, flags=re.IGNORECASE).strip()
            if not raw_path:
                raise FileProcessingError("Açılacak klasör yolunu belirtin.")
            folder = resolve_user_file(raw_path)
            if not folder.is_dir():
                raise FileProcessingError("Klasör bulunamadı.")
            if platform.system() == "Windows":
                os.startfile(str(folder))
            else:
                subprocess.Popen(["xdg-open", str(folder)])
            return f"Klasör açma isteği işletim sistemine iletildi: {folder}"
        if plan.action == "file_operation":
            self.permissions.check(Permission.FILES)
            content = plan.request.strip()
            raw_path = re.sub(r"^dosya\s+(aç|ac|oluştur|olustur)\s*", "", content, flags=re.IGNORECASE).strip()
            if not raw_path:
                raise FileProcessingError("Dosya yolunu komutta belirtin.")
            if content.casefold().startswith(("dosya oluştur", "dosya olustur")):
                path = resolve_user_file(raw_path, for_creation=True)
                with path.open("x", encoding="utf-8"):
                    pass
                return f"Dosya oluşturuldu: {path}"
            path = resolve_user_file(raw_path)
            with path.open("r", encoding="utf-8") as file:
                preview = file.read(700)
            self.konus(preview or "Dosya boş.")
            return f"Dosya okundu: {path}"
        if plan.action == "file_learn":
            self.dosya_ogret(plan.request)
            return "Dosyadan öğrenme işlemi tamamlandı."
        if plan.action == "shell_command":
            raise PermissionDeniedError("Kabuk komutları bu sürümde doğrudan çalıştırılmaz.")
        raise PermissionDeniedError("Bu işlem bu sürümde güvenli olarak desteklenmiyor.")

    def konusma_kaydet(self, kim, mesaj):
        cursor.execute(
            "INSERT INTO conversations (speaker, message, timestamp) VALUES (?, ?, ?)",
            (kim, mesaj, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

    def isim_coz(self, text):
        text = text.lower()
        if "benim adım" in text:
            return text.split("benim adım")[-1].strip().capitalize()
        if "adım" in text:
            return text.split("adım")[-1].strip().capitalize()
        return text.strip().capitalize()


    def isim_degistirme_istegi(self, text):
        text = text.lower()
        return ("isim" in text or "ad" in text) and "değiştir" in text or "degistir" in text
    def yeni_isim_coz(self, text):
        text = text.lower().strip()
 
        if "bana artık" in text:
            k = text.split("bana artık")[-1].strip()
            if k:
                return k.capitalize()
        if "adımı değiştir" in text:
            k = text.split("adımı değiştir")[-1].strip()
            if k:
                return k.capitalize()
        if "ismimi değiştir" in text:
            k = text.split("ismimi değiştir")[-1].strip()
            if k:
                return k.capitalize()

        if text and len(text) > 1:
            return text.capitalize()

        return None

    def dinle_hotword(self):   
        if not self.permissions.is_allowed(Permission.WEB):
            logger.info("Bulut hotword tanıma web izni kapalı olduğu için çalıştırılmadı")
            return None
        sr_recognizer = sr.Recognizer()
        sr_recognizer.energy_threshold = 2000  
        fs = 44100
        saniye = 1  
        try:
            print("🎤 Hotword dinleniyor...")
            ses = sd.rec(int(saniye * fs), samplerate=fs, channels=1, dtype=np.int16)
            sd.wait() 
            ses = np.asarray(ses, dtype=np.float32)
            ses = ses / 32768.0
            audio_data = sr.AudioData((ses * 32768).astype(np.int16).tobytes(), fs, 2)
            try:
                text = sr_recognizer.recognize_google(audio_data, language="tr-TR")
                print(f"Hotword: {text}")
                return text.lower()
            except sr.UnknownValueError:
                return None
            except sr.RequestError:
                return None
        except Exception as e:
            print(f"Hotword dinleme hatası: {e}")
            return None
    def hava_durumu_google(self, sehir):
        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as exc:
            self.konus(f"Hava durumu için web izni gerekli: {exc}")
            return
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        import time
        code_map = {
            0: "Açık",
            1: "Çoğunlukla açık",
            2: "Parçalı bulutlu",
            3: "Bulutlu",
            45: "Sis",
            48: "Donmuş sis",
            51: "Hafif çiseleme",
            53: "Orta çiseleme",
            55: "Yoğun çiseleme",
            56: "Donan hafif çiseleme",
            57: "Donan yoğun çiseleme",
            61: "Hafif yağmur",
            63: "Orta yağmur",
            65: "Şiddetli yağmur",
            66: "Donan hafif yağmur",
            67: "Donan yoğun yağmur",
            71: "Hafif kar",
            73: "Orta kar",
            75: "Yoğun kar",
            77: "Dolu",
            80: "Hafif sağanak",
            81: "Orta sağanak",
            82: "Şiddetli sağanak",
            85: "Hafif kar sağanağı",
            86: "Yoğun kar sağanağı",
            95: "Gök gürültülü fırtına",
            96: "Gök gürültülü hafif dolu",
            99: "Gök gürültülü yoğun dolu"
        }
        def speak(msg):
            try:
                self.konus(msg)
            except Exception:
                print(msg)
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.8, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        try:
            geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.requote_uri(sehir)}&count=1&language=tr"
            r = session.get(geo_url, timeout=8)
            r.raise_for_status()
            gj = r.json()
            lat = lon = None
            place_name = sehir
            if gj.get("results"):
                loc = gj["results"][0]
                lat = loc.get("latitude")
                lon = loc.get("longitude")
                place_name = loc.get("name") or place_name
            if lat is None or lon is None:
                try:
                    nom = session.get("https://nominatim.openstreetmap.org/search",
                                      params={"q": sehir, "format": "json", "limit": 1},
                                      headers={"User-Agent": "ev-asistani/1.0"}, timeout=8)
                    nom.raise_for_status()
                    nj = nom.json()
                    if nj:
                        lat = float(nj[0]["lat"])
                        lon = float(nj[0]["lon"])
                        place_name = nj[0].get("display_name", place_name).split(",")[0]
                except Exception:
                    pass
            if lat is None or lon is None:
                speak("Şehir koordinatları bulunamadı. Lütfen şehir adını kontrol edin.")
                return
            weather_url = ("https://api.open-meteo.com/v1/forecast"
                           f"?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto")
            w = session.get(weather_url, timeout=8)
            w.raise_for_status()
            wj = w.json()
            cw = wj.get("current_weather")
            if not cw:
                speak("Hava durumu verisi alınamadı.")
                return
            temp = cw.get("temperature")  
            wind = cw.get("windspeed")    
            code = cw.get("weathercode")
            condition = code_map.get(code, "Bilinmeyen hava durumu")
            try:
                temp_str = f"{temp:.1f}°C" if temp is not None else ""
                wind_str = f"{wind} km/s" if wind is not None else ""
                parts = [f"{place_name} hava durumu: {condition}"]
                if temp_str:
                    parts.append(f"sıcaklık {temp_str}")
                if wind_str:
                    parts.append(f"rüzgar {wind_str}")
                speak(", ".join(parts))
                return
            except Exception:
                speak(f"{place_name} hava durumu: {condition}")
                return
        except Exception:
            speak("Hava durumu servisine bağlanılamadı.")
            self._web_adresi_ac("https://www.mgm.gov.tr/", "Resmi meteoroloji sayfası")
    def hesap_makinesi(self, komut=None):
        ifade = self._giris_metni(komut)
        self._giris_temizle()
        try:
            sonuc = evaluate_expression(ifade)
            self.konus(f"Sonuç: {sonuc}")
        except CalculationError as exc:
            self.konus(f"Geçerli bir matematiksel işlem yazın: {exc}")
    def hafizayi_kaydet(self, dosya="hafiza.json"):
        data = {"gorevler": self.gorevler, "alisveris": self.alisveris_listesi, "notlar": self.notlar}
        try:
            JsonStateStore(dosya).save(data)
        except (OSError, TypeError, ValueError) as error:
            logger.warning("Legacy hafıza kaydedilemedi: %s", type(error).__name__)
    def hafizayi_yukle(self, dosya="hafiza.json"):
        data = JsonStateStore(dosya).load()
        self.gorevler = data.get("gorevler", []) if isinstance(data.get("gorevler", []), list) else []
        self.alisveris_listesi = data.get("alisveris", []) if isinstance(data.get("alisveris", []), list) else []
        self.notlar = data.get("notlar", []) if isinstance(data.get("notlar", []), list) else []
    def stop_reading(self, komut=None):
        self.stop_speaking = True
        self.reading_haber = False
        self.awaiting_haber_detayi = None
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        if hasattr(self, "gui"):
            try:
                self.gui.root.after(0, self.gui.mesaj_ekle, "Sistem", "Haber okuma durduruldu.")
            except Exception:
                pass
        else:
            print("Haber okuma durduruldu.")
    def haberi_detayli_oku(self, index):
        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as error:
            self.konus(f"Haber detayı için web izni gerekli: {error}")
            return
        import requests
        from bs4 import BeautifulSoup
        import json, re
        from urllib.parse import urljoin, urlparse, quote_plus, unquote
        import time
        if not hasattr(self, "links") or index < 1 or index > len(self.links):
            self.konus("Geçersiz haber numarası.")
            return
        start_url = self.links[index - 1]
        if not start_url:
            self.konus("Bu haberin bağlantısı bulunamadı.")
            return
        headline = None
        try:
            headline = (self.awaiting_haber_detayi[index - 1] if hasattr(self, "awaiting_haber_detayi") else None)
        except Exception:
            headline = None
        headline = None
        try:
            headline = (self.haber_basliklari[index - 1] if hasattr(self, "haber_basliklari") else None)
        except Exception:
            headline = None
        headline = None
        try:
            if hasattr(self, "haber_basliklari"):
                headline = self.haber_basliklari[index - 1]
        except Exception:
            headline = None
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        def clean_text(t):
            if not t:
                return ""
            t = re.sub(r'\s+', ' ', t).strip()
            t = re.sub(r"(?is)Copyright.*?$", "", t)
            t = re.sub(r"(?is)Tüm hakları saklıdır.*?$", "", t)
            t = re.sub(r"(?is)YASAL UYARI:.*?$", "", t)
            t = re.sub(r"(?is)Burada yer alan.*?$", "", t)
            t = re.sub(r"(?is)Bu haber.*?izin.*?$", "", t)
            return t.strip()
        def speak_and_show(text, source_url=None):
            if not text:
                return
            text = clean_text(text)
            if not text:
                return        
            if hasattr(self, "gui"):
                try:
                    self.gui.root.after(0, self.gui.mesaj_ekle, self.isim, text)
                except Exception:
                    pass       
            chunk = 800
            for i in range(0, len(text), chunk):
                part = text[i:i+chunk]
                part = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', part)
                self.konus(part)
                time.sleep(0.25)
            if source_url:
                try:
                    self.konus(f"Kaynak: {source_url}")
                except Exception:
                    pass
        def fetch_soup(url, timeout=12):
            try:
                r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                r.raise_for_status()
                if "html" not in (r.headers.get("Content-Type") or "").lower():
                    return None, r.url
                return BeautifulSoup(r.text, "html.parser"), r.url
            except Exception:
                return None, url
        def extract_bigpara(soup):
            if not soup:
                return None
            selectors = [
                "div[itemprop='articleBody']",
                "div[class*='article-text']",
                "div[class*='article-body']",
                "div[class*='content']",
                "div[class*='news-detail']",
                "div[class*='haber-detay']",
                "div[class*='detail-body']",
            ]
            for sel in selectors:
                try:
                    el = soup.select_one(sel)
                    if el:
                        paras = [p.get_text(" ", strip=True) for p in el.find_all(["p","h2","h3","div"]) if p.get_text(strip=True)]
                        text = " ".join(paras)
                        text = clean_text(text)
                        if text and len(text) > 200:
                            return text
                except Exception:
                    continue
            try:
                big_div = max(soup.find_all("div"), key=lambda d: len(d.get_text(" ", strip=True) or ""))
                txt = clean_text(big_div.get_text(" ", strip=True))
                if txt and len(txt) > 200:
                    return txt
            except Exception:
                pass
            return None
        def general_extract(soup):
            if not soup:
                return None
            domain = urlparse(final_url or start_url).netloc.lower() if 'final_url' in locals() else ""
            if "aa.com.tr" in domain:
                selectors = [
                    "div[class*='news-content'] p",
                    "div[class*='article-body'] p",
                    "article p",
                    "div[id='content'] p",
                    "div[class*='detail'] p"
                ]
                paras = []
                for sel in selectors:
                    try:
                        elements = soup.select(sel)
                        if elements:
                            paras.extend([p.get_text(" ", strip=True) for p in elements if p.get_text(strip=True)])
                    except Exception:
                        continue
                if paras:
                    text = clean_text(" ".join(paras))
                    if text and len(text) > 200:
                        return text

            general_selectors = [
                "main p",
                "section p",
                "article p",
                "div[class*='content'] p",
                "div[class*='article'] p"
            ]
            for sel in general_selectors:
                try:
                    elements = soup.select(sel)
                    if elements:
                        paras = [p.get_text(" ", strip=True) for p in elements if p.get_text(strip=True)]
                        text = clean_text(" ".join(paras))
                        if text and len(text) > 200:
                            return text
                except Exception:
                    continue
        def try_amp_variants(url):
            amps = []
            if url.endswith("/"):
                base = url[:-1]
            else:
                base = url
            amps.append(base + "/amp")
            amps.append(base + "?outputType=amp")
            amps.append(base + "/m")
            for a in amps:
                soup, final = fetch_soup(a)
                if soup:
                    text = general_extract(soup) or extract_bigpara(soup)
                    if text and len(text) > 200:
                        return text, final
            return None, None
        try:
            soup, final_url = fetch_soup(start_url)
            soup, final_url = fetch_soup(start_url)
            domain = urlparse(final_url).netloc.lower() if final_url else urlparse(start_url).netloc.lower()
            parsed = urlparse(final_url or start_url)
            path = (parsed.path or "").strip("/")
            if (not path or path == "") and headline:
                try:
                    q = f"site:{domain} {headline}"
                    r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=headers, timeout=10)
                    if r.status_code == 200:
                        so = BeautifulSoup(r.text, "html.parser")
                        found = None
                        for a in so.find_all("a", href=True):
                            h = a["href"].strip()
                            if h.startswith("/"):
                                h = urljoin(f"https://{domain}", h)
                            if h.startswith("http") and domain in urlparse(h).netloc:
                                found = h
                                break
                        if found:
                            soup, final_url = fetch_soup(found)
                            domain = urlparse(final_url).netloc.lower() if final_url else domain
                except Exception:
                    pass
            if "bigpara" in domain or "hurriyet" in domain and "bigpara" in start_url:
                 text = extract_bigpara(soup)
                 if not text:
                     amp_text, amp_url = try_amp_variants(final_url or start_url)
                     if amp_text:
                         speak_and_show(amp_text, amp_url)
                         return
                     text = general_extract(soup)
                 if text and len(text) > 200:
                     speak_and_show(text, final_url)
                     return
                 if headline:
                     try:
                         q = f"site:{domain} {headline}"
                         r = requests.post("https://html.duckduckgo.com/html/", data={"q": q}, headers=headers, timeout=10)
                         if r.status_code == 200:
                             so = BeautifulSoup(r.text, "html.parser")
                             found = None
                             for a in so.find_all("a", href=True):
                                 h = a["href"].strip()
                                 if domain in h and h.startswith("http"):
                                     found = h
                                     break
                             if found:
                                 s2, f2 = fetch_soup(found)
                                 if s2:
                                     t2 = extract_bigpara(s2) or general_extract(s2)
                                     if t2 and len(t2) > 200:
                                         speak_and_show(t2, f2)
                                         return
                     except Exception:
                         pass
            text = general_extract(soup)
            if text and len(text) > 200:
                speak_and_show(text, final_url)
                return
            try:
                if soup:
                    candidates = []
                    for a in soup.find_all("a", href=True):
                        href = a["href"].strip()
                        if href.startswith("/"):
                            href = urljoin(final_url or start_url, href)
                        if href.startswith("http") and "google" not in href and href not in candidates:
                            candidates.append(href)
                    for c in candidates[:10]:
                        s2, f2 = fetch_soup(c)
                        if s2:
                            t2 = extract_bigpara(s2) or general_extract(s2)
                            if t2 and len(t2) > 200:
                                speak_and_show(t2, f2)
                                return
            except Exception:
                pass
            amp_text, amp_url = try_amp_variants(final_url or start_url)
            if amp_text:
                speak_and_show(amp_text, amp_url)
                return  
            if soup:
                paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
                paras = [p for p in paras if p and len(p) > 30]
                if paras:
                    merged = clean_text(" ".join(paras[:80]))
                    if merged and len(merged) > 120:
                        speak_and_show(merged, final_url)
                        return      
            self.konus("Tam metin otomatik alınamadı.")
            self._web_adresi_ac(final_url or start_url, "Orijinal haber sayfası")
            return
        except Exception as e:
            self.konus(f"Haber detayları alınamadı: {e}")
            return
    def sus_gecici(self, komut=None):
        """20 saniyeliğine tamamen susar (konuşmaz, dinlemez)"""
        if self.sus_mode:
            return 

        self.stop_speaking = True
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass

        self.sus_mode = True
        self.konus("Tamam lan susuyorum.")

        import threading
        self.sus_timer = threading.Timer(20.0, self.sus_bitis)
        self.sus_timer.daemon = True
        self.sus_timer.start()
    
    def sus_bitis(self):
        """Sus modu bittiğinde çağrılır"""
        self.sus_mode = False
        self.stop_speaking = False
        self.konus("Artık susmamaya karar verdim.")
    def ilac_hatirlat(self, komut=None):
        metin = (komut or "").lower().strip()
        metin = metin.replace("ilacı hatırlat", "").strip()
        if metin in ("hayır", "hayir", "iptal", "vazgeç", "vazgec"):
            self.konus("Tamam, ilacı hatırlatma iptal edildi.")
            self.awaiting_ilac = False
            self.awaiting_ilac_step = None
            self.awaiting_ilac_med = None
            return
        import re
        if metin:
            time_match = re.search(r'(\d{1,2}\s*[:\.]\s*\d{1,2})|(\d{1,2})(?=\D*$)', metin)
            if time_match:
                time_str = time_match.group(0)
                ilac = metin.replace(time_str, "").replace("saat", "").strip()
                if not ilac:
                    self.konus("Hangi ilacı hatırlatayım?")
                    self.awaiting_ilac = True
                    self.awaiting_ilac_step = 1
                    self.awaiting_ilac_med = None
                    return
                self.awaiting_ilac = False
                self.awaiting_ilac_step = None
                self.process_ilac_response(f"{ilac} {time_str}")
                return
        self.konus("Hangi ilacı hatırlatayım?")
        self.awaiting_ilac = True
        self.awaiting_ilac_step = 1  
        self.awaiting_ilac_med = None
        return
    def process_ilac_response(self, cevap):
        try:
            if not cevap:
                return
            text = str(cevap).strip()
            lower = text.lower().strip()
            if lower in ("hayır", "hayir", "iptal", "vazgeç", "vazgec"):
                self.konus("Tamam, ilacı hatırlatma iptal edildi.")
                self.awaiting_ilac = False
                self.awaiting_ilac_step = None
                self.awaiting_ilac_med = None
                return
            import re, datetime, threading
            step = getattr(self, "awaiting_ilac_step", None)
            def parse_time(s):
                s = s.lower()
                m = re.search(r'(\d{1,2})\s*[:\.]\s*(\d{1,2})', s)
                if m:
                    h = int(m.group(1)); mi = int(m.group(2)); return h, mi
                m2 = re.search(r'(\d{1,2})', s)
                if m2:
                    h = int(m2.group(1)); return h, 0
                return None
            if step is None:
                tparse = parse_time(text)
                if tparse:
                    time_part = re.search(r'(\d{1,2}\s*[:\.]\s*\d{1,2})|(\d{1,2})(?=\D*$)', text).group(0)
                    ilac = text.replace(time_part, "").replace("saat", "").strip()
                    if not ilac:
                        ilac = "ilaç"
                    hour, minute = tparse

                    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                        self.konus("Geçersiz saat bilgisi. 0-23 arası saat ve 0-59 arası dakika girin.")
                        return
                    now = datetime.now()
                    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if target <= now:
                        target = target + datetime.timedelta(days=1)
                    delta = (target - now).total_seconds()
                    def hatirlatici():
                        try:
                            self.konus(f"Saat {hour:02d}:{minute:02d} oldu — {ilac} ilacını almayı unutma.")
                        except Exception:
                            pass
                    timer = threading.Timer(delta, hatirlatici)
                    timer.daemon = True
                    timer.start()
                    self.ilac_timer = timer
                    self.ilac_time = target.isoformat()
                    self.konus(f"Tamam. {ilac} için saat {hour:02d}:{minute:02d} hatırlatması ayarlandı (ilk hatırlatma {target.strftime('%Y-%m-%d %H:%M')}).")
                    return
                else:
                    self.awaiting_ilac = True
                    self.awaiting_ilac_step = 1
                    self.awaiting_ilac_med = text
                    self.konus(f"Tamam, '{text}' için. Saat kaçta hatırlatayım?")
                    self.awaiting_ilac_step = 2
                    return
            if step == 1:
                ilac = text
                self.awaiting_ilac_med = ilac
                self.konus(f"'{ilac}' ilacı için saat kaçta hatırlatayım?")
                self.awaiting_ilac_step = 2
                self.awaiting_ilac = True
                return
            if step == 2:
                ilac = getattr(self, "awaiting_ilac_med", None) or "ilacınız"
                parsed = parse_time(text)
                if not parsed:
                    m = re.search(r'([^\d:]+)\s+(\d{1,2}[:\.]\d{1,2}|\d{1,2})', text)
                    if m:
                        ilac = m.group(1).strip()
                        parsed = parse_time(m.group(2))
                if not parsed:
                    self.konus("Saati anlayamadım. Lütfen örnek: '10' veya '10:10' şeklinde yazın.")
                    return
                hour, minute = parsed
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    self.konus("Geçersiz saat bilgisi. 0-23 arası saat ve 0-59 arası dakika girin.")
                    return
                now = datetime.now()
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if target <= now:
                    target = target + datetime.timedelta(days=1)
                delta = (target - now).total_seconds()

                def hatirlatici():
                    try:
                        self.konus(f"Saat {hour:02d}:{minute:02d} oldu — {ilac} ilacını almayı unutma.")
                    except Exception:
                        pass
                timer = threading.Timer(delta, hatirlatici)
                timer.daemon = True
                timer.start()
                self.ilac_timer = timer
                self.ilac_time = target.isoformat()
                self.awaiting_ilac = False
                self.awaiting_ilac_step = None
                self.awaiting_ilac_med = None
                self.konus(f"Tamam. {ilac} için saat {hour:02d}:{minute:02d} hatırlatması ayarlandı (ilk hatırlatma {target.strftime('%Y-%m-%d %H:%M')}).")
                return
        except Exception as e:
            self.konus(f"İlaç hatırlatma işlemi sırasında hata: {e}")

    TURKCE_KELIMELER = {
        'a': ['elma', 'ayakkabı', 'ağaç', 'ayna', 'arabalar', 'aslan', 'alet', 'aile', 'anlık'],
        'b': ['baba', 'bahar', 'bahçe', 'balık', 'bambu', 'banka', 'bardak', 'barış', 'bastırma'],
        'c': ['can', 'cazibe', 'ceket', 'cephe', 'cerah', 'cezerye'],
        'd': ['dağ', 'daire', 'dans', 'davul', 'değer', 'değişim', 'denim', 'dış', 'diş'],
        'e': ['ebe', 'eczane', 'eda', 'eğitim', 'eğlence', 'eğrelti', 'elastik', 'elektrik', 'eleman'],
        'f': ['fabrika', 'faç', 'fahiş', 'faide', 'fal', 'falan', 'fark', 'farsa', 'faunası'],
        'g': ['gaj', 'galeri', 'galiş', 'galon', 'garaz', 'garson', 'gasa', 'gaş', 'gaz'],
        'h': ['ha', 'haç', 'hadef', 'hademe', 'hadise', 'haftası', 'hain', 'halam', 'halat'],
        'ı': ['ıdır', 'ık', 'ıkış', 'ıl', 'ılı', 'ılkaya', 'ırk', 'ırma', 'ış'],
        'i': ['ibe', 'iç', 'içeride', 'içinde', 'idare', 'idam', 'ide', 'ideasız', 'idemen'],
        'j': ['jadedi', 'jaket', 'jambon', 'jandarma', 'jankri', 'japonca', 'jargon', 'jasper'],
        'k': ['ka', 'kaaç', 'kaba', 'kabağı', 'kabahat', 'kabala', 'kabalak', 'kabalaşmak', 'kabaca'],
        'l': ['la', 'labarum', 'labda', 'laberint', 'labıyaka', 'labla', 'labne', 'laboşş'],
        'm': ['ma', 'maaçı', 'maalef', 'maama', 'maanqa', 'maara', 'maasi', 'maasiye'],
        'n': ['na', 'naasır', 'naazı', 'naber', 'nabız', 'nabiye', 'nabla', 'nabuk', 'nabz'],
        'o': ['oa', 'oaı', 'oasis', 'oasist', 'ob', 'oba', 'obak', 'obakçı'],
        'ö': ['öbek', 'öbek', 'öberi', 'öberk', 'öbet', 'öbey', 'öbi', 'öbok', 'öbür'],
        'p': ['pa', 'paan', 'paaş', 'pab', 'paba', 'pabağı', 'pabağlı', 'pabalık', 'paban'],
        'r': ['ra', 'raa', 'raaş', 'rab', 'raba', 'rabağı', 'rabah', 'rabai', 'rabaraber'],
        's': ['sa', 'saa', 'saasını', 'sab', 'saba', 'sabah', 'sababı', 'sabac', 'sabaç'],
        'ş': ['şa', 'şaa', 'şab', 'şaba', 'şabağı', 'şabah', 'şabahu', 'şabak', 'şabal'],
        't': ['ta', 'taa', 'taş', 'tab', 'taba', 'tabağı', 'tabak', 'tabal', 'taban'],
        'u': ['ua', 'uaş', 'ub', 'uba', 'ubağı', 'ubah', 'ubahu', 'ubak', 'ubakal'],
        'ü': ['üa', 'üaş', 'üb', 'üba', 'übağı', 'übah', 'übahu', 'übak', 'übakal'],
        'v': ['va', 'vaa', 'vaş', 'vab', 'vaba', 'vabağı', 'vabah', 'vabahu', 'vabak'],
        'y': ['ya', 'yaa', 'yaş', 'yab', 'yaba', 'yabağı', 'yabah', 'yabahu', 'yabak'],
        'z': ['za', 'zaa', 'zaş', 'zab', 'zaba', 'zabağı', 'zabah', 'zabahu', 'zabak']
    }
    
    def kelime_oyunu_oyna(self, komut=None):
        """Kelime oyunu: minimum 60 turda devam et"""
        self_asistan = self

        kullanilan_kelimeler = set()
        sira = "ai"
        tur = 0
        max_turlar = 200 

        self_asistan.konus("Kelime oyununa hoş geldin! 60+ tur oynamak istiyoruz? Hadi başlayalım!")
        time.sleep(1)

        ilk_kelimeler = ['elma', 'kitap', 'kapı', 'masa', 'bahçe', 'deniz', 'dağ', 'güneş', 'ayakkabı']
        son_kelime = random.choice(ilk_kelimeler)
        self_asistan.konus(f"Başlıyorum: {son_kelime}")
        kullanilan_kelimeler.add(son_kelime)
        sira = "insan"

        while tur < max_turlar:
            tur += 1

            if sira == "insan":
                self_asistan.konus(f"[Tur {tur}] Senin sırası. '{son_kelime[-1]}' ile başla.")
                dinleme_girisi = self_asistan.dinle()

                if not dinleme_girisi:
                    self_asistan.konus("Duyamadım.")
                    continue
                    
                kelime = dinleme_girisi.lower().strip()
                kelime_temiz = ''.join(c for c in kelime if c.isalpha())

                if not kelime_temiz or len(kelime_temiz) < 2:
                    self_asistan.konus("Geçerli bir kelime söyle.")
                    continue
                    
                if not kelime_temiz.startswith(son_kelime[-1]):
                    self_asistan.konus(f"Yanlış harf! {son_kelime[-1]} gerekli. Kaybettin!")
                    self_asistan.konus(f"Oyun bitiş: {tur} tur, {len(kullanilan_kelimeler)} kelime.")
                    return

                if kelime_temiz in kullanilan_kelimeler:
                    self_asistan.konus(f"'{kelime_temiz}' zaten söylenmişti! Kaybettin.")
                    return

                kullanilan_kelimeler.add(kelime_temiz)
                son_kelime = kelime_temiz
                sira = "ai"

            else:  
                son_harf = son_kelime[-1]

    
                aday_kelimeler = [k for k in TURKCE_KELIMELER.get(son_harf, []) if k not in kullanilan_kelimeler and len(k) > 1]

                if aday_kelimeler:
                    ai_kelime = random.choice(aday_kelimeler)
                else:

                    try:
                        response = self_asistan.client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[
                                {"role": "system", "content": "Türkçe kelime oyunu. '{} ' harfiyle başlayan 1 Türkçe kelime söyle. Sadece kelime, başka şey yazma.".format(son_harf)},
                                {"role": "user", "content": f"'{son_harf}' ile başlayan yeni kelime (daha söylenmiş: {', '.join(list(kullanilan_kelimeler)[-5:])})"}
                            ],
                            max_tokens=10,
                            temperature=0.8
                        )
                        ai_kelime = response.choices[0].message.content.lower().strip().split()[0]
                    except:
                        self_asistan.konus("Takıldım. Sen kazandın!")
                        return

                if ai_kelime in kullanilan_kelimeler or not ai_kelime.startswith(son_harf):
                    self_asistan.konus(f"Başarısız oldum. Sen kazandın! {len(kullanilan_kelimeler)} tur /60+")
                    return

                self_asistan.konus(ai_kelime)
                kullanilan_kelimeler.add(ai_kelime)
                son_kelime = ai_kelime
                sira = "insan"
                time.sleep(0.5)

                if tur >= 60:
                    kont = (self_asistan.dinle() or "").lower()
                    if "dur" in kont or "bitti" in kont:
                        self_asistan.konus(f"Tebrik! {tur} tur, {len(kullanilan_kelimeler)} kelime! 🎉")
                        return

        self_asistan.konus(f"Oyun sınırına ulaştı! {tur} tur, {len(kullanilan_kelimeler)} kelime 🎮")     
    def bugunun_anlami(self, komut=None):
        import datetime
        tarih = datetime.now()
        gun = tarih.day
        ay = tarih.strftime("%B")
        gunler_ve_anlamlari = {
            # OCAK
            ("January", 1): "Yılbaşı",
            ("January", 7): "Beyaz Baston Körler Haftası Başlangıcı",
            ("January", 10): "Çalışan Gazeteciler Günü / İdareciler Günü",
            ("January", 14): "Beyaz Baston Körler Haftası Bitişi",
            ("January", 25): "Cüzam Haftası Başlangıcı",
            ("January", 26): "Dünya Gümrük Günü",
            ("January", 31): "Cüzam Haftası Bitişi",
            # ŞUBAT
            ("February", 9): "Dünya Sigarayı Bırakma Günü",
            ("February", 14): "Sevgililer Günü",
            ("February", 28): "Sivil Savunma Günü",
            # MART
            ("March", 1): "Yeşilay Haftası Başlangıcı",
            ("March", 7): "Yeşilay Haftası Bitişi",
            ("March", 8): "Dünya Kadınlar Günü",
            ("March", 12): "İstiklal Marşının Kabulü",
            ("March", 15): "Dünya Tüketiciler Günü",
            ("March", 18): "Şehitler Günü / Çanakkale Zaferi",
            ("March", 18): "Yaşlılara Saygı Haftası Başlangıcı",
            ("March", 24): "Yaşlılara Saygı Haftası Bitişi / Dünya Verem Günü",
            ("March", 21): "Nevruz Bayramı / Orman Haftası Başlangıcı / Dünya Şiir Günü",
            ("March", 26): "Orman Haftası Bitişi",
            ("March", 22): "Dünya Su Günü",
            ("March", 23): "Dünya Meteoroloji Günü",
            ("March", 27): "Dünya Tiyatrolar Günü",
            # NİSAN
            ("April", 1): "Dünya Sağlık Günü ve Kanser Haftası Başlangıcı",
            ("April", 7): "Dünya Sağlık Günü ve Kanser Haftası Bitişi",
            ("April", 5): "Avukatlar Günü",
            ("April", 8): "Sağlık Haftası Başlangıcı",
            ("April", 14): "Sağlık Haftası Bitişi",
            ("April", 10): "Polis Teşkilatının Kuruluşu",
            ("April", 15): "Turizm Haftası Başlangıcı",
            ("April", 22): "Turizm Haftası Bitişi",
            ("April", 21): "Ebeler Haftası Başlangıcı",
            ("April", 28): "Ebeler Haftası Bitişi / Kardeşlik Haftası Başlangıcı",
            ("April", 23): "23 Nisan Ulusal Egemenlik ve Çocuk Bayramı",
            ("April", 20): "Kutlu Doğum Haftası Başlangıcı",
            ("April", 26): "Kutlu Doğum Haftası Bitişi",
            # MAYIS
            ("May", 1): "Emek ve Dayanışma Günü",
            ("May", 4): "İş Sağlığı ve Güvenliği Haftası Başlangıcı",
            ("May", 10): "İş Sağlığı ve Güvenliği Haftası Bitişi / Danıştay ve İdari Yargı Haftası",
            ("May", 6): "Hıdrellez Kültür ve Bahar Bayramı",
            ("May", 10): "Müzeler Haftası Başlangıcı / Sakatlar Haftası Başlangıcı",
            ("May", 16): "Müzeler Haftası Bitişi / Sakatlar Haftası Bitişi",
            ("May", 12): "Hemşirelik Haftası Başlangıcı",
            ("May", 18): "Hemşirelik Haftası Bitişi",
            ("May", 14): "Dünya Eczacılık Günü / Dünya Çiftçiler Günü",
            ("May", 15): "Yeryüzü İklim Günü / Hava Şehitlerini Anma Günü",
            ("May", 17): "Dünya Telekomünikasyon Günü",
            ("May", 19): "Gençlik Haftası Başlangıcı",
            ("May", 25): "Gençlik Haftası Bitişi",
            ("May", 21): "Dünya Süt Günü",
            ("May", 29): "İstanbul'un Fethi",
            ("May", 31): "Dünya Sigarasız Günü / Dünya Hostesler Günü",
            # HAZİRAN
            ("June", 5): "Dünya Çevre Günü",
            ("June", 10): "Çevre Koruma Haftası Başlangıcı",
            ("June", 16): "Çevre Koruma Haftası Bitişi",
            ("June", 17): "Dünya Çölleşme ve Kuraklıkla Mücadele Haftası",
            ("June", 20): "Dünya Mülteciler Günü",
            ("June", 26): "Uyuşturucu Kullanımı ve Trafiği ile Mücadele Günü",
            # TEMMUZ
            ("July", 1): "Kabotaj ve Denizcilik Günü",
            ("July", 5): "Nasrettin Hoca Şenlikleri Başlangıcı",
            ("July", 10): "Nasrettin Hoca Şenlikleri Bitişi",
            ("July", 11): "Dünya Nüfus Günü",
            ("July", 24): "Gazeteciler (Basın) Bayramı",
            # AĞUSTOS
            ("August", 30): "Zafer Bayramı",
            # EYLÜL
            ("September", 1): "Dünya Barış Günü",
            ("September", 3): "Halk Sağlığı Haftası Başlangıcı",
            ("September", 9): "Halk Sağlığı Haftası Bitişi",
            ("September", 19): "Şehitler ve Gaziler Günü / Haftası Başlangıcı",
            ("September", 25): "İtfaiyecilik Haftası Başlangıcı",
            ("October", 1): "İtfaiyecilik Haftası Bitişi",
            ("September", 26): "Dil Bayramı",
            ("September", 27): "Dünya Turizm Günü",
            # EKİM
            ("October", 1): "Dünya Yaşlılar Günü / Camiler ve Din Görevlileri Haftası Başlangıcı",
            ("October", 4): "Hayvanları Koruma Günü",
            ("October", 10): "Dünya Ruh Sağlığı Günü",
            ("October", 13): "Ankara'nın Başkent Oluşu",
            ("October", 14): "Dünya Standartlar Günü",
            ("October", 16): "Dünya Gıda Günü",
            ("October", 17): "Dünya Yoksullukla Mücadele Günü",
            ("October", 24): "Birleşmiş Milletler Günü",
            ("October", 29): "Cumhuriyet Bayramı",
            ("October", 31): "Dünya Tasarruf Günü",
            # KASIM
            ("November", 1): "Türk Harf Devrimi Haftası Başlangıcı",
            ("November", 7): "Türk Harf Devrimi Haftası Bitişi",
            ("November", 3): "Organ Nakli Haftası Başlangıcı",
            ("November", 9): "Organ Nakli Haftası Bitişi / Dünya Şehircilik Günü",
            ("November", 10): "Atatürk'ün Ölüm Günü / Atatürk Haftası Başlangıcı",
            ("November", 16): "Atatürk Haftası Bitişi",
            ("November", 14): "Dünya Diyabet Günü",
            ("November", 20): "Dünya Çocuk Hakları Günü",
            ("November", 22): "Diş Hekimleri Günü / Ağız ve Diş Sağlığı Haftası",
            ("November", 24): "Bugün 24 Kasım Öğretmenler günü olup bütün öğretmenlerimizin öğretmenler gününü kutlar sevgi ve saygıyla selamlıyorum. .",
            ("November", 25): "Kadına Yönelik Şiddete Karşı Uluslararası Mücadele Günü",
            # ARALIK
            ("December", 1): "Dünya AİDS Günü",
            ("December", 2): "Köleliğin Yasaklanması Günü",
            ("December", 3): "Dünya Özürlüler Günü / Vakıflar Haftası Başlangıcı",
            ("December", 4): "Dünya Madenciler Günü",
            ("December", 5): "Kadın Hakları Günü",
            ("December", 7): "Uluslararası Sivil Havacılık Günü",
            ("December", 10): "Dünya İnsan Hakları Günü / İnsan Hakları Haftası Başlangıcı",
            ("December", 18): "İnsan Hakları Haftası Bitişi / Tutum, Yatırım ve Türk Malları Haftası Bitişi",
            ("December", 12): "Tutum, Yatırım ve Türk Malları Haftası Başlangıcı / Yoksullarla Dayanışma Haftası Başlangıcı",
            ("December", 18): "Tutum, Yatırım ve Türk Malları Haftası Bitişi / Yoksullarla Dayanışma Haftası Bitişi",
            ("December", 21): "Dünya Kooperatifçilik Günü",
            ("December", 27): "Atatürk'ün Ankara'ya Gelişi",
        }
        anlam = gunler_ve_anlamlari.get((ay, gun), "Bugün özel bir gün değil")
        self.konus("Bugünün anlamı: " + anlam) 
    def ceviri_yap(self, komut=None):
        """
        Çeviri modu: 
        - Hangi dilden hangi dile sorusu
        - Kelime söylemesini ister
        - Çeviriyi yapar
        - Çıkış komutu
        """
        self.konus("Hangi dilden hangi dile çevirmek istersin? Örne: ingilizce türkçe")
        self.awaiting_ceviri = True
        self.ceviri_step = 1
        self.ceviri_kaynak = None
        self.ceviri_hedef = None
        return

    def process_ceviri_response(self, komut):
        """Çeviri işlemini adım adım işle"""
        import re

        try:
            if not komut:
                return

            text = str(komut).strip().lower()
            import unicodedata
            text = unicodedata.normalize("NFD", text)
            if text in ("çıkış", "cikis", "dur", "bitti", "kapat"):
                self.konus("Çeviri modu kapatıldı.")
                self.awaiting_ceviri = False
                self.ceviri_step = None
                self.ceviri_kaynak = None
                self.ceviri_hedef = None
                return

            step = getattr(self, "ceviri_step", None)

            if step == 1:
                dil_kodlari = {
                    "türkçe": "tr", "turkce": "tr",
                    "ingilizce": "en", "ingılızce": "en",
                    "almanca": "de", "französizca": "fr", "fransızca": "fr",
                    "ispanyolca": "es", "italyanca": "it", "italyanca": "it",
                    "çince": "zh", "cinese": "zh",
                    "japonca": "ja", "korece": "ko",
                    "rusça": "ru", "rusca": "ru",
                    "arapça": "ar", "arapca": "ar",
                    "portekizce": "pt", "hollandaca": "nl"
                }

                satirlar = re.split(r'[,\s\-]+', text)
                bulunan_diller = []

                for satir in satirlar:
                    satir = unicodedata.normalize("NFD", satir.strip())
                    for dil_key in dil_kodlari:
                        if unicodedata.normalize("NFD", dil_key) == satir: bulunan_diller.append((dil_key, dil_kodlari[dil_key])); break

                if len(bulunan_diller) < 2:
                    self.konus("Lütfen iki dil söyle. Örneğin: ingilizce türkçe")
                    return

                self.ceviri_kaynak = bulunan_diller[0][1]
                self.ceviri_hedef = bulunan_diller[1][1]   

                self.konus(f"{bulunan_diller[0][0]}'den {bulunan_diller[1][0]}'ye çevirmeye başlayacağız. Çevirelecek kelimeyi söyle yada 'çıkış' de.")
                self.ceviri_step = 2
                self.awaiting_ceviri = True
                return

            if step == 2:
                if text in ("çıkış", "cikis", "dur", "bitti", "kapat"):
                    self.konus("Çeviri modu kapatıldı.")
                    self.awaiting_ceviri = False
                    self.ceviri_step = None
                    self.ceviri_kaynak = None
                    self.ceviri_hedef = None
                    return

                kelime = text.strip()
                if not kelime or len(kelime) < 1:
                    self.konus("Geçerli bir kelime söyle.")
                    return

                try:
                    self.permissions.check(Permission.WEB)
                    ceviri = GoogleTranslator(
                        source=self.ceviri_kaynak,
                        target=self.ceviri_hedef
                    ).translate(kelime)

                    self.konus(f"{kelime} → {ceviri}")
                    self.konus("Başka kelime söyle yada 'çıkış' de.")
             
                    self.awaiting_ceviri = True
                    self.ceviri_step = 2
                    return

                except PermissionDeniedError as error:
                    self.konus(f"Çeviri için web izni gerekli: {error}")
                    self.awaiting_ceviri = False
                    self.ceviri_step = None
                    return
                except Exception:
                    self.konus("Çeviri servisi şu an yanıt veremiyor. Başka kelime söyle.")
                    self.awaiting_ceviri = True
                    self.ceviri_step = 2
                    return

        except Exception as e:
            self.konus(f"Çeviri işlem hatası: {e}")
            self.awaiting_ceviri = False
            self.ceviri_step = None  
    def altin_piyasasi(self, komut=None):
        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as error:
            self.konus(f"Altın fiyatları için web izni gerekli: {error}")
            return
        import re
        import requests
        from bs4 import BeautifulSoup
        from statistics import median
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        sites = [
            ("doviz.com - gram", "https://www.doviz.com/altin/gram-altin"),
            ("bigpara", "https://bigpara.hurriyet.com.tr/altin/gram-altin/"),
            ("doviz.com - genel", "https://www.doviz.com/altin"),
            ("bloomberght", "https://www.bloomberght.com/altin")
        ]
        num_pattern = re.compile(r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?')
        def normalize_number(token):
            if not token:
                return None
            s = token.strip().replace(" ", "")
            if "." in s and "," in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            try:
                return float(re.search(r'\d+(?:\.\d+)?', s).group(0))
            except:
                return None
        def scrape(url):
            try:
                r = requests.get(url, headers=headers, timeout=8)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.get_text(" ", strip=True) 
                for m in re.finditer(r'(' + num_pattern.pattern + r')\s*(?:TL|₺|lira)?\s*(?:\/\s*)?(?:gram|gr)\b', text, re.I):
                    val = normalize_number(m.group(1))
                    if val and val > 100:  
                        return round(val, 2)
                for m in re.finditer(r'(?:gram|gr)\b.{0,40}?(' + num_pattern.pattern + r')|(' + num_pattern.pattern + r').{0,40}?(?:gram|gr)\b', text, re.I | re.S):
                    tok = m.group(1) or m.group(2)
                    val = normalize_number(tok)
                    if val and val > 100:
                        return round(val, 2)
                for cls in ("value", "price", "kur", "ticker", "last", "text--left", "text--right", "price--value", "fiyat"):
                    el = soup.find(attrs={"class": re.compile(cls, re.I)})
                    if el:
                        v = normalize_number(el.get_text(" ", strip=True))
                        if v and v > 100:
                            return round(v, 2)
                nums = [normalize_number(n) for n in num_pattern.findall(text)]
                nums = [n for n in nums if n and 300 <= n <= 200000]
                if nums:
                    return round(median(nums), 2)
            except:
                return None
            return None
        found = []
        for name, url in sites:
            value = scrape(url)
            if value is not None:
                found.append((name, value))
        vals = [v for _, v in found if 300 <= v <= 200000]
        if vals:
            chosen = round(median(vals), 2)
            kaynaklar = " | ".join(f"{n}: {v}" for n, v in found)
            self.konus(f"Gram altın (kaynak örnekleri) — {kaynaklar}")
            self.konus(f"Tahmini gram altın: {chosen} TL")
            return
        if found:
            self.konus("Bazı kaynaklardan veri alındı ama değerler tutarsız: " +
                   ", ".join(f"{n}:{v}" for n, v in found))
        else:
            self.konus("Altın fiyatları alınamadı. Sitelerin yapısı değişmiş olabilir veya istek engellenmiş olabilir.")
        self._web_adresi_ac("https://www.doviz.com/altin/gram-altin", "Güncel altın fiyatları")
    def bugun_ne_var(self): 
        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as error:
            self.konus(f"Haberler için web izni gerekli: {error}")
            return
        import requests
        from bs4 import BeautifulSoup
        import xml.etree.ElementTree as ET
        from urllib.parse import urljoin, unquote
        import re
        import threading
        import time
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        def pick_link_from_item(item):
            link = None
            if item.find("link") is not None and item.find("link").text:
                link = item.find("link").text.strip()
            src = item.find("source")
            if src is not None and src.get("url"):
                cand = src.get("url").strip()
                if cand:
                    link = cand
            guid = item.find("guid")
            if guid is not None and guid.text and "http" in (guid.text or ""):
                gtxt = guid.text.strip()
                if gtxt.startswith("http"):
                    link = gtxt
            desc = None
            dtag = item.find("description")
            if dtag is not None and dtag.text:
                desc = dtag.text
                try:
                    soupd = BeautifulSoup(desc, "html.parser")
                    a = soupd.find("a", href=True)
                    if a:
                        href = a["href"].strip()
                        if href.startswith("/"):
                            href = urljoin(link or "https://news.google.com", href)
                        href = unquote(href)
                        if href and "google" not in href:
                            link = href
                except Exception:
                    pass
            try:
                raw = (dtag.text or "") if dtag is not None else ""
                m = re.search(r"https?://[^\s'\"<>()]+", raw)
                if m:
                    u = unquote(m.group(0).rstrip("),.;\"'"))
                    if "google" not in u:
                        link = u
            except Exception:
                pass
            return link
            pass
        def resolve_possible_original(link):
            if not link:
                return link
            try:
                rr = requests.get(link, headers=headers, timeout=10, allow_redirects=True)
            except Exception:
                return link
            final = rr.url or link
            text = rr.text or ""
            if "news.google" not in final and len(text.strip()) > 800 and "Google News" not in text:
                try:
                    soup = BeautifulSoup(text, "html.parser")
                    og = soup.find("meta", property="og:url") or soup.find("meta", attrs={"name": "og:url"})
                    if og and og.get("content"):
                        cand = og["content"].strip()
                        if cand and "google" not in cand:
                            return cand
                    can = soup.find("link", rel="canonical")
                    if can and can.get("href"):
                        cand = can["href"].strip()
                        if cand and "google" not in cand:
                            return cand
                except Exception:
                    pass
                return final
            try:
                candidates = []
                soup = BeautifulSoup(text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if href.startswith("/"):
                        href = urljoin(final, href)
                    href = unquote(href)
                    if href.startswith("http") and "google" not in href and "accounts.google" not in href:
                        candidates.append(href)
                for c in candidates:
                    if "google" not in c:
                        return c
            except Exception:
                pass
            return final
            pass
        def worker():
            headlines = []
            links = []
            blacklist = ["diken", "sozcu", "rudaw"]
            try:
                rss = "https://news.google.com/rss?hl=tr&gl=TR&ceid=TR:tr"
                r = requests.get(rss, headers=headers, timeout=8)
                r.raise_for_status()
                root = ET.fromstring(r.content)
                items = root.findall(".//item")[:10]
                for it in items:
                    title = (it.find("title").text or "").strip() if it.find("title") is not None else None
                    link = pick_link_from_item(it)
                    if title and link:
                        if not any(b in link.lower() for b in blacklist):
                            headlines.append(title)
                            links.append(link)
            except Exception:
                pass
            if len(headlines) < 6:
                try:
                    url = "https://www.hurriyet.com.tr/gundem/"
                    r = requests.get(url, headers=headers, timeout=8)
                    r.raise_for_status()
                    soup = BeautifulSoup(r.text, "html.parser")
                    found = []
                    found_links = []
                    for tag in ("h3", "h2", "h1"):
                        for h in soup.find_all(tag):
                            t = h.get_text().strip()
                            if not t or len(t) < 10:
                                continue
                            a = h.find_parent("a") or h.find("a") or h.find_next("a")
                            href = None
                            if a and a.get("href"):
                                href = urljoin("https://www.hurriyet.com.tr", a.get("href"))
                            if t not in found and href:
                                if not any(b in href.lower() for b in blacklist):
                                    found.append(t)
                                    found_links.append(href)
                            if len(found) >= 10:
                                break
                        if len(found) >= 10:
                            break
                    for t, l in zip(found, found_links):
                        if len(headlines) >= 10:
                            break
                        if t not in headlines:
                            headlines.append(t)
                            links.append(l)
                except Exception:
                    pass
            if not headlines:
                self.konus("Haber alınamadı. İnternet bağlantınızı veya siteleri kontrol edin.")
                return
            resolved = []
            for l in links[:10]:
                if not l:
                    resolved.append(None)
                    continue
                try:
                    resolved.append(resolve_possible_original(l))
                except Exception:
                    resolved.append(l)
            self.haber_basliklari = []
            self.links = []
            for title, link in zip(headlines, resolved):
                if title and link:
                    if not any(b in link.lower() for b in blacklist):
                        self.haber_basliklari.append(title)
                        self.links.append(link)
            mesaj = "Bugünün haber başlıkları:\n"
            for i, h in enumerate(self.haber_basliklari, 1):
                mesaj += f"{i}. {h}\n"
            if hasattr(self, "gui"):
                try:
                    self.gui.root.after(0, self.gui.mesaj_ekle, self.isim, mesaj)
                except Exception:
                    pass
            self.reading_haber = True
            self.stop_speaking = False 
        
            try:
                self.konus("Günün öne çıkan haberleri:")

                for i, h in enumerate(self.haber_basliklari, 1):

                    if self.stop_speaking:
                        print("🛑 OKUMA DURDURULDU")
                        self.stop_speaking = False
                        self.reading_haber = False
                        self.konus("Detaylı okumamı istediğiniz haber numarası var mı?")
                        self.awaiting_haber_detayi = True
                        return 

                    self.konus(f"{i}. {h}")
                    time.sleep(0.15)

                if not self.stop_speaking:
                    kaynak_mesaji = "Kaynak linkleri:\n"
                    for i, link in enumerate(self.links, 1):
                        kaynak_mesaji += f"{i}. {link or 'Bulunamadı'}\n"

                    if hasattr(self, "gui"):
                        try:
                            self.gui.root.after(0, self.gui.mesaj_ekle, self.isim, kaynak_mesaji)
                        except Exception:
                            pass
 
                    self.konus("Detaylı okumamı istediğiniz haber numarası var mı? (örn. 2 veya 'hayır')")
                    self.awaiting_haber_detayi = True

            finally:
                self.reading_haber = False
                self.stop_speaking = False

        threading.Thread(target=worker, daemon=True).start()
    def dinle(self):
        if not self.permissions.is_allowed(Permission.WEB):
            logger.info("Bulut ses tanıma web izni kapalı olduğu için çalıştırılmadı")
            return "HATA"
        sr_recognizer = sr.Recognizer()
        sr_recognizer.energy_threshold = 4000
        fs = 44100  
        saniye = 5  
        print("Dinliyorum...")    
        try:
            ses = sd.rec(int(saniye * fs), samplerate=fs, channels=1, dtype=np.int16)
            sd.wait()  
            ses = np.asarray(ses, dtype=np.float32)
            ses = ses / 32768.0  
            audio_data = sr.AudioData(
                (ses * 32768).astype(np.int16).tobytes(),
                fs,
                2
            ) 
            try:
                text = sr_recognizer.recognize_google(audio_data, language="tr-TR")
                print("Siz (sesli):", text)
                return text.lower()
            except sr.UnknownValueError:
                print("Sesi anlayamadım.")
                return "ANLAŞILMADI"
            except sr.RequestError as e:
                print(f"Google Speech API hatası: {e}")
                return "HATA"
        except Exception as e:
            print(f"Dinleme hatası: {e}")
            return "HATA"

    _EK_LISTESI = ["dir", "dır", "dur", "dür", "tir", "tır", "tur", "tür"]

    def _ek_ayikla(self, kelime):
        """'meyvedir' -> 'meyve', 'hayvandır' -> 'hayvan' gibi ekleri ayıklar."""
        k = (kelime or "").strip().lower()
        for ek in self._EK_LISTESI:
            if k.endswith(ek) and len(k) > len(ek) + 1:
                return k[: -len(ek)]
        return k

    def bilgi_ogren(self, cumle):
        """'X bir Y'dir' / 'X Y'dir' kalıbındaki cümleleri kalıcı bilgi olarak kaydeder.
        Kaydedebildiyse True, kalıba uymuyorsa False döner."""
        if not cumle:
            return False
        s = str(cumle).strip()
        if s.endswith("?"):
            return False
        s_temiz = s.rstrip(".!").strip()
        if not s_temiz:
            return False

        import re
        if re.search(r"\b(kimdir|nedir|nasıl|nasil|hangi|nerede|ne zaman|kaç|kac)\b", s_temiz, flags=re.IGNORECASE):
            return False
        if re.search(r"\b(mi|mı|mu|mü|midir|mıdır|mudur|müdür)\b\s*$", s_temiz, flags=re.IGNORECASE):
            return False

        m = re.match(r"^(.+?)\s+bir\s+(\S+)$", s_temiz, flags=re.IGNORECASE)
        if not m:
            m = re.match(r"^(.+?)\s+(\S+)$", s_temiz, flags=re.IGNORECASE)
        if not m:
            return False

        konu_ham, tanim_ham = m.group(1).strip(), m.group(2).strip()
        tanim = self._ek_ayikla(tanim_ham)
        if tanim == tanim_ham.lower():
            return False
        if not konu_ham or not tanim:
            return False
        konu = konu_ham.lower()

        try:
            init_db()
            cursor.execute(
                "INSERT INTO ogrenilen_bilgiler (konu, tanim, tam_cumle, tarih) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(konu) DO UPDATE SET tanim=excluded.tanim, tam_cumle=excluded.tam_cumle, tarih=excluded.tarih",
                (konu, tanim, s_temiz, datetime.now().isoformat())
            )
            conn.commit()
        except Exception as e:
            print(f"[HATA] Bilgi kaydedilemedi: {e}")
            return False

        self.konus(f"Anladım, öğrendim: {konu_ham} bir {tanim}dir.")
        return True

    def bilgi_getir(self, konu):
        """Verilen konu için daha önce öğrenilmiş tanımı döndürür, yoksa None."""
        try:
            init_db()
            cursor.execute("SELECT tanim FROM ogrenilen_bilgiler WHERE konu = ?", (konu.lower().strip(),))
            sonuc = cursor.fetchone()
            return sonuc[0] if sonuc else None
        except Exception as e:
            print(f"[HATA] Bilgi okunamadı: {e}")
            return None

    def bilgi_sorusuna_cevap_ver(self, soru):
        """'X Y midir?' / 'X nedir?' gibi soruları öğrenilen bilgilerden yanıtlar.
        Soru kalıbına uymuyorsa None döner (böylece normal akışa devam edilir)."""
        if not soru:
            return None
        s = str(soru).strip().rstrip("?").strip()
        if not s:
            return None

        import re

        m = re.match(r"^(.+?)\s+nedir$", s, flags=re.IGNORECASE)
        if m:
            konu_ham = m.group(1).strip()
            tanim = self.bilgi_getir(konu_ham)
            if tanim:
                return f"{konu_ham.capitalize()} bir {tanim}dir."

            return None

        m = re.match(
            r"^(.+?)\s+(?:bir\s+)?(\S+?)\s+(midir|mıdır|mudur|müdür|mi|mı|mu|mü)$",
            s, flags=re.IGNORECASE
        )
        if not m:
            return None

        konu_ham, tanim_ham = m.group(1).strip(), m.group(2).strip()
        sorulan_tanim = self._ek_ayikla(tanim_ham) if self._ek_ayikla(tanim_ham) != tanim_ham.lower() else tanim_ham.lower()
        kayitli_tanim = self.bilgi_getir(konu_ham)

        if kayitli_tanim is None:
            return None

        if kayitli_tanim == sorulan_tanim or kayitli_tanim in sorulan_tanim or sorulan_tanim in kayitli_tanim:
            return f"Evet, {konu_ham} bir {kayitli_tanim}dir."
        else:
            return f"Hayır, {konu_ham} bir {kayitli_tanim}dir, {sorulan_tanim} değildir."

    def sohbet_et(self, komut=None):
        user_text = self._giris_metni(komut)
        self._giris_temizle()

        try:
            self.permissions.check(Permission.WEB)
            reply = self.llm_controller.generate(
                user_text,
                task_type="chat",
                system_prompt=(
                    "Sen ANKA adlı Türkçe kişisel asistansın. Kısa, doğal ve yararlı yanıt ver. "
                    "Kullanıcı duygu paylaşırsa yargılamadan dinle ve uygun, açık uçlu bir soru sor."
                ),
            )
            self.konus(reply)
        except PermissionDeniedError as error:
            self.konus(f"Dil modeli için web izni gerekli: {error}")
        except ModelServiceError as error:
            logger.warning("LLM sohbeti tamamlanamadı: %s", type(error).__name__)
            self.konus("Şu an dil modeli yanıtı alınamadı. Biraz sonra tekrar deneyebilir misin?")

    def onceden_tanimli_cevap_ver(self, komut):
        for anahtar, cevap in self.onceden_tanimli_cevaplar.items():
            if anahtar in komut:
                self.konus(cevap)
                return True
        return False
    def selamla(self, komut=None):
        self.konus(f"Merhaba {self.isim}, Ben Anka.. Size nasıl yardımcı olabilirim?")
    def muzik_ac(self, komut=None):
        musik_folder = r"/home/meged/Desktop/müzik"
        mp3s = []
        try:
            if os.path.exists(musik_folder):
                for f in os.listdir(musik_folder):
                    p = os.path.join(musik_folder, f)
                    if os.path.isfile(p) and f.lower().endswith(".mp3"):
                        mp3s.append(p)
            else:
                self.konus(f"Klasör bulunamadı: {musik_folder}")
                return
        except Exception as e:
            self.konus(f"Klasör okuma hatası: {e}")
            return
        
        if not mp3s:
            self.konus("Belirtilen klasörde mp3 dosyası bulunamadı.")
            return    
        self.muzik_list = mp3s
        isimler = [os.path.splitext(os.path.basename(p))[0] for p in mp3s]
        mesaj = "Müzik klasöründeki şarkılar:\n" + "\n".join(f"{i+1}. {n}" for i, n in enumerate(isimler))
        self.konus(mesaj)
        self.konus("Hangi müziği açmamı istiyorsun? İsim ya da numara söyle.")
        self.awaiting_muzik = True
    def process_muzik_response(self, cevap):
        if not getattr(self, "awaiting_muzik", False):
            return
        if not cevap:
            return
        import re
        text = str(cevap).strip().lower()
        if text in ("hayır", "hayir", "iptal", "vazgeç", "vazgec", "olmaz"):
            self.konus("Tamam, müzik seçimi iptal edildi.")
            self.awaiting_muzik = False
            return
        def text_to_number(s):
            s = s.lower()
            tokens = re.findall(r"[\wçğıöşü]+", s, flags=re.UNICODE)
            mapping = {
                "bir": 1, "iki": 2, "üç": 3, "uc": 3, "dört": 4, "dort": 4,
                "beş": 5, "bes": 5, "altı": 6, "alti": 6, "yedi": 7,
                "sekiz": 8, "dokuz": 9, "on": 10, "onbir": 11, "on iki": 12
            }
            for t in tokens:
                if t.isdigit():
                    try:
                        return int(t)
                    except:
                        pass
                if t in mapping:
                    return mapping[t]
                for k, v in mapping.items():
                    if t.startswith(k):
                        return v
            return None
        sel = None
        num = None
        try:
            num = int(text.split()[0])
        except Exception:
            num = text_to_number(text)

        if isinstance(num, int) and 1 <= num <= len(getattr(self, "muzik_list", [])):
            sel = self.muzik_list[num - 1]

        if sel is None:
            for p in getattr(self, "muzik_list", []):
                name = os.path.splitext(os.path.basename(p))[0].lower()
                if text in name or any(tok in name for tok in text.split()):
                    sel = p
                    break
        if sel is None:
            self.konus("Seçiminizi anlayamadım. Lütfen numara veya tam/parsiyel isim söyleyin.")
            return
        try:
            mesaj = f"Çalıyor: {os.path.basename(sel)}. Müzik kapatmak için 'kapat' veya 'müziği kapat' söyleyin."
            self.konus(mesaj)
        except Exception:
            pass
        try:
            pygame.mixer.music.load(sel)
            pygame.mixer.music.play()
            self.current_music = sel
            try:
                import dijidost_entegrasyon
                dijidost_entegrasyon.muzik_durumu_bildir(
                    os.path.splitext(os.path.basename(sel))[0], "Yerel müzik", "ANKA"
                )
            except (ImportError, OSError, ValueError):
                logger.warning("Yerel müzik durumu arayüze aktarılamadı")
        except Exception as e:
            self.konus(f"Müzik çalınamadı: {e}")
        finally:
            self.awaiting_muzik = False

    def youtube_sarki_ac(self, komut=None):
        """YouTube'da şarkı arama"""
        self.konus("Hangi şarkıyı YouTube'da açmamı istiyorsun?")
        self.awaiting_youtube_sarki = True
    
    def process_youtube_sarki(self, cevap):
        """YouTube'da şarkı ara ve ilk videoyu aç"""
        if not getattr(self, "awaiting_youtube_sarki", False):
            return
        if not cevap or str(cevap).strip().lower() in ("hayır", "hayir", "iptal", "vazgeç"):
            self.konus("Tamam, işlem iptal edildi.")
            self.awaiting_youtube_sarki = False
            return
        
        sarki_adi = str(cevap).strip()
        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as error:
            self.konus(str(error))
            self.awaiting_youtube_sarki = False
            return

        self.konus(f"'{sarki_adi}' YouTube'da aranıyor...")
        
        try:
            import webbrowser
            from yt_dlp import YoutubeDL

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'default_search': 'ytsearch1' 
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(sarki_adi, download=False)
                if result and 'entries' in result and len(result['entries']) > 0:
                    video = result['entries'][0]

                    video_id = video.get('id')
                    if video_id:
                        video_url = f"https://www.youtube.com/watch?v={video_id}&autoplay=1"
                        if not webbrowser.open(video_url):
                            self.konus("YouTube bulundu fakat varsayılan tarayıcı açma isteğini reddetti.")
                            return
                        try:
                            import dijidost_entegrasyon
                            dijidost_entegrasyon.muzik_durumu_bildir(
                                video.get("title") or sarki_adi,
                                video.get("uploader") or "YouTube",
                                "YouTube Music",
                            )
                        except (ImportError, OSError, ValueError):
                            logger.warning("YouTube müzik durumu arayüze aktarılamadı")
                        self.konus(f"'{sarki_adi}' için YouTube açma isteği işletim sistemine iletildi.")
                    else:
                        self.konus(f"'{sarki_adi}' URL bulunamadı.")
                else:
                    self.konus(f"'{sarki_adi}' bulunamadı. Lütfen başka bir şarkı dene.")
        except Exception as e:
            self.konus(f"YouTube'da arama başarısız: {str(e)[:50]}")
        finally:
            self.awaiting_youtube_sarki = False


    def muzik_kapat(self, komut=None):
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except Exception:
                pass
            if hasattr(self, "current_music"):
                ad = os.path.basename(self.current_music)
                self.konus(f"{ad} durduruldu.")
                del self.current_music
            else:
                self.konus("Müzik durduruldu.")
        except Exception as e:
            self.konus(f"Müzik kapatılamadı: {e}")
    def saat_soyle(self):
        self.konus("Şu an saat: " + datetime.now().strftime("%H:%M"))
        try:
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now()(ZoneInfo("Europe/Istanbul"))
        except Exception:
            try:
                import pytz
                now = datetime.datetime.now()(pytz.timezone("Europe/Istanbul"))
            except Exception:
                now = datetime.now()
        self.konus("Şu an saat (İstanbul): " + now.strftime("%H:%M"))
    def tarih_soyle(self):
        tarih_str = self._format_tarih_turkce()
        self.konus("Bugün tarih: " + tarih_str)
        import datetime
        dt = datetime.now()
        months = {
            1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
            7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
        }
        tarih_str = f"{dt.day} {months.get(dt.month, '')} {dt.year}"
        self.konus("Bugün tarih: " + tarih_str)
    def arama_yap(self, komut=None):
        query = self._giris_metni(komut)
        if not query:
            self.konus("Aramak istediğin konuyu yaz.")
            return
        self._web_adresi_ac(
            f"https://www.google.com/search?q={quote_plus(query)}",
            f"'{query}' için arama",
        )
    def gorev_ekle(self, komut=None):
        gorev = self._giris_metni(komut)
        self._giris_temizle()
        if not gorev:
            gorev = input("Görev girin: ")
        self.gorevler.append(gorev)
        self.konus(f"'{gorev}' görevi eklendi.")
        self.hafizayi_kaydet()  
    def ip_adresim(self):
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        self.konus(f"Bilgisayarınızın IP adresi: {ip}")
    def rastgele_kelime(self):
        kelimeler = ["elma", "armut", "kitap", "araba", "güneş", "yıldız", "çay", "kahve"]
        self.konus(f"Rastgele kelime: {random.choice(kelimeler)}")
    def gorevleri_listele(self):
        if self.gorevler:
            self.konus("Görevlerin şunlar:")
            for i, gorev in enumerate(self.gorevler):
                self.konus(f"{i+1}. {gorev}")
        else:
            self.konus("Hiç görev eklenmemiş.")
    def alisveris_ekle(self):
        self.konus("Ne almak istiyorsunuz? Ürün adını söyleyin.")
        self.awaiting_alisveris = True
        return
        try:
            if not cevap:
                return
            text = str(cevap).strip()
            lower = text.lower()
            if lower in ("hayır", "hayir", "iptal", "vazgeç", "vazgec", "olmaz","istemiyorum"):
                self.konus("Tamam, alışveriş eklemeyi iptal ettim.")
                self.awaiting_alisveris = False
                return
            self.alisveris_listesi.append(text)
            self.hafizayi_kaydet()
            self.konus(f"'{text}' alışveriş listenize eklendi.")
            self.awaiting_alisveris = False    
        except Exception as e:
            self.konus(f"Alışveriş işleme hatası: {e}")
            self.awaiting_alisveris = False  
        self.konus("Ne almak istiyorsunuz? Ürün adını söyleyin.")
        self.awaiting_alisveris = True
        return
    def process_alisveris_response(self, komut):
        try:
            if not komut:
                return
            text = str(komut).strip()
            lower = text.lower()
            if lower in ("hayır", "hayir", "iptal", "vazgeç", "vazgec", "olmaz"):
                self.konus("Tamam, alışveriş eklemeyi iptal ettim.")
                self.awaiting_alisveris = False
                return
            self.alisveris_listesi.append(text)
            self.hafizayi_kaydet()
            self.konus(f"'{text}' alışveriş listenize eklendi.")
            self.awaiting_alisveris = False
        except Exception as e:
            self.konus(f"Alışveriş işleme hatası: {e}")
            self.awaiting_alisveris = False
    def alisveris_goster(self):
        if self.alisveris_listesi:
            self.konus("Alışveriş listeniz şunlar:")
            for i, urun in enumerate(self.alisveris_listesi):
                self.konus(f"{i+1}. {urun}")
        else:
            self.konus("Alışveriş listenizde hiç ürün yok.")
    def faktoriyel_hesapla(self, komut=None):
        sayi = self._giris_metni(komut)
        self._giris_temizle()
        if sayi.isdigit():
            sonuc = 1
            for i in range(1, int(sayi)+1):
                sonuc *= i
            self.konus(f"{sayi}! = {sonuc}")
        else:
            self.konus("Lütfen geçerli bir sayı girin.")
    def yardim_goster(self):
        try:
            komut_listesi = list(self.komutlar.keys())
            mesaj = "Yapabileceğim bazı komutlar:\n" + "\n".join(f"- {k}" for k in komut_listesi[:40])
            self.konus(mesaj)
        except Exception as e:
            self.konus("Yardım gösterilemedi: " + str(e))    
    def karekok_hesapla(self, komut=None):
        sayi = self._giris_metni(komut)
        self._giris_temizle()
        try:
            sonuc = float(sayi) ** 0.5
            self.konus(f"{sayi} sayısının karekökü: {sonuc}")
        except:
            self.konus("Lütfen geçerli bir sayı girin.")
    def alisveris_listesi_goster(self):
        if self.alisveris_listesi:
            self.konus("Alışveriş listeniz şunlar:")
            for i, urun in enumerate(self.alisveris_listesi):
                self.konus(f"{i+1}. {urun}")
        else:
            self.konus("Alışveriş listesi boş.")
    def dosya_olustur(self, komut=None):
        dosya_adi = self._giris_metni(komut).strip()
        self._giris_temizle()
        if not dosya_adi:
            self.konus("Oluşturulacak dosyanın adını belirtin.")
            return
        request = dosya_adi if dosya_adi.casefold().startswith(("dosya oluştur", "dosya olustur")) else f"dosya oluştur {dosya_adi}"
        result = self.task_agent.submit(request, self._guvenli_gorev_calistir)
        self.konus(result.message)
    def dosya_ac(self, komut=None):
        dosya_adi = self._giris_metni(komut).strip()
        self._giris_temizle()
        if not dosya_adi:
            self.konus("Açılacak dosyanın yolunu belirtin.")
            return
        request = dosya_adi if dosya_adi.casefold().startswith(("dosya aç", "dosya ac")) else f"dosya aç {dosya_adi}"
        result = self.task_agent.submit(request, self._guvenli_gorev_calistir)
        self.konus(result.message)
    def hatirlatici_kur(self, komut=None):
        self.konus("Neyi hatırlatayım? Söyleyin. (Örn: Kardeşimin doğum günü, Toplantı, Spor antrenmanı vb.)")
        self.awaiting_hatirlatici = True
        self.hatirlatici_step = 1  
        self.hatirlatici_konu = None
        return
    def process_hatirlatici_response(self, komut):
        import re
        import datetime
        import threading
        try:
            if not komut:
                return
            
            text = str(komut).strip()
            lower = text.lower()
            
            if lower in ("hayır", "hayir", "iptal", "vazgeç", "vazgec", "olmaz"):
                self.konus("Tamam, hatırlatıcı kurulumu iptal edildi.")
                self.awaiting_hatirlatici = False
                self.hatirlatici_step = None
                self.hatirlatici_konu = None
                return
            step = getattr(self, "hatirlatici_step", None)
            if step == 1:
                self.hatirlatici_konu = text
                self.konus(f"'{text}' için — Saat kaçta hatırlatayım? (Örn: '8', '14:30', 'yarın 8', 'pazartesi 9' vb.)")
                self.hatirlatici_step = 2
                self.awaiting_hatirlatici = True
                return
            if step == 2:
                konu = self.hatirlatici_konu or "Hatırlatıcı"
                
                def parse_time_advanced(s):
                    s_lower = s.lower()
                    
                    if "yarın" in s_lower or "yarin" in s_lower:
                        m = re.search(r'(\d{1,2})\s*[:\.]\s*(\d{1,2})|(\d{1,2})(?=\D*$)', s)
                        if m:
                            h = int(m.group(1) or m.group(3))
                            mi = int(m.group(2)) if m.group(2) else 0
                            delta_days = 1
                            return (h, mi, delta_days, "yarın")
                    gun_map = {
                        "pazartesi": 0, "salı": 1, "çarşamba": 2, "perşembe": 3,
                        "cuma": 4, "cumartesi": 5, "pazar": 6,
                        "sali": 1, "carsamba": 2, "persembe": 3, "cumartesi": 5
                    }
                    for gun_tr, gun_idx in gun_map.items():
                        if gun_tr in s_lower:
                            m = re.search(r'(\d{1,2})\s*[:\.]\s*(\d{1,2})|(\d{1,2})(?=\D*$)', s)
                            if m:
                                h = int(m.group(1) or m.group(3))
                                mi = int(m.group(2)) if m.group(2) else 0
                                today_idx = datetime.now().weekday()
                                delta = (gun_idx - today_idx) % 7
                                if delta == 0:
                                    delta = 7  
                                return (h, mi, delta, gun_tr)
                    m = re.search(r'(\d{1,2})\s*[:\.]\s*(\d{1,2})|(\d{1,2})(?=\D*$)', s)
                    if m:
                        h = int(m.group(1) or m.group(3))
                        mi = int(m.group(2)) if m.group(2) else 0
                        return (h, mi, 0, None)  
                    return None
                parsed = parse_time_advanced(text)
                if not parsed:
                    self.konus("Saati anlayamadım. Lütfen örnek: '8', '14:30', 'yarın 9', 'pazartesi 10' gibi söyleyin.")
                    return
                hour, minute, delta_days, day_info = parsed
                if hour < 0 or hour > 23 or minute < 0 or minute > 59:
                    self.konus("Geçersiz saat bilgisi. 0-23 arası saat ve 0-59 arası dakika girin.")
                    return
                now = datetime.now()
                target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if delta_days > 0:
                    target = target + datetime.timedelta(days=delta_days)
                elif target <= now:
                    target = target + datetime.timedelta(days=1)
                delta_seconds = (target - now).total_seconds()
                def hatirlatici_callback():
                    try:
                        self.konus(f"Hatırlatıcı: {konu}")
                    except Exception:
                        pass
                timer = threading.Timer(delta_seconds, hatirlatici_callback)
                timer.daemon = True
                timer.start()
                self.hatirlatici_timer = timer
                self.hatirlatici_time = target.isoformat()
                
                gun_str = day_info if day_info else "bugün"
                mesaj = f"Tamam. '{konu}' için {gun_str} saat {hour:02d}:{minute:02d} hatırlatması ayarlandı."
                mesaj += f"\n(İlk hatırlatma: {target.strftime('%Y-%m-%d %H:%M')})"
                self.konus(mesaj)
                self.awaiting_hatirlatici = False
                self.hatirlatici_step = None
                self.hatirlatici_konu = None
                return
        except Exception as e:
            self.konus(f"Hatırlatıcı kurulum hatası: {e}")
            self.awaiting_hatirlatici = False
            self.hatirlatici_step = None
            self.hatirlatici_konu = None
    def not_al(self):
        self.konus("Hangi notu almak istiyorsunuz? Söyleyin.")
        self.awaiting_not = True  
    def process_not_response(self, cevap):
        try:
            if not cevap:
                return
            text = str(cevap).strip()
            lower = text.lower()
            if lower in ("hayır", "hayir", "iptal", "vazgeç", "vazgec", "olmaz"):
                self.konus("Tamam, not almayı iptal ettim.")
                self.awaiting_not = False
                return
            self.notlar.append(text)
            self.hafizayi_kaydet()
            self.konus(f"Not kaydedildi: '{text}'")
            self.awaiting_not = False
        except Exception as e:
            self.konus(f"Not işleme hatası: {e}")
            self.awaiting_not = False
    def notlari_goster(self):
        if self.notlar:
            self.konus("Notlarınız şunlar:")
            for i, not_metni in enumerate(self.notlar):
                self.konus(f"{i+1}. {not_metni}")
        else:
            self.konus("Hiç not alınmamış.")
    def saka_yap(self):
        s = [
            "Neden bilgisayar çok iyi dans eder? Çünkü hard disk’i var!",
            "Bilgisayar neden ağrı hisseder? Çünkü byte’lar!",
            "Programcı neden denize girmez? Çünkü overflow olur!"
        ]
        self.konus(random.choice(s))
    def alarm_kur(self):
        saat = input("Alarm saatini HH:MM formatında girin: ")
        self.konus(f"{saat} için alarm kuruldu (simüle edildi).")
    
    def rastgele_sayi(self):
        self.konus(f"Rastgele sayı: {random.randint(0,1000)}")
    def so_zluk(self, komut=None):
        kelime = self._giris_metni(komut)
        self._giris_temizle()
        if not kelime:
            self.konus("Lütfen çevirmek istediğin kelimeyi yaz.")
            return
        try:
            self.permissions.check(Permission.WEB)
            ceviri = GoogleTranslator(source="auto", target="tr").translate(kelime)
            self.konus(f"{kelime} → {ceviri}")
        except PermissionDeniedError as error:
            self.konus(f"Sözlük/çeviri için web izni gerekli: {error}")
        except Exception:
            self.konus("Sözlük/çeviri servisi şu an yanıt veremiyor.")
    def hakkinda(self):
        self.konus("Ben ANKA, Türkçe konuşabilen kişisel yapay zeka asistanınım.")
    def _web_adresi_ac(self, url, aciklama):
        """Web erişimini izin ve işletim sistemi sonucuyla birlikte uygular."""
        try:
            self.permissions.check(Permission.WEB)
        except PermissionDeniedError as error:
            self.konus(str(error))
            return False

        try:
            opened = bool(webbrowser.open(url))
        except (OSError, ValueError) as error:
            logger.warning("Web adresi açılamadı (%s): %s", aciklama, type(error).__name__)
            self.konus(f"{aciklama} açılamadı. Varsayılan tarayıcı ayarını kontrol edin.")
            return False

        if not opened:
            self.konus(f"{aciklama} için tarayıcı açma isteği reddedildi.")
            return False
        self.konus(f"{aciklama} için tarayıcı açma isteği işletim sistemine iletildi.")
        return True

    def tarayici_ac(self):
        self._web_adresi_ac("https://www.google.com", "Tarayıcı")
    def youtube_ac(self):
        self._web_adresi_ac("https://www.youtube.com", "YouTube")
    def spotify_ac(self):
        self._web_adresi_ac("https://open.spotify.com", "Spotify")
    def google_harita(self):
        self._web_adresi_ac("https://www.google.com/maps", "Google Haritalar")
    def bilgisayar_bilgisi(self):
        self.konus(f"İşletim sistemi: {platform.system()} {platform.release()}")
        self.konus(f"Python versiyonu: {platform.python_version()}")
    def klasor_ac(self, komut=None):
        request = self._giris_metni(komut).strip()
        self._giris_temizle()
        if request.casefold() in {"klasör aç", "klasor ac"} or not request:
            self.konus("Açılacak klasörü belirtin. Örnek: 'klasör aç Belgeler'.")
            return
        request = request if request.casefold().startswith(("klasör aç", "klasor ac")) else f"klasör aç {request}"
        result = self.task_agent.submit(request, self._guvenli_gorev_calistir)
        self.konus(result.message)
    def gunluk_not(self):
        metin = input("Bugün için notunuzu yazın: ")
        self.konus(f"Günlük notunuz kaydedildi: {metin}")
    def sistem_durumu(self):
        self.konus(f"İşlemci: {platform.processor()}")
        self.konus(f"Sistem: {platform.system()} {platform.release()}")
    def bilgisayari_kapat(self):
        """Kapatma isteğini planlar; açık kullanıcı onayı olmadan çalıştırmaz."""
        sonuc = self.task_agent.submit("bilgisayarı kapat", self._guvenli_gorev_calistir)
        self.konus(sonuc.message)

    def benim_hakkimda_ne_biliyorsun(self, komut=None):
        """Kullanıcı tercihlerini, öğrenilen bilgileri ve görev geçmişini özetler."""
        summary = self.categorized_memory.get_user_summary()
        self.konus(summary)

    def gunluk_ozet_cikart(self, komut=None):
        """Günlük alınan notlar, tamamlanan görevler ve öğrenilen bilgilerin özetini sunar."""
        digest = self.daily_digest.generate_digest(notes=self.notlar, tasks=self.gorevler)
        self.konus(digest["report_text"])

    def kodlama_modu_tara(self, komut=None):
        """Geliştirici modu: Proje dosya yapısını ve bağımlılıkları analiz eder."""
        scan = self.developer_mode.scan_project()
        self.konus(f"Proje taraması tamamlandı: {scan['total_files']} dosya bulundu. "
                   f"Bağımlılık dosyaları: {', '.join(scan['dependency_files']) or 'Yok'}")

    def testleri_calistir(self, komut=None):
        """Projedeki otomatik testleri çalıştırır."""
        self.konus("Testler çalıştırılıyor...")
        res = self.developer_mode.run_tests()
        if res.get("success"):
            self.konus("✓ Tüm testler başarıyla geçti.")
        else:
            self.konus(f"✗ Test çalıştırmasında uyarı/hata: {res.get('error') or 'Ayrıntılar konsolda.'}")

    def guvenlik_paneli(self, komut=None):
        """Güvenlik ve izin paneli özetini ve audit loglarını görüntüler."""
        perms = self.security_center.get_permission_status()
        logs = self.security_center.get_audit_logs(limit=5)
        summary = ", ".join(f"{k}: {'açık' if v else 'kapalı'}" for k, v in perms.items())
        self.konus(f"Güvenlik Merkezi İzinleri: {summary}. Son güvenlik kayıtları sayısı: {len(logs)}")

    def eklentileri_listele(self, komut=None):
        """Modüler Skill / Plugin mimarisinde kayıtlı aktif yetenekleri listeler."""
        plugins = self.plugin_registry.list_plugins()
        mesaj = "Yüklü ANKA Skill / Plugin eklentileri:\n" + "\n".join(
            f"- {p['name']} (v{p['version']}): {p['description']}" for p in plugins
        )
        self.konus(mesaj)

    def cikis(self):
        try:
            self.konus("Asistan kapatılıyor. Görüşürüz!")
            if hasattr(self, "gui") and getattr(self.gui, "root", None):
                try:
                    self.gui.root.destroy()
                except Exception:
                    pass        
            sys.exit(0)
        except SystemExit:
            raise
        except Exception as e:        
            try:
                self.konus(f"Çıkış sırasında hata: {e}")
            except Exception:
                pass

    def uygulamayi_kapat(self, komut=None):
        """'Uygulamayı kapat', 'kendini kapat' gibi sesli komutlarla
        pencereyi (webview) gerçekten kapatır. 'kapat' genel anahtarı
        müzik kapatmaya gittiği için bu, daha spesifik anahtarlarla
        ondan ÖNCE eşleşmesi gereken ayrı bir fonksiyondur."""
        try:
            self.konus("Uygulama kapatılıyor. Görüşürüz!")
        except Exception:
            pass

        def _kapat():
            try:
                import webview
                for pencere in list(webview.windows):
                    try:
                        pencere.destroy()
                    except Exception:
                        pass
            except Exception:
                pass
            os._exit(0)

        threading.Timer(0.6, _kapat).start()
def main():
    print(" Asistan başlatılıyor...\n")
    time.sleep(1)

    asistan = EvAsistani(isim="Anka")
    threading.Thread(target=asistan.listen_loop, daemon=True).start()

    def web_guncelle():
        time.sleep(2)
        try:
            import dijidost_entegrasyon
            dijidost_entegrasyon.update_user_name(asistan.isim)
        except Exception as e:
            print(f"Webview güncelleme hatası: {e}")

    threading.Thread(target=web_guncelle, daemon=True).start()

    import dijidost_entegrasyon
    import webview

    class AppAPI(dijidost_entegrasyon.API):
        def uygulamayi_yeniden_baslat(self):
            entrypoint = os.path.abspath(__file__)
            try:
                child = subprocess.Popen(
                    [sys.executable, entrypoint],
                    cwd=os.path.dirname(entrypoint),
                )
            except (OSError, ValueError) as exc:
                logger.error("Uygulama yeniden başlatılamadı: %s", type(exc).__name__)
                return {"ok": False, "message": "Yeni uygulama süreci başlatılamadı."}
            if child.poll() is not None:
                return {"ok": False, "message": "Yeni uygulama süreci hemen sonlandı."}

            def close_current_app():
                try:
                    for window in list(webview.windows):
                        window.destroy()
                except (AttributeError, OSError):
                    pass
                os._exit(0)

            threading.Timer(0.2, close_current_app).start()
            return {"ok": True}

        def shutdown_app(self):
            def close_app():
                try:
                    for window in list(webview.windows):
                        window.destroy()
                finally:
                    os._exit(0)

            threading.Timer(0.2, close_app).start()
            return True

    dijidost_entegrasyon.set_asistan(asistan)
    camera_js = """
let cameraStream=null;
let cameraFallbackOpen=false;
async function toggleCamera(){
    let panel=document.getElementById('camera-panel');
    if(cameraStream||cameraFallbackOpen){
        if(cameraStream)cameraStream.getTracks().forEach(track=>track.stop());
        cameraStream=null;
        cameraFallbackOpen=false;
        if(panel)panel.remove();
        mesajEkle('Anka','Kamera kapatildi.');
        return false;
    }
    if(!panel){
        panel=document.createElement('div');
        panel.id='camera-panel';
        panel.style.cssText='position:fixed;right:16px;bottom:86px;width:min(360px,calc(100vw - 32px));aspect-ratio:16/10;background:#05070d;border:1px solid rgba(6,182,212,.45);border-radius:12px;overflow:hidden;z-index:9999;box-shadow:0 18px 60px rgba(0,0,0,.55)';
        panel.innerHTML='<video id="camera-video" autoplay playsinline muted style="width:100%;height:100%;object-fit:cover;background:#000"></video><button type="button" onclick="toggleCamera()" style="position:absolute;top:8px;right:8px;border:1px solid rgba(255,255,255,.25);background:rgba(0,0,0,.55);color:#fff;border-radius:8px;padding:5px 8px;font-size:12px;cursor:pointer">KAPAT</button>';
        document.body.appendChild(panel);
    }
    try{
        if(typeof pywebview!=='undefined'&&pywebview.api&&pywebview.api.gizlilik_izinleri_getir){
            const permissions=await pywebview.api.gizlilik_izinleri_getir();
            if(!permissions.camera){
                if(panel)panel.remove();
                mesajEkle('Anka','Kamera izni kapalı. Ayarlar > Gizlilik ve İzinler bölümünden etkinleştir.');
                return false;
            }
        }
        cameraStream=await navigator.mediaDevices.getUserMedia({video:true,audio:false});
        document.getElementById('camera-video').srcObject=cameraStream;
        mesajEkle('Anka','Kamera acildi.');
        return true;
    }catch(e){
        try{
            panel.innerHTML='<img src="http://127.0.0.1:5000/kamera" style="width:100%;height:100%;object-fit:cover;background:#000"><button type="button" onclick="toggleCamera()" style="position:absolute;top:8px;right:8px;border:1px solid rgba(255,255,255,.25);background:rgba(0,0,0,.55);color:#fff;border-radius:8px;padding:5px 8px;font-size:12px;cursor:pointer">KAPAT</button>';
            cameraFallbackOpen=true;
            mesajEkle('Anka','Kamera yerel sunucudan acildi.');
            return true;
        }catch(err){
            if(panel)panel.remove();
            mesajEkle('Anka','Kamera acilamadi: '+(err&&err.message?err.message:err));
            return false;
        }
    }
}
"""
    trai_action_patch = """function traiAction(action){
    if(action==='cam'){
        const chat=document.getElementById('trai-chat');
        const div=document.createElement('div');
        div.className='ai-s';
        div.textContent='SYS: '+((cameraStream||cameraFallbackOpen)?'Kamera kapatiliyor...':'Kamera baslatiliyor...');
        chat.appendChild(div);
        chat.scrollTop=chat.scrollHeight;
        toggleCamera();
        return;
    }
    if(action==='shutdown'){
        const chat=document.getElementById('trai-chat');
        const div=document.createElement('div');
        div.className='ai-s';
        div.textContent='SYS: Uygulama kapatiliyor...';
        chat.appendChild(div);
        chat.scrollTop=chat.scrollHeight;
        try{
            if(typeof pywebview!=='undefined'&&pywebview.api&&pywebview.api.shutdown_app){
                pywebview.api.shutdown_app();
            }else{
                window.close();
            }
        }catch(e){
            window.close();
        }
        return;
    }"""
    html_content = dijidost_entegrasyon.DIJIDOST_HTML.replace(
        "function traiAction(action){",
        camera_js + "\n" + trai_action_patch
    )

    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dijidost_ui.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("[OK] ANKA AI Masaüstü arayüzü başlatılıyor...")
    webview.create_window(asistan.isim, html_path, width=1600, height=900, resizable=True, js_api=AppAPI())
    webview.start()

if __name__ == "__main__":
    main() 
