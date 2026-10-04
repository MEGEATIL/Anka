# -*- coding: utf-8 -*-
"""
ajan.py
-------
ANKA'ya "genel amaçlı ajan" (senin yerine iş yapan asistan) yeteneği
kazandıran modül.

Mantık (ReAct döngüsü):
1) Kullanıcı bir HEDEF söyler ("ödevimi hazırla", "bilgisayarda X'i aç ve
   Y hakkında araştır" gibi).
2) LLM'e elindeki ARAÇLARIN listesi + hedef verilir. LLM her adımda SADECE
   JSON formatında şu şekilde cevap verir:
       {"dusunce": "...", "eylem": "arac_adi", "eylem_girdi": {...}}
   veya iş bittiyse:
       {"dusunce": "...", "eylem": "cevap_ver", "eylem_girdi": {"mesaj": "..."}}
3) Kod, "eylem" alanındaki aracı gerçekten çalıştırır, sonucu (gözlem) LLM'e
   geri verir, LLM bir sonraki adıma karar verir. Bu, "eylem": "cevap_ver"
   gelene ya da MAX_ADIM'a ulaşılana kadar devam eder.

Neden function-calling API yerine JSON/ReAct?
Hugging Face router üzerindeki ücretsiz modeller (Llama-3.2-3B gibi) her
zaman düzgün "tool calling" desteklemeyebiliyor. JSON tabanlı ReAct, hemen
hemen her sohbet modeliyle çalışır ve modeli değiştirmen gerekirse de
taşınabilir kalır.

Yeni bir araç eklemek istersen: TOOLS sözlüğüne
    "arac_adi": {"fn": fonksiyon, "aciklama": "LLM'e görünecek açıklama"}
eklemen yeterli - ajan otomatik olarak kullanabilir hale gelir.
"""

import inspect
import json
import re
from llm_yardimci import guvenli_tamamla


MAX_ADIM = 6


class GorevAjani:
    def __init__(self, client, model=None, konus_fn=None):
        """
        client    -> OpenAI uyumlu client (EvAsistani.client). None ise ajan
                     çalışamaz (LLM olmadan çok adımlı planlama yapılamaz).
        model     -> Kullanılacak model adı.
        konus_fn  -> Ajanın ara adımlarda kullanıcıyı bilgilendirmek için
                     çağıracağı fonksiyon (örn. self.konus). Opsiyonel;
                     verilmezse sessizce çalışır, sadece son cevabı döndürür.
        """
        self.client = client
        self.model = model
        self.konus_fn = konus_fn
        self.tools = {}

    def arac_kaydet(self, isim, fn, aciklama):
        """Ajanın kullanabileceği yeni bir araç ekler.
        fn(**kwargs) -> str (sonucu metin olarak döndürmeli)."""
        if not isinstance(isim, str) or not re.fullmatch(r"[a-z_][a-z0-9_]*", isim):
            raise ValueError("Geçersiz araç adı.")
        parameters = inspect.signature(fn).parameters.values()
        accepted_arguments = {
            parameter.name
            for parameter in parameters
            if parameter.kind in (parameter.POSITIONAL_OR_KEYWORD, parameter.KEYWORD_ONLY)
        }
        self.tools[isim] = {
            "fn": fn,
            "aciklama": str(aciklama),
            "arguments": accepted_arguments,
        }

    def _sistem_prompt(self):
        arac_listesi = "\n".join(
            f'- "{isim}": {bilgi["aciklama"]}' for isim, bilgi in self.tools.items()
        )
        return (
            "Sen ANKA adlı Türkçe konuşan bir yapay zeka asistanının GÖREV AJANISIN. "
            "Kullanıcının verdiği hedefe ulaşmak için aşağıdaki araçları adım adım "
            "kullanabilirsin:\n\n"
            f"{arac_listesi}\n"
            '- "cevap_ver": Görev tamamlandığında veya daha fazla araç kullanmaya '
            "gerek olmadığında kullanıcıya son cevabı vermek için kullan.\n\n"
            "KURALLAR:\n"
            "1) HER ZAMAN sadece geçerli bir JSON nesnesi döndür, başka hiçbir "
            "metin/açıklama/markdown ekleme.\n"
            "2) Format tam olarak şöyle olmalı:\n"
            '   {"dusunce": "kısa iç muhakeme", "eylem": "arac_adi", '
            '"eylem_girdi": {"parametre": "değer"}}\n'
            "3) Bir aracın sonucunu (gözlem) gördükten sonra hedefe ulaşılıp "
            "ulaşılmadığına karar ver; ulaşıldıysa 'cevap_ver' eylemini kullan.\n"
            "4) Gereksiz yere aynı aracı tekrar tekrar çağırma; en fazla "
            f"{MAX_ADIM} adımın var, ona göre planla.\n"
            "5) 'cevap_ver' kullanırken eylem_girdi.mesaj alanına kullanıcıya "
            "Türkçe, kısa ve net bir sonuç mesajı yaz. Bir araç çağrısının "
            "gözlemi olmadan dış dünyada işlem yapıldığını veya başarının "
            "doğrulandığını iddia etme."
        )

    def _json_ayikla(self, ham_metin):
        """LLM cevabından (markdown code-fence olsa da) JSON'u çıkarır."""
        temiz = ham_metin.strip()
        temiz = re.sub(r"^```(?:json)?\s*|```$", "", temiz, flags=re.MULTILINE).strip()
        try:
            return json.loads(temiz)
        except Exception:
            m = re.search(r"\{.*\}", temiz, flags=re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except Exception:
                    return None
            return None

    def _bilgilendir(self, mesaj):
        if self.konus_fn:
            try:
                self.konus_fn(mesaj)
            except Exception:
                pass

    def gorevi_yurut(self, hedef):
        """Ana giriş noktası: bir hedef metni alır, ajanı çalıştırır,
        son cevabı (str) döndürür."""
        if not self.client:
            return ("Görev ajanını çalıştırmak için LLM bağlantısı gerekiyor "
                    "(HF_TOKEN ayarlanmamış görünüyor).")

        if not self.tools:
            return "Ajana henüz hiçbir araç kaydedilmemiş (arac_kaydet ile ekle)."

        messages = [
            {"role": "system", "content": self._sistem_prompt()},
            {"role": "user", "content": f"HEDEF: {hedef}"},
        ]

        tool_observations: list[str] = []
        for adim_no in range(1, MAX_ADIM + 1):
            try:
                ham, _kullanilan_model = guvenli_tamamla(
                    self.client, messages, tercih_edilen_model=self.model
                )
            except Exception:
                return "Görev planı oluşturulamadı; LLM bağlantısını veya API ayarlarını kontrol edin."

            karar = self._json_ayikla(ham)
            if not karar or "eylem" not in karar:
                return "Görev planı doğrulanamadı; herhangi bir işlem yapılmadı."

            eylem = karar.get("eylem")
            girdi = karar.get("eylem_girdi") or {}
            dusunce = karar.get("dusunce", "")

            if dusunce:
                # Modelin iç muhakemesini değil, denetlenebilir işlem durumunu göster.
                self._bilgilendir(f"[Adım {adim_no}] Görev planı denetleniyor.")

            if eylem == "cevap_ver":
                if not tool_observations:
                    return "Görevin sonucu doğrulanamadı; herhangi bir araç çalıştırılmadı."
                if any(observation.startswith("HATA:") for observation in tool_observations):
                    return "Görev adımlarından biri başarısız oldu; başarı doğrulanamadı."
                return girdi.get("mesaj", "Görev tamamlandı.")

            if eylem not in self.tools:
                gozlem = f"HATA: '{eylem}' adında bir araç yok. Geçerli araçlardan birini seç."
            else:
                try:
                    if not isinstance(girdi, dict):
                        raise TypeError("Araç parametreleri nesne olmalıdır.")
                    unexpected = set(girdi) - self.tools[eylem]["arguments"]
                    if unexpected:
                        raise TypeError("Araç için izin verilmeyen parametreler var.")
                    gozlem = self.tools[eylem]["fn"](**girdi)
                    if gozlem is None:
                        gozlem = "(sonuç boş döndü)"
                    gozlem = str(gozlem)
                except TypeError as e:
                    gozlem = f"HATA: Araç yanlış parametrelerle çağrıldı ({e})."
                except Exception as e:
                    gozlem = "HATA: Araç güvenli biçimde çalıştırılamadı."

            tool_observations.append(gozlem)

            # Modelin kendi cevabını ve gözlemi konuşma geçmişine ekle
            messages.append({"role": "assistant", "content": json.dumps(karar, ensure_ascii=False)})
            messages.append({"role": "user", "content": f"GÖZLEM: {gozlem}"})

        return ("Görevi belirlenen adım sayısında tamamlayamadım. Hedefi daha "
                "küçük parçalara bölüp tekrar dener misin?")
