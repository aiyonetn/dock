"""QML icin limit modeli ve 60 sn'lik arka plan yenileyicisi."""
from __future__ import annotations

import threading

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QByteArray,
    QModelIndex,
    QObject,
    QTimer,
    Qt,
    Signal,
    Slot,
)

from . import limitler


class LimitModel(QAbstractListModel):
    RolAd = Qt.UserRole + 1
    RolPlan = Qt.UserRole + 2
    RolKaynak = Qt.UserRole + 3
    RolSessionYuzde = Qt.UserRole + 4
    RolSessionReset = Qt.UserRole + 5
    RolWeeklyYuzde = Qt.UserRole + 6
    RolWeeklyReset = Qt.UserRole + 7

    veriDegisti = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._veri = {"codex": limitler._bos(), "claude": limitler._bos()}
        self._veri_var = False
        self._bayat = False

    veriVar = Property(bool, lambda self: self._veri_var, notify=veriDegisti)
    bayat = Property(bool, lambda self: self._bayat, notify=veriDegisti)

    def _saglayici(self, ad: str) -> dict:
        return self._veri.get(ad) or limitler._bos()

    codex = Property("QVariantMap", lambda self: self._saglayici("codex"), notify=veriDegisti)
    claude = Property("QVariantMap", lambda self: self._saglayici("claude"), notify=veriDegisti)

    def roleNames(self):
        return {
            self.RolAd: QByteArray(b"ad"),
            self.RolPlan: QByteArray(b"plan"),
            self.RolKaynak: QByteArray(b"kaynak"),
            self.RolSessionYuzde: QByteArray(b"sessionYuzde"),
            self.RolSessionReset: QByteArray(b"sessionReset"),
            self.RolWeeklyYuzde: QByteArray(b"weeklyYuzde"),
            self.RolWeeklyReset: QByteArray(b"weeklyReset"),
        }

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else 2

    def data(self, indeks, rol=Qt.DisplayRole):
        if not indeks.isValid() or indeks.row() > 1:
            return None
        anahtar = "codex" if indeks.row() == 0 else "claude"
        veri = self._veri.get(anahtar) or limitler._bos()
        if rol == self.RolAd:
            return "ChatGPT" if anahtar == "codex" else "Claude"
        if rol == self.RolPlan:
            return veri.get("plan") or ""
        if rol == self.RolKaynak:
            return veri.get("kaynak") or "yok"
        if rol == self.RolSessionYuzde:
            deger = (veri.get("session") or {}).get("percent")
            return -1.0 if deger is None else float(deger)
        if rol == self.RolSessionReset:
            return float((veri.get("session") or {}).get("reset") or 0)
        if rol == self.RolWeeklyYuzde:
            deger = (veri.get("weekly") or {}).get("percent")
            return -1.0 if deger is None else float(deger)
        if rol == self.RolWeeklyReset:
            return float((veri.get("weekly") or {}).get("reset") or 0)
        return None

    @Slot(object)
    def guncelle(self, veri: dict) -> None:
        veri = veri or {}
        if (veri.get("codex") or {}).get("kaynak") == "hata" and self._veri_var:
            veri["codex"] = self._veri.get("codex") or limitler._bos()
            self._bayat = True
        else:
            self._bayat = False
        self._veri = veri
        self._veri_var = True
        self.dataChanged.emit(self.index(0, 0), self.index(1, 0), list(self.roleNames().keys()))
        self.veriDegisti.emit()


class LimitYonetici(QObject):
    """Veriyi ayri thread'de okur; UI'yi kilitlemez."""

    veriHazir = Signal(object)

    def __init__(self, model: LimitModel, parent=None):
        super().__init__(parent)
        self.model = model
        self._mesgul = False
        self._deneme = 0
        self.veriHazir.connect(self._isle)
        self._zaman = QTimer(self)
        self._zaman.setInterval(60000)
        self._zaman.timeout.connect(self.yenile)
        self._zaman.start()
        self.yenile()

    def yenile(self) -> None:
        if self._mesgul:
            return
        self._mesgul = True
        threading.Thread(target=self._islet, daemon=True).start()

    def _islet(self) -> None:
        try:
            veri = limitler.oku()
        except Exception:
            veri = {"codex": limitler._bos(), "claude": limitler._bos()}
        finally:
            self._mesgul = False
        self.veriHazir.emit(veri)

    @Slot(object)
    def _isle(self, veri: dict) -> None:
        self.model.guncelle(veri)
        # Ilk okuma bosa duserse 5 sn arayla en fazla 3 kez dene.
        if (veri.get("codex") or {}).get("kaynak") != "api" and self._deneme < 3:
            self._deneme += 1
            QTimer.singleShot(5000, self.yenile)
        elif (veri.get("codex") or {}).get("kaynak") == "api":
            self._deneme = 0
