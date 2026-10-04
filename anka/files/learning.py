from __future__ import annotations

import os
import re
from pathlib import Path

from anka.core.errors import FileProcessingError


class DocumentLearner:
    ALLOWED = {".txt", ".pdf", ".docx"}
    MAX_BYTES = 20 * 1024 * 1024

    def read(self, path: str) -> tuple[str, str]:
        file_path = Path(path)
        if not file_path.is_file():
            raise FileProcessingError("Dosya bulunamadı.")
        if file_path.suffix.lower() not in self.ALLOWED:
            raise FileProcessingError("Yalnızca PDF, DOCX ve TXT dosyaları desteklenir.")
        if file_path.stat().st_size > self.MAX_BYTES:
            raise FileProcessingError("Dosya 20 MB güvenlik sınırını aşıyor.")
        try:
            if file_path.suffix.lower() == ".txt":
                raw = file_path.read_bytes()
                for encoding in ("utf-8-sig", "utf-8", "cp1254"):
                    try:
                        text = raw.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        text = ""
                if not text:
                    raise FileProcessingError("Metin dosyasının kodlaması okunamadı.")
            elif file_path.suffix.lower() == ".pdf":
                try:
                    from pypdf import PdfReader
                except ImportError as exc:
                    raise FileProcessingError("PDF için pypdf paketi gerekli.") from exc
                text = "\n".join((page.extract_text() or "") for page in PdfReader(str(file_path)).pages)
            else:
                try:
                    import docx
                except ImportError as exc:
                    raise FileProcessingError("DOCX için python-docx paketi gerekli.") from exc
                text = "\n".join(paragraph.text for paragraph in docx.Document(str(file_path)).paragraphs)
        except FileProcessingError:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            raise FileProcessingError("Dosya okunamadı veya dosya biçimi bozuk.") from exc
        except Exception as exc:
            # PDF/DOCX sağlayıcıları kendi istisna sınıflarını dışa aktarır;
            # bu dış sınırda teknik ayrıntıyı kullanıcıya sızdırmayız.
            raise FileProcessingError("Dosya ayrıştırılamadı; dosya bozuk olabilir.") from exc
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            raise FileProcessingError("Dosyadan metin çıkarılamadı; görsel PDF için OCR gerekebilir.")
        return file_path.name, text

    def relevant_excerpt(self, text: str, query: str, maximum: int = 1400) -> str:
        terms = set(re.findall(r"\w+", query.casefold()))
        chunks = [text[index:index + 550] for index in range(0, len(text), 450)]
        scored = [(len(terms & set(re.findall(r"\w+", chunk.casefold()))), chunk) for chunk in chunks]
        return max(scored, key=lambda item: item[0])[1][:maximum] if scored else text[:maximum]
