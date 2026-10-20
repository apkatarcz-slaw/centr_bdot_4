# -*- coding: utf-8 -*-
"""Log launchera: plik .log (UTF-8), panel „Komunikaty” QGIS, panel w oknie."""

import os
from datetime import datetime

from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import Qgis, QgsApplication, QgsMessageLog

TAG = "Centrum BDOT10k/BDOO"
LOG_NAME = "centrum_bdot_bdoo.log"
MAX_LOG_BYTES = 1024 * 1024  # po przekroczeniu 1 MB stary log trafia do .1

INFO, WARNING, ERROR = "info", "warning", "error"
_QGIS_LEVEL = {
    INFO: Qgis.MessageLevel.Info,
    WARNING: Qgis.MessageLevel.Warning,
    ERROR: Qgis.MessageLevel.Critical,
}


class Logger(QObject):
    """Zapisuje komunikaty i powiadamia panel logu w oknie."""

    message = pyqtSignal(str, str)  # (linia z czasem, poziom)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.path = os.path.join(
            QgsApplication.qgisSettingsDirPath(), LOG_NAME
        )
        self._rotate()

    def _rotate(self):
        try:
            if os.path.getsize(self.path) > MAX_LOG_BYTES:
                os.replace(self.path, self.path + ".1")
        except OSError:
            pass

    def write(self, text, level=INFO):
        now = datetime.now()
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(
                    "{}  [{}]  {}\n".format(
                        now.strftime("%Y-%m-%d %H:%M:%S"), level.upper(), text
                    )
                )
        except OSError:
            pass
        QgsMessageLog.logMessage(
            text, TAG, _QGIS_LEVEL.get(level, Qgis.MessageLevel.Info)
        )
        self.message.emit(
            "{}  {}".format(now.strftime("%H:%M:%S"), text), level
        )

    def info(self, text):
        self.write(text, INFO)

    def warning(self, text):
        self.write(text, WARNING)

    def error(self, text):
        self.write(text, ERROR)
