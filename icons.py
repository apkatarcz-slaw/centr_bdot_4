# -*- coding: utf-8 -*-
"""Ikony kafelków: lokalne z zainstalowanej wtyczki lub z repozytorium.

Pobierany jest wyłącznie obrazek ikony (przez QgsNetworkAccessManager, z
ustawieniami proxy QGIS); wynik trafia do pamięci podręcznej na dysku.
"""

import os

from qgis.PyQt.QtCore import QObject, QRectF, Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest
from qgis.core import QgsApplication, QgsNetworkAccessManager

MAX_ICON_BYTES = 512 * 1024
_PALETTE = [
    "#3c78c8",
    "#5aa05a",
    "#c88228",
    "#a03c3c",
    "#6e50aa",
    "#288c96",
    "#5a5a8c",
]


def fallback_icon(key, label, size=64):
    """Zastępcza ikona: kolorowy kwadrat z pierwszą literą nazwy."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    idx = sum(ord(ch) for ch in key) % len(_PALETTE)  # stały kolor dla klucza
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(_PALETTE[idx]))
    painter.drawRoundedRect(QRectF(2, 2, size - 4, size - 4), 10, 10)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(size * 0.42))
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(
        QRectF(0, 0, size, size),
        Qt.AlignmentFlag.AlignCenter,
        (label or "?")[0].upper(),
    )
    painter.end()
    return QIcon(pix)


class IconProvider(QObject):
    iconReady = pyqtSignal(str)  # klucz wtyczki

    def __init__(self, parent=None):
        super().__init__(parent)
        self._memory = {}
        self._pending = {}
        self._cache_dir = os.path.join(
            QgsApplication.qgisSettingsDirPath(), "cache", "centrum_bdot_bdoo"
        )

    def _cache_path(self, key):
        return os.path.join(self._cache_dir, key.lower() + ".img")

    def icon(self, info):
        """Zwraca QIcon albo None (wtedy ikona jest pobierana w tle)."""
        key = info.key
        if info.icon_local:
            icon = QIcon(info.icon_local)
            if not icon.isNull():
                self._memory[key] = icon
                return icon
        if key in self._memory:
            return self._memory[key]
        cache = self._cache_path(key)
        if os.path.isfile(cache):
            pix = QPixmap()
            try:
                with open(cache, "rb") as fh:
                    ok = pix.loadFromData(fh.read())
            except OSError:
                ok = False
            if ok:
                self._memory[key] = QIcon(pix)
                return self._memory[key]
        if info.icon_url and key not in self._pending:
            self._request(key, info.icon_url)
        return None

    def forget_cache(self):
        self._memory.clear()

    def _request(self, key, url):
        request = QNetworkRequest(QUrl(url))
        reply = QgsNetworkAccessManager.instance().get(request)
        self._pending[key] = reply
        reply.finished.connect(lambda k=key, r=reply: self._finished(k, r))

    def _finished(self, key, reply):
        self._pending.pop(key, None)
        try:
            if reply.error() != QNetworkReply.NetworkError.NoError:
                return
            data = bytes(reply.read(MAX_ICON_BYTES + 1))
            if not data or len(data) > MAX_ICON_BYTES:
                return
            pix = QPixmap()
            if not pix.loadFromData(data):
                return
            self._memory[key] = QIcon(pix)
            try:
                os.makedirs(self._cache_dir, exist_ok=True)
                with open(self._cache_path(key), "wb") as fh:
                    fh.write(data)
            except OSError:
                pass
            self.iconReady.emit(key)
        finally:
            reply.deleteLater()


def numbered_icon(base_path, number, size=64):
    """Ikona launchera z nałożonym numerem grupy (1-10)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    base = QIcon(base_path).pixmap(size, size)
    painter.drawPixmap(0, 0, base)
    text = str(number)
    bw = int(size * (0.42 if number < 10 else 0.56))
    bh = int(size * 0.42)
    rect = QRectF(size - bw, size - bh, bw, bh)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#1e1e1e"))
    painter.drawRoundedRect(rect, size * 0.08, size * 0.08)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(bh * 0.8))
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    painter.end()
    return QIcon(pix)


def author_icon(size=64):
    """Ikona kafla „Inne wtyczki autora”: stos kart z plusem."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    k = size / 64
    painter.setBrush(QColor("#dcbe78"))
    painter.drawRoundedRect(
        QRectF(14 * k, 4 * k, 46 * k, 46 * k), 8 * k, 8 * k
    )
    painter.setBrush(QColor("#c89632"))
    painter.drawRoundedRect(
        QRectF(4 * k, 14 * k, 46 * k, 46 * k), 8 * k, 8 * k
    )
    font = QFont()
    font.setBold(True)
    font.setPixelSize(int(34 * k))
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(
        QRectF(4 * k, 14 * k, 46 * k, 46 * k),
        Qt.AlignmentFlag.AlignCenter,
        "+",
    )
    painter.end()
    return QIcon(pix)
