"""Ekrana sigan dock olculeri.

Qt'siz saf fonksiyon: uygulama, test scriptleri ve otomasyon ayni sayilari
buradan alir. Kural: panel (buyumus haliyle de) ekran genisliginden
2*emniyet kadar kucuk kalmali.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

EMNIYET = 24  # panel ile ekran kenari arasinda en az bosluk (px)
MIN_IKON = 20
MIN_BOSLUK = 4
MIN_YAN = 4


@dataclass(frozen=True)
class Olcu:
    ekran_genislik: int
    ikon_sayisi: int
    ikon_boyut: int
    buyutme: float
    bosluk: int
    yan_bosluk: int
    taban_panel_genislik: int
    hover_panel_genislik: int
    pencere_yan_pay: int
    pencere_genislik: int
    pencere_x: int
    panel_x: int
    emniyet: int
    kirpildi: bool
    nedenler: tuple[str, ...]

    @property
    def panel_ekran_x(self) -> int:
        return self.pencere_x + self.panel_x

    @property
    def sinir_genislik(self) -> int:
        return self.ekran_genislik - 2 * self.emniyet


def _panel(n: int, ikon: int, bosluk: int, yan: int) -> int:
    return n * ikon + (n - 1) * bosluk + 2 * yan


def hesapla(
    ekran_genislik: int,
    ikon_sayisi: int,
    istenen_ikon: int,
    istenen_buyutme: float,
    *,
    bosluk: int = 12,
    yan_bosluk: int = 16,
    emniyet: int = EMNIYET,
    pencere_yan_pay: int = 120,
    min_ikon: int = MIN_IKON,
    min_bosluk: int = MIN_BOSLUK,
    min_yan: int = MIN_YAN,
) -> Olcu:
    """Istenen olculeri ekrana sigacak sekilde kisitlar.

    Sirasi: ikon boyutu -> bosluklar -> buyutme -> (cok kucuk ekran) ikon.
    Hover genisligi de sinir icine girer; boylece imlec en uctaki ikonun
    uzerindeyken panel ekran kenarina dayanmaz.
    """
    ekran = max(1, int(ekran_genislik))
    n = max(1, int(ikon_sayisi))
    istenen_ikon = max(1, int(istenen_ikon))
    istenen_buyutme = max(1.0, float(istenen_buyutme))
    sinir = max(1, ekran - 2 * int(emniyet))

    ikon = istenen_ikon
    alan = max(0, int(bosluk))
    yan = max(0, int(yan_bosluk))
    buy = istenen_buyutme
    nedenler: list[str] = []

    def hover() -> float:
        return _panel(n, ikon, alan, yan) + (buy - 1.0) * ikon

    # 1) Buyumus panel de sigana kadar ikon boyutunu kucult.
    while hover() > sinir and ikon > min_ikon:
        ikon -= 1
    # 2) Ikon alt sinirdaysa once bosluklari daralt.
    while hover() > sinir and (alan > min_bosluk or yan > min_yan):
        if alan > min_bosluk:
            alan -= 1
        else:
            yan -= 1
    # 3) Hala sigmiyorsa buyutme miktarini sinirla.
    if hover() > sinir:
        kalan = sinir - _panel(n, ikon, alan, yan)
        buy = max(1.0, min(buy, 1.0 + kalan / ikon))
    # 4) Cok kucuk ekran: temel panel de sigmiyorsa dibe kadar kucult.
    while _panel(n, ikon, alan, yan) > sinir and ikon > 1:
        ikon -= 1
    while _panel(n, ikon, alan, yan) > sinir and alan > 0:
        alan -= 1
    while _panel(n, ikon, alan, yan) > sinir and yan > 0:
        yan -= 1

    if ikon != istenen_ikon:
        nedenler.append(f"ikon {istenen_ikon}->{ikon}")
    if alan != bosluk:
        nedenler.append(f"bosluk {bosluk}->{alan}")
    if yan != yan_bosluk:
        nedenler.append(f"yan bosluk {yan_bosluk}->{yan}")
    if abs(buy - istenen_buyutme) > 1e-9:
        nedenler.append(f"buyutme {istenen_buyutme:g}->{buy:.2f}")

    taban = _panel(n, ikon, alan, yan)
    hover_gen = int(math.ceil(hover() - 1e-9))
    pay = min(max(0, int(pencere_yan_pay)), max(0, (ekran - hover_gen) // 2))
    gen = hover_gen + 2 * pay
    if gen > ekran:  # guvenlik: her zaman ekrana sig
        gen = ekran
        pay = max(0, (ekran - hover_gen) // 2)
    x = max(0, min(ekran - gen, (ekran - gen) // 2))
    # QML Math.round((pencere - panel) / 2) ile ayni yarim-yukari yuvarlama.
    panel_x = int(math.floor((gen - taban) / 2 + 0.5))

    return Olcu(
        ekran_genislik=ekran,
        ikon_sayisi=n,
        ikon_boyut=ikon,
        buyutme=buy,
        bosluk=alan,
        yan_bosluk=yan,
        taban_panel_genislik=taban,
        hover_panel_genislik=hover_gen,
        pencere_yan_pay=pay,
        pencere_genislik=gen,
        pencere_x=x,
        panel_x=panel_x,
        emniyet=int(emniyet),
        kirpildi=bool(nedenler),
        nedenler=tuple(nedenler),
    )
