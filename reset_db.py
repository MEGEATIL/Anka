"""Geliştirici amaçlı hafıza veritabanı sıfırlama aracı.

Bu betik yalnızca açık ``--confirm-reset`` bayrağıyla çalışır. Uygulama içi
sıfırlama için Ayarlar ekranındaki iki aşamalı onayı kullanın.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def reset_database(path: Path) -> bool:
    allowed = (Path.cwd() / "hafiza.db").resolve()
    if path.resolve() != allowed:
        raise ValueError("Yalnızca geçerli çalışma klasöründeki hafiza.db silinebilir.")
    if not allowed.is_file():
        return False
    allowed.unlink()
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="ANKA hafıza veritabanını sıfırlar.")
    parser.add_argument("--confirm-reset", action="store_true", help="Geri alınamaz silmeyi açıkça onaylar.")
    parser.add_argument("--database", default="hafiza.db", help="Yalnızca yerel veritabanı dosya adı.")
    args = parser.parse_args()
    if not args.confirm_reset:
        parser.error("Silme işlemi için --confirm-reset bayrağı zorunludur.")
    try:
        deleted = reset_database(Path(args.database))
    except ValueError as error:
        parser.error(str(error))
    if deleted:
        print("hafiza.db silindi. Uygulama yeniden başlatıldığında yeniden oluşturulur.")
    else:
        print("hafiza.db bulunamadı; silme işlemi yapılmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
