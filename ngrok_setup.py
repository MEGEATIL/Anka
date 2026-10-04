#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ngrok yetkilendirmesini shell çağrısı yapmadan yapılandırır."""

from __future__ import annotations

import getpass


def main() -> int:
    print("=== ngrok Kurulumu ===\n")
    authtoken = getpass.getpass(
        "ngrok authtoken girin (girdi ekranda gösterilmez):\n> "
    ).strip()
    if not authtoken:
        print("[HATA] Token girilmedi.")
        return 1

    try:
        from pyngrok import ngrok
    except ImportError:
        print("[HATA] pyngrok kurulu değil. requirements.txt dosyasını yükleyin.")
        return 2

    try:
        ngrok.set_auth_token(authtoken)
    except (OSError, ValueError) as error:
        print(f"[HATA] Token kaydedilemedi: {type(error).__name__}")
        return 3

    print("[OK] ngrok authtoken kaydedildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
