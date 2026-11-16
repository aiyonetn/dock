"""X11 Shape uzantisi: input maskesi ve gecici bounding bosaltma."""
from __future__ import annotations

import ctypes
import os

_libX11 = ctypes.CDLL("libX11.so.6")
_libXext = ctypes.CDLL("libXext.so.6")


class _XRectangle(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_short),
        ("y", ctypes.c_short),
        ("width", ctypes.c_ushort),
        ("height", ctypes.c_ushort),
    ]


_libX11.XOpenDisplay.restype = ctypes.c_void_p
_libX11.XOpenDisplay.argtypes = [ctypes.c_char_p]
_libX11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
_libXext.XShapeCombineRectangles.argtypes = [
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.POINTER(_XRectangle),
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
]

_SHAPE_BOUNDING = 0
_SHAPE_INPUT = 2
_SHAPE_SET = 0
_UNSORTED = 0

_display = _libX11.XOpenDisplay(os.environ.get("DISPLAY", ":99").encode())
if not _display:
    _display = _libX11.XOpenDisplay(None)


def _uygula(pencere: int, dikdortgenler: list[tuple[int, int, int, int]], hedef: int) -> None:
    if not _display:
        return
    dizi = (_XRectangle * len(dikdortgenler))(
        *[_XRectangle(x, y, max(1, w), max(1, h)) for x, y, w, h in dikdortgenler]
    )
    _libXext.XShapeCombineRectangles(
        _display, pencere, hedef, 0, 0, dizi, len(dikdortgenler), _SHAPE_SET, _UNSORTED
    )
    _libX11.XSync(_display, 0)


def giris_maskesi(pencere: int, dikdortgenler: list[tuple[int, int, int, int]]) -> None:
    _uygula(pencere, dikdortgenler, _SHAPE_INPUT)


def bounding_bosalt(pencere: int) -> None:
    _uygula(pencere, [], _SHAPE_BOUNDING)


def bounding_tam(pencere: int, gen: int, yuk: int) -> None:
    _uygula(pencere, [(0, 0, gen, yuk)], _SHAPE_BOUNDING)
