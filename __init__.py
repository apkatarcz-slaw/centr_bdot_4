# -*- coding: utf-8 -*-
"""Centrum wtyczek BDOT10k / BDOO (QGIS 4.x, PyQt6) - punkt wejścia wtyczki."""


def classFactory(iface):  # noqa: N802 (nazwa wymagana przez QGIS)
    from .plugin import CentrumPlugin

    return CentrumPlugin(iface)
