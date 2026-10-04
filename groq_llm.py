# -*- coding: utf-8 -*-
from typing import Optional, List, Dict
import json
import os
from datetime import datetime
from pathlib import Path
from threading import RLock
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        return False

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()

class GroqChatMemory:
    def __init__(self, max_messages: int = 20):
        self.messages: List[Dict] = []
        self.max_messages = max(1, int(max_messages))
        self.memory_file = Path("konusma_hafizasi.json")
        self._lock = RLock()
        self.load_from_file()
    
    def add_message(self, role: str, content: str):
        if role not in {"system", "user", "assistant", "tool"}:
            raise ValueError("Geçersiz konuşma rolü.")
        text = str(content).strip()[:12_000]
        if not text:
            return
        with self._lock:
            self.messages.append({
                "role": role,
                "content": text,
                "timestamp": datetime.now().isoformat()
            })
            self.messages = self.messages[-self.max_messages:]
            self.save_to_file()
    
    def get_messages(self) -> List[Dict]:
        return [{"role": msg["role"], "content": msg["content"]} 
                for msg in self.messages]
    
    def clear(self):
        with self._lock:
            self.messages = []
            self.save_to_file()
    
    def save_to_file(self):
        try:
            temporary = self.memory_file.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self.messages, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            temporary.replace(self.memory_file)
        except (OSError, TypeError, ValueError) as error:
            print(f"Bellek kaydedilemedi: {type(error).__name__}")
    
    def load_from_file(self):
        try:
            if self.memory_file.exists():
                raw_messages = json.loads(self.memory_file.read_text(encoding="utf-8"))
                if not isinstance(raw_messages, list):
                    raise ValueError("Geçersiz hafıza biçimi")
                self.messages = [
                    item for item in raw_messages[-self.max_messages:]
                    if isinstance(item, dict)
                    and item.get("role") in {"system", "user", "assistant", "tool"}
                    and isinstance(item.get("content"), str)
                ]
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Bellek yüklenemedi: {type(error).__name__}")
            self.messages = []

class GroqLLM:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key or Groq is None:
            print("Groq sağlayıcısı yapılandırılmamış veya SDK kurulu değil")
            self.client = None
            self.memory = GroqChatMemory()
            self.model = "llama-3.3-70b-versatile"
            return
        self.client = Groq(api_key=self.api_key)
        self.memory = GroqChatMemory()
        self.model = "llama-3.3-70b-versatile"
        print(f"Groq LLM basladi | Model: {self.model}")
    
    def chat(self, user_message: str, system_prompt: str = None) -> str:
        if not self.client:
            return "Dil modeli şu an yapılandırılmamış. API ayarlarını kontrol edin."
        try:
            self.memory.add_message("user", user_message)
            if system_prompt is None:
                system_prompt = """Sen EgeDa, profesyonel bir Turkce yapay zeka asistanisn.
- Ozlu, net ve yararli cevaplar ver
- Turkce dilbilgisine ozen goster
- Samimi ve yardimci bir tona sahip ol"""
            messages = [{"role": "system", "content": system_prompt}] + self.memory.get_messages()
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model,
                temperature=0.7,
                max_tokens=512,
            )
            response = chat_completion.choices[0].message.content
            self.memory.add_message("assistant", response)
            return response
        except Exception as e:
            print(f"Groq Hata: {type(e).__name__}")
            return "Dil modeli şu an yanıt veremiyor. API ayarlarını ve bağlantıyı kontrol edin."
    
    def clear_memory(self):
        self.memory.clear()
        print("Konusma bellegi temizlendi")
    
    def get_memory_stats(self) -> Dict:
        return {
            "toplam_mesaj": len(self.memory.messages),
            "maksimum": self.memory.max_messages,
            "model": self.model,
        }
