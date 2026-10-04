from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from anka.core.errors import WebResearchError


@dataclass(frozen=True)
class WebSource:
    title: str
    url: str
    snippet: str


class WebResearcher:
    _PREFERRED_DOMAINS = (
        ".gov.tr", ".edu.tr", "wikipedia.org", "bbc.com", "reuters.com",
        "aa.com.tr", "who.int", "openai.com", "microsoft.com", "apple.com",
    )

    def search(self, query: str, max_sources: int = 5) -> list[WebSource]:
        if not query or len(query) > 300:
            raise WebResearchError("Araştırma sorgusu geçersiz.")
        try:
            response = requests.post(
                "https://html.duckduckgo.com/html/", data={"q": query},
                headers={"User-Agent": "ANKA/1.0"}, timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WebResearchError("Araştırma servisine bağlanılamadı.") from exc
        soup = BeautifulSoup(response.text, "html.parser")
        sources: list[WebSource] = []
        for result in soup.select(".result")[:max_sources]:
            title_tag, snippet_tag, link_tag = result.select_one(".result__a"), result.select_one(".result__snippet"), result.select_one(".result__a")
            if not title_tag or not link_tag:
                continue
            href = link_tag.get("href", "")
            parsed = urlparse(href)
            if parsed.path == "/l/":
                href = parse_qs(parsed.query).get("uddg", [""])[0]
            if urlparse(href).scheme not in {"http", "https"}:
                continue
            sources.append(WebSource(title_tag.get_text(" ", strip=True), href, snippet_tag.get_text(" ", strip=True) if snippet_tag else ""))
        if not sources:
            raise WebResearchError("Karşılaştırılabilir kaynak bulunamadı.")
        query_terms = {term.casefold() for term in re.findall(r"\w+", query) if len(term) > 2}

        def quality(source: WebSource) -> tuple[int, int, int]:
            domain = urlparse(source.url).netloc.casefold()
            preferred = int(any(domain == item or domain.endswith(item) for item in self._PREFERRED_DOMAINS))
            text = f"{source.title} {source.snippet}".casefold()
            relevance = sum(term in text for term in query_terms)
            return preferred, relevance, min(len(source.snippet), 600)

        return sorted(sources, key=quality, reverse=True)

    @staticmethod
    def format_sources(sources: list[WebSource], limit: int = 3) -> str:
        return "\n".join(
            f"- {source.title} ({urlparse(source.url).netloc})"
            for source in sources[:limit]
        )

    @staticmethod
    def offline_summary(sources: list[WebSource], limit: int = 300) -> str:
        """LLM kullanılamadığında ham arama sonucunu okunabilir hale getirir."""
        for source in sources:
            snippet = re.sub(r"\s+", " ", source.snippet).strip(" -:;")
            if not snippet:
                continue
            sentence = re.split(r"(?<=[.!?])\s+", snippet, maxsplit=1)[0].strip()
            if len(sentence) < 35:
                continue
            if len(sentence) > limit:
                sentence = sentence[:limit - 3].rsplit(" ", 1)[0] + "..."
            return sentence
        return "Güvenilir bir kısa özet çıkaracak yeterli kaynak metni bulunamadı."

    def report(self, query: str, max_sources: int = 5) -> str:
        sources = self.search(query, max_sources)
        summary = self.offline_summary(sources, limit=300)
        citations = self.format_sources(sources, limit=3)
        return f"{summary}\n\nKaynaklar:\n{citations}"
