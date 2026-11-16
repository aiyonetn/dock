"""Dock ayar dosyasi: ~/.config/dock/ayar.json."""
from __future__ import annotations

import json
import os
from pathlib import Path

VARSAYILAN = {
    "autoHide": False,
    "iconSize": 64,
    "buyutme": 1.9,
    "kenarBosluk": 10,
    "sabitlenen": [],
}

SINIRLAR = {
    "iconSize": (32, 96),
    "buyutme": (1.0, 2.5),
    "kenarBosluk": (0, 120),
}


def ayar_yolu() -> Path:
    kok = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(kok) / "dock" / "ayar.json"


def _sinirla(ayar: dict) -> dict:
    for anahtar, (alt, ust) in SINIRLAR.items():
        try:
            ayar[anahtar] = max(alt, min(ust, type(ayar[anahtar])(ayar[anahtar])))
        except (KeyError, TypeError, ValueError):
            ayar[anahtar] = VARSAYILAN[anahtar]
    if not isinstance(ayar.get("sabitlenen"), list):
        ayar["sabitlenen"] = []
    ayar["autoHide"] = bool(ayar.get("autoHide", False))
    return ayar


def yukle(varsayilan_sabitlenen: list[str]) -> dict:
    """Ayarlari okur; dosya yoksa varsayilanlarla olusturur."""
    yol = ayar_yolu()
    ayar = dict(VARSAYILAN)
    try:
        ayar.update(json.loads(yol.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        ayar["sabitlenen"] = list(varsayilan_sabitlenen)
        kaydet(ayar)
        return _sinirla(ayar)
    ayar = _sinirla(ayar)
    if not ayar["sabitlenen"]:
        ayar["sabitlenen"] = list(varsayilan_sabitlenen)
    return ayar


def kaydet(ayar: dict) -> None:
    yol = ayar_yolu()
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(ayar, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
