# -*- coding: utf-8 -*-
"""Mevcut index.html'e genisletme parcalarini ekler — hicbir sey silinmez."""
from pathlib import Path

ROOT = Path(__file__).parent
INDEX = ROOT / "index.html"

def main():
    html = INDEX.read_text(encoding="utf-8")
    css = (ROOT / "expansion.css").read_text(encoding="utf-8")
    body = (ROOT / "expansion.html").read_text(encoding="utf-8")
    js = (ROOT / "expansion.js").read_text(encoding="utf-8")
    nav = (ROOT / "expansion_nav.html").read_text(encoding="utf-8")

    if "<!-- ANKA EXPANSION START -->" in html:
        print("Genisletme zaten eklenmis.")
        return

    html = html.replace("</style>", css + "\n</style>", 1)
    html = html.replace(
        '<a href="#iletisim"><span data-i18n="nav_iletisim">İLETİŞİM</span></a>',
        nav + '\n    <a href="#iletisim"><span data-i18n="nav_iletisim">İLETİŞİM</span></a>',
        1,
    )
    html = html.replace(
        "<!-- ===================== FOOTER ===================== -->",
        body + "\n<!-- ===================== FOOTER ===================== -->",
        1,
    )
    html = html.replace("</body>", js + "\n</body>", 1)

    INDEX.write_text(html, encoding="utf-8")
    line_count = html.count("\n") + 1
    print(f"Tamamlandi. Toplam satir: {line_count}")

if __name__ == "__main__":
    main()
