"""QML tarafina verilen ikon listesi modeli."""
from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt, Slot

from .uygulamalar import Uygulama


class IkonModel(QAbstractListModel):
    RolAd = Qt.UserRole + 1
    RolIkon = Qt.UserRole + 2
    RolCalisti = Qt.UserRole + 3
    RolParlama = Qt.UserRole + 4
    RolHata = Qt.UserRole + 5
    RolKimlik = Qt.UserRole + 6

    def __init__(self, uygulamalar: list[Uygulama], parent=None):
        super().__init__(parent)
        self.uygulamalar = uygulamalar
        self._calisti = [False] * len(uygulamalar)
        self._parlama = [0] * len(uygulamalar)
        self._hata = [""] * len(uygulamalar)

    def roleNames(self):
        return {
            self.RolAd: QByteArray(b"ad"),
            self.RolIkon: QByteArray(b"ikon"),
            self.RolCalisti: QByteArray(b"calisti"),
            self.RolParlama: QByteArray(b"parlama"),
            self.RolHata: QByteArray(b"hata"),
            self.RolKimlik: QByteArray(b"kimlik"),
        }

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.uygulamalar)

    def data(self, indeks, rol=Qt.DisplayRole):
        if not indeks.isValid():
            return None
        i = indeks.row()
        if rol == self.RolAd:
            return self.uygulamalar[i].ad
        if rol == self.RolIkon:
            return self.uygulamalar[i].ikon
        if rol == self.RolCalisti:
            return self._calisti[i]
        if rol == self.RolParlama:
            return self._parlama[i]
        if rol == self.RolHata:
            return self._hata[i]
        if rol == self.RolKimlik:
            return self.uygulamalar[i].kimlik
        return None

    @Slot(int, bool)
    def calisti_ayarla(self, i: int, deger: bool):
        if 0 <= i < len(self.uygulamalar) and self._calisti[i] != deger:
            self._calisti[i] = deger
            indeks = self.index(i, 0)
            self.dataChanged.emit(indeks, indeks, [self.RolCalisti])

    def parlama_tetikle(self, i: int, hata: str = ""):
        if not 0 <= i < len(self.uygulamalar):
            return
        self._hata[i] = hata
        self._parlama[i] += 1
        indeks = self.index(i, 0)
        self.dataChanged.emit(indeks, indeks, [self.RolParlama, self.RolHata])

    def hata_temizle(self, i: int):
        if 0 <= i < len(self.uygulamalar) and self._hata[i]:
            self._hata[i] = ""
            indeks = self.index(i, 0)
            self.dataChanged.emit(indeks, indeks, [self.RolHata])
