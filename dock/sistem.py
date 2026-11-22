"""Sistem sayaclari: CPU/RAM, ag hizi ve en cok tuketen surecler.

Okuma QThread icinde calisir; ana thread yalnizca hazir veriyi alir.
Sayaclar 1 sn, surec listesi 2 sn aralikla yenilenir.
"""
from __future__ import annotations

import time

from PySide6.QtCore import Property, QMetaObject, QObject, QThread, QTimer, Qt, Signal, Slot

try:
    import psutil
except ImportError:  # paket yoksa kart "veri yok" der; uydurma sayi uretilmez.
    psutil = None


def bos_veri() -> dict:
    return {
        "cpu": None,
        "ramYuzde": None,
        "ramKullanilan": None,
        "ramToplam": None,
        "indirme": None,
        "yukleme": None,
        "gecmis": [],
        "topCpu": [],
        "topRam": [],
        "zaman": 0.0,
        "gecmisSayisi": 0,
    }


class SistemModel(QObject):
    """QML'in okudugu tek QVariantMap: her yenilemede veriDegisti yayilir."""

    veriDegisti = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._veri = bos_veri()
        self._veri_var = False

    def _veri_getir(self):
        return self._veri

    def _veri_var_mi(self) -> bool:
        return self._veri_var

    veri = Property("QVariantMap", _veri_getir, notify=veriDegisti)
    veriVar = Property(bool, _veri_var_mi, notify=veriDegisti)

    @Slot(object)
    def guncelle(self, veri: dict) -> None:
        if not veri:
            return
        gecerli = veri.get("cpu") is not None and veri.get("ramYuzde") is not None
        self._veri = veri
        self._veri_var = bool(gecerli)
        self.veriDegisti.emit()


class _Okuyucu(QObject):
    """QThread icinde yasar; QTimer'lar bu thread'de kurulur."""

    hazir = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._surecler: dict[int, object] = {}
        self._adlar: dict[int, str] = {}
        self._cpu_gecmis: dict[int, tuple[float, float]] = {}
        self._top_cpu: list[dict] = []
        self._top_ram: list[dict] = []
        self._gecmis: list[list[float]] = []
        self._ag_son: tuple[int, int] | None = None
        self._zaman_son = 0.0
        self._sayac = None
        self._surec_sayac = None

    @Slot()
    def basla(self) -> None:
        if psutil is None:
            self.hazir.emit(bos_veri())
            return
        try:
            psutil.cpu_percent(None)  # ilk cagri taban cizgisi
            self._ag_son = self._ag_oku()
            self._zaman_son = time.monotonic()
        except Exception:
            self.hazir.emit(bos_veri())
            return
        self._sayac = QTimer(self)
        self._sayac.setInterval(1000)
        self._sayac.timeout.connect(self._tick)
        self._sayac.start()
        # Surec taramasi yalniz ust listeler gorunurken calisir; CPU/RAM/ag
        # kartlari acikken bosuna /proc gezilmez.
        self._surec_sayac = QTimer(self)
        self._surec_sayac.setInterval(2000)
        self._surec_sayac.timeout.connect(self._surec_tara)

    @staticmethod
    def _ag_oku() -> tuple[int, int]:
        toplam_in = toplam_out = 0
        for ad, sayac in psutil.net_io_counters(pernic=True).items():
            if ad == "lo":
                continue
            toplam_in += sayac.bytes_recv
            toplam_out += sayac.bytes_sent
        return toplam_in, toplam_out

    @Slot()
    def _tick(self) -> None:
        try:
            simdi = time.monotonic()
            gecen = max(0.001, simdi - self._zaman_son)
            self._zaman_son = simdi
            ag = self._ag_oku()
            indirme = yukleme = 0.0
            if self._ag_son is not None:
                indirme = max(0.0, (ag[0] - self._ag_son[0]) / gecen)
                yukleme = max(0.0, (ag[1] - self._ag_son[1]) / gecen)
            self._ag_son = ag
            self._gecmis.append([round(indirme, 1), round(yukleme, 1)])
            if len(self._gecmis) > 60:
                del self._gecmis[: len(self._gecmis) - 60]

            cpu = psutil.cpu_percent(None)
            bellek = psutil.virtual_memory()
            veri = {
                "cpu": round(float(cpu), 1),
                "ramYuzde": round(float(bellek.percent), 1),
                "ramKullanilan": round((bellek.total - bellek.available) / (1024**3), 2),
                "ramToplam": round(bellek.total / (1024**3), 2),
                "indirme": round(indirme, 1),
                "yukleme": round(yukleme, 1),
                "gecmis": list(self._gecmis),
                "topCpu": list(self._top_cpu),
                "topRam": list(self._top_ram),
                "zaman": time.time(),
                "gecmisSayisi": len(self._gecmis),
            }
        except Exception:
            veri = bos_veri()
        self.hazir.emit(veri)

    @Slot(bool)
    def surecleri_izle(self, acik: bool) -> None:
        if self._surec_sayac is None:
            return
        if acik:
            self._top_cpu = []
            self._top_ram = []
            self._surec_tara()
            self._surec_sayac.start()
        else:
            self._surec_sayac.stop()

    @Slot()
    def durdur(self) -> None:
        for zaman in (self._sayac, self._surec_sayac):
            if zaman is not None:
                zaman.stop()

    @Slot()
    def _surec_tara(self) -> None:
        if psutil is None:
            return
        try:
            simdi = time.monotonic()
            canli = set(psutil.pids())
            for pid in list(self._surecler):
                if pid not in canli:
                    self._surecler.pop(pid, None)
                    self._adlar.pop(pid, None)
                    self._cpu_gecmis.pop(pid, None)
            for pid in canli:
                if pid in self._surecler:
                    continue
                try:
                    surec = psutil.Process(pid)
                    self._surecler[pid] = surec
                    self._adlar[pid] = (surec.name() or str(pid)).strip()
                    self._cpu_gecmis[pid] = (sum(surec.cpu_times()[:2]), simdi)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            cpu_ad: dict[str, dict] = {}
            ram_ad: dict[str, dict] = {}
            for pid, surec in list(self._surecler.items()):
                try:
                    toplam = sum(surec.cpu_times()[:2])
                    rss = int(surec.memory_info().rss)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    self._surecler.pop(pid, None)
                    self._adlar.pop(pid, None)
                    self._cpu_gecmis.pop(pid, None)
                    continue
                except Exception:
                    continue
                once = self._cpu_gecmis.get(pid)
                self._cpu_gecmis[pid] = (toplam, simdi)
                ad = self._adlar.get(pid) or str(pid)
                yuzde = 0.0
                if once is not None:
                    gecen = simdi - once[1]
                    if gecen > 0.05:
                        yuzde = max(0.0, (toplam - once[0]) / gecen * 100.0)
                kayit = cpu_ad.setdefault(ad, {"ad": ad, "cpu": 0.0})
                kayit["cpu"] += yuzde
                bellek = ram_ad.setdefault(ad, {"ad": ad, "bayt": 0})
                bellek["bayt"] += rss

            cekirdek = max(1, psutil.cpu_count() or 1)
            cpu_liste = [
                x
                for x in sorted(cpu_ad.values(), key=lambda x: x["cpu"], reverse=True)
                if x["cpu"] / cekirdek >= 0.05
            ][:3]
            self._top_cpu = [
                {"ad": x["ad"], "yuzde": round(min(100.0, x["cpu"] / cekirdek), 1)}
                for x in cpu_liste
            ]
            ram_liste = [
                x
                for x in sorted(ram_ad.values(), key=lambda x: x["bayt"], reverse=True)
                if x["bayt"] >= 1024**2
            ][:3]
            self._top_ram = [
                {"ad": x["ad"], "mb": round(x["bayt"] / (1024**2), 0)}
                for x in ram_liste
            ]
        except Exception:
            self._top_cpu = []
            self._top_ram = []


class SistemYonetici(QObject):
    """Okuyucu thread'i kurar, modeli ana thread'de gunceller."""

    veriHazir = Signal(object)
    surecIzle = Signal(bool)

    def __init__(self, model: SistemModel, parent=None):
        super().__init__(parent)
        self.model = model
        self._thread = QThread(self)
        self._okuyucu = _Okuyucu()
        self._okuyucu.moveToThread(self._thread)
        self._thread.started.connect(self._okuyucu.basla)
        self._okuyucu.hazir.connect(self._isle)
        self.surecIzle.connect(self._okuyucu.surecleri_izle)
        self._thread.start()

    @Slot(object)
    def _isle(self, veri: dict) -> None:
        self.model.guncelle(veri)
        self.veriHazir.emit(veri)

    def izle(self, acik: bool) -> None:
        self.surecIzle.emit(acik)

    def durdur(self) -> None:
        if self._thread.isRunning():
            QMetaObject.invokeMethod(self._okuyucu, "durdur", Qt.BlockingQueuedConnection)
            self._thread.quit()
            self._thread.wait(2000)
