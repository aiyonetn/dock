"""Ses cikisi ve mikrofon durumu: pactl ile okuma/ayarlama.

Gerçek hoparlör/mikrofon olmayan makinelerde de çalışır: çıkış için
varsayılan sink, mikrofon için önce .monitor olmayan kaynak aranır;
yoksa varsayılan kaynak (auto_null.monitor) yedek olarak kullanılır ve
`mikrofonVar` false kalır. Mute yine sayısal olarak çalışır.
"""
from __future__ import annotations

import re
import subprocess

from PySide6.QtCore import Property, QObject, Signal, Slot


class SesModel(QObject):
    degisti = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cikisAd = ""
        self._cikisYuzde = 0
        self._cikisMute = False
        self._cikisVar = False
        self._kaynakAd = ""
        self._kaynakYuzde = 0
        self._kaynakMute = False
        self._kaynakVar = False
        self._mikrofonVar = False
        self.yenile()

    # --- yardimcilar -------------------------------------------------------
    @staticmethod
    def _cal(*argumanlar: str) -> str:
        try:
            sonuc = subprocess.run(
                ["pactl", *argumanlar], capture_output=True, text=True, timeout=3
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        if sonuc.returncode != 0:
            return ""
        return sonuc.stdout.strip()

    @staticmethod
    def _yuzde(metin: str) -> int:
        degerler = [int(v) for v in re.findall(r"(\d+)%", metin or "")]
        if not degerler:
            return 0
        return int(round(sum(degerler) / len(degerler)))

    @staticmethod
    def _mute(metin: str) -> bool:
        return (metin or "").strip().lower().endswith("yes")

    def _kaynaklar(self) -> list[str]:
        adlar = []
        for satir in self._cal("list", "short", "sources").splitlines():
            parcalar = satir.split("\t")
            if len(parcalar) >= 2 and parcalar[1]:
                adlar.append(parcalar[1])
        return adlar

    # --- okuma -------------------------------------------------------------
    @Slot()
    def yenile(self) -> None:
        onceki = (
            self._cikisAd, self._cikisYuzde, self._cikisMute, self._cikisVar,
            self._kaynakAd, self._kaynakYuzde, self._kaynakMute,
            self._kaynakVar, self._mikrofonVar,
        )

        cikis = self._cal("get-default-sink")
        self._cikisVar = bool(cikis)
        self._cikisAd = cikis
        if cikis:
            self._cikisYuzde = self._yuzde(self._cal("get-sink-volume", "@DEFAULT_SINK@"))
            self._cikisMute = self._mute(self._cal("get-sink-mute", "@DEFAULT_SINK@"))
        else:
            self._cikisYuzde = 0
            self._cikisMute = False

        kaynaklar = self._kaynaklar()
        gercek = [ad for ad in kaynaklar if ".monitor" not in ad]
        varsayilan = self._cal("get-default-source")
        if gercek:
            kaynak = varsayilan if varsayilan in gercek else gercek[0]
            self._mikrofonVar = True
        elif kaynaklar:
            kaynak = varsayilan if varsayilan in kaynaklar else kaynaklar[0]
            self._mikrofonVar = False
        else:
            kaynak = ""
            self._mikrofonVar = False
        self._kaynakAd = kaynak
        self._kaynakVar = bool(kaynak)
        if kaynak:
            self._kaynakYuzde = self._yuzde(self._cal("get-source-volume", kaynak))
            self._kaynakMute = self._mute(self._cal("get-source-mute", kaynak))
        else:
            self._kaynakYuzde = 0
            self._kaynakMute = False

        if onceki != (
            self._cikisAd, self._cikisYuzde, self._cikisMute, self._cikisVar,
            self._kaynakAd, self._kaynakYuzde, self._kaynakMute,
            self._kaynakVar, self._mikrofonVar,
        ):
            self.degisti.emit()

    # --- eylemler ----------------------------------------------------------
    @Slot(int)
    def cikisAyarla(self, yuzde: int) -> None:
        yuzde = max(0, min(100, int(yuzde)))
        if not self._cikisVar:
            return
        self._cal("set-sink-volume", "@DEFAULT_SINK@", f"{yuzde}%")
        self.yenile()

    @Slot()
    def cikisMuteDegistir(self) -> None:
        if not self._cikisVar:
            return
        self._cal("set-sink-mute", "@DEFAULT_SINK@", "0" if self._cikisMute else "1")
        self.yenile()

    @Slot()
    def kaynakMuteDegistir(self) -> None:
        if not self._kaynakVar:
            return
        self._cal("set-source-mute", self._kaynakAd, "0" if self._kaynakMute else "1")
        self.yenile()

    # --- ozellikler --------------------------------------------------------
    cikisAd = Property(str, lambda s: s._cikisAd, notify=degisti)
    cikisYuzde = Property(int, lambda s: s._cikisYuzde, notify=degisti)
    cikisMute = Property(bool, lambda s: s._cikisMute, notify=degisti)
    cikisVar = Property(bool, lambda s: s._cikisVar, notify=degisti)
    kaynakAd = Property(str, lambda s: s._kaynakAd, notify=degisti)
    kaynakYuzde = Property(int, lambda s: s._kaynakYuzde, notify=degisti)
    kaynakMute = Property(bool, lambda s: s._kaynakMute, notify=degisti)
    kaynakVar = Property(bool, lambda s: s._kaynakVar, notify=degisti)
    mikrofonVar = Property(bool, lambda s: s._mikrofonVar, notify=degisti)
