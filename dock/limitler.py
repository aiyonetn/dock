"""AI kullanim limitleri: Codex app-server (JSON-RPC) ve Claude OAuth ucu."""
from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

_ZAMAN_ASIMI = 10.0
_CODEX = shutil.which("codex") or "/home/claudecodexsever/.local/npm/bin/codex"


def _bos(kaynak: str = "yok", plan: str = "") -> dict:
    return {
        "session": {"percent": None, "reset": None},
        "weekly": {"percent": None, "reset": None},
        "plan": plan,
        "kaynak": kaynak,
    }


def _epoch(deger) -> int | None:
    if deger is None:
        return None
    if isinstance(deger, (int, float)):
        return int(deger)
    if isinstance(deger, str):
        try:
            return int(datetime.fromisoformat(deger.replace("Z", "+00:00")).timestamp())
        except ValueError:
            return None
    return None


def _yuzde(deger) -> float | None:
    try:
        return max(0.0, min(100.0, float(deger)))
    except (TypeError, ValueError):
        return None


# --- Codex -----------------------------------------------------------------
def _rpc(proc: subprocess.Popen, istek: dict, durum: dict) -> dict:
    proc.stdin.write((json.dumps(istek) + "\n").encode())
    proc.stdin.flush()
    bitis = datetime.now(timezone.utc).timestamp() + _ZAMAN_ASIMI
    while True:
        tampon = durum.get("tampon", b"")
        while b"\n" in tampon:
            satir, tampon = tampon.split(b"\n", 1)
            durum["tampon"] = tampon
            try:
                cevap = json.loads(satir.decode("utf-8", "replace"))
            except ValueError:
                continue
            if cevap.get("id") == istek.get("id"):
                if "error" in cevap:
                    raise RuntimeError(str(cevap["error"]))
                return cevap.get("result") or {}
        durum["tampon"] = tampon
        kalan = bitis - datetime.now(timezone.utc).timestamp()
        if kalan <= 0:
            raise TimeoutError("codex app-server yanit vermedi")
        hazir, _, _ = select.select([proc.stdout], [], [], kalan)
        if not hazir:
            raise TimeoutError("codex app-server yanit vermedi")
        parca = os.read(proc.stdout.fileno(), 65536)
        if not parca:
            raise RuntimeError("codex app-server kapandi")
        durum["tampon"] = tampon + parca


def _codex_oku() -> dict:
    if not Path(_CODEX).is_file():
        return _bos()
    proc = subprocess.Popen(
        [_CODEX, "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    durum = {"tampon": b""}
    try:
        _rpc(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"clientInfo": {"name": "dock", "version": "0.1"}},
            },
            durum,
        )
        proc.stdin.write(
            (json.dumps({"jsonrpc": "2.0", "method": "initialized", "params": {}}) + "\n").encode()
        )
        proc.stdin.flush()
        hesap = _rpc(
            proc, {"jsonrpc": "2.0", "id": 2, "method": "account/read", "params": {}}, durum
        )
        limitler = _rpc(
            proc,
            {"jsonrpc": "2.0", "id": 3, "method": "account/rateLimits/read", "params": {}},
            durum,
        )
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except (OSError, subprocess.SubprocessError):
            proc.kill()

    plan = str((hesap.get("account") or {}).get("planType") or "")
    rl = limitler.get("rateLimits") or {}
    sonuc = _bos("api", plan)

    def doldur(anahtar: str, veri: dict | None) -> None:
        if not isinstance(veri, dict):
            return
        sonuc[anahtar] = {
            "percent": _yuzde(veri.get("usedPercent")),
            "reset": _epoch(veri.get("resetsAt")),
        }

    for anahtar, veri in (("primary", rl.get("primary")), ("secondary", rl.get("secondary"))):
        if not isinstance(veri, dict):
            continue
        sure = veri.get("windowDurationMins")
        hedef = "weekly" if isinstance(sure, (int, float)) and sure >= 10000 else "session"
        doldur(hedef, veri)
    return sonuc


# --- Claude ----------------------------------------------------------------
def _zaman_bul(veri, derinlik: int = 0):
    """credentials icinde expiresAt/expires_at ara; epoch (sn) dondur."""
    if derinlik > 6:
        return None
    if isinstance(veri, dict):
        for anahtar, deger in veri.items():
            if anahtar.lower() in ("expiresat", "expires_at", "expiry"):
                if isinstance(deger, (int, float)):
                    sayi = int(deger)
                    return sayi // 1000 if sayi > 2e10 else sayi
                deger = _epoch(deger)
                if deger is not None:
                    return deger
            bulunan = _zaman_bul(deger, derinlik + 1)
            if bulunan:
                return bulunan
    elif isinstance(veri, list):
        for deger in veri:
            bulunan = _zaman_bul(deger, derinlik + 1)
            if bulunan:
                return bulunan
    return None


def _token_bul(veri, derinlik: int = 0):
    if derinlik > 6:
        return None
    if isinstance(veri, dict):
        for anahtar, deger in veri.items():
            if anahtar == "accessToken" and isinstance(deger, str) and deger:
                return deger
            bulunan = _token_bul(deger, derinlik + 1)
            if bulunan:
                return bulunan
    elif isinstance(veri, list):
        for deger in veri:
            bulunan = _token_bul(deger, derinlik + 1)
            if bulunan:
                return bulunan
    return None


def _elle(ad: str) -> dict | None:
    yol = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "dock" / "limitler.json"
    try:
        veri = json.loads(yol.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    kayit = veri.get(ad)
    if not isinstance(kayit, dict):
        return None
    s = _yuzde(kayit.get("session"))
    w = _yuzde(kayit.get("weekly"))
    if s is None and w is None:
        return None
    return {
        "session": {"percent": s, "reset": None},
        "weekly": {"percent": w, "reset": None},
        "plan": "",
        "kaynak": "elle",
    }


def _claude_oku() -> dict:
    try:
        kimlik = json.loads((Path.home() / ".claude" / ".credentials.json").read_text("utf-8"))
    except (OSError, ValueError):
        kimlik = None
    token = _token_bul(kimlik)
    if not token:
        return _elle("claude") or _bos()
    sona_erme = _zaman_bul(kimlik)
    if sona_erme is not None and sona_erme <= int(datetime.now(timezone.utc).timestamp()):
        return _bos("suresi_doldu")

    istek = Request(
        "https://api.anthropic.com/api/oauth/usage?at_wall=1&skip_spend=1",
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(istek, timeout=8) as cevap:
            veri = json.loads(cevap.read().decode("utf-8"))
    except HTTPError as hata:
        if hata.code in (401, 403):
            return _bos("suresi_doldu")
        return _bos()
    except Exception:
        return _bos()

    sonuc = _bos("api", str(veri.get("plan") or ""))
    for kayit in veri.get("limits") or []:
        if not isinstance(kayit, dict):
            continue
        tur = kayit.get("kind")
        hedef = "session" if tur == "session" else "weekly" if tur in ("weekly_all", "weekly_scoped") else None
        if hedef is None:
            continue
        yuzde = _yuzde(kayit.get("percent"))
        reset = _epoch(kayit.get("resets_at"))
        eski = sonuc[hedef]
        if eski["percent"] is None or (yuzde is not None and yuzde > eski["percent"]):
            sonuc[hedef] = {"percent": yuzde, "reset": reset}

    if sonuc["session"]["percent"] is None and sonuc["weekly"]["percent"] is None:
        for anahtar, alan in (("session", "five_hour"), ("weekly", "seven_day")):
            veri2 = veri.get(alan)
            if isinstance(veri2, dict):
                sonuc[anahtar] = {
                    "percent": _yuzde(veri2.get("utilization", veri2.get("percent"))),
                    "reset": _epoch(veri2.get("resets_at")),
                }
    return sonuc


def oku() -> dict:
    """Iki saglayiciyi da okur; hata durumunda 'yok' doner."""
    sonuc = {"codex": _bos(), "claude": _bos()}
    try:
        sonuc["codex"] = _codex_oku()
    except Exception:
        sonuc["codex"] = _bos("hata")
    try:
        sonuc["claude"] = _claude_oku()
    except Exception:
        sonuc["claude"] = _bos()
    return sonuc
