# -*- coding: utf-8 -*-
"""Rejestracja wtyczki: ikony grup 1-10 na pasku narzędzi i w menu Wtyczki,
okna grup oraz okno „Inne wtyczki autora”."""

import os

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QAction  # Qt6: QAction jest w QtGui

from . import catalog
from .i18n import esc, tip
from .hider import IconHider
from .icons import numbered_icon
from .logger import Logger

MENU = "&Centrum wtyczek BDOT10k / BDOO (QGIS 4.x)"
ICON = os.path.join(os.path.dirname(__file__), "icon.png")


class CentrumPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.actions = {}
        self.dialogs = {}
        self.author_dialog = None
        self.log = None
        self.hider = None

    # ------------------------------------------------------------ QGIS
    def initGui(self):  # noqa: N802
        self.log = Logger()
        self.hider = IconHider(self.iface, self.log)
        for n in catalog.groups():
            self._add_action(n)
        # ikony innych wtyczek chowamy, gdy wszystkie wtyczki się wczytają:
        # przy starcie QGIS po sygnale initializationCompleted, a przy
        # włączeniu launchera w trakcie pracy - z krótkim opóźnieniem
        try:
            self.iface.initializationCompleted.connect(self.sync_icons)
        except (AttributeError, TypeError):
            pass
        QTimer.singleShot(1500, self.sync_icons)

    def sync_icons(self):
        """Chowa ikony pasków narzędzi wtyczek z kafelkami, pozostałe
        przywraca."""
        if self.hider is not None:
            self.hider.sync(catalog.keys_to_hide())

    def unload(self):
        if self.hider is not None:
            self.hider.restore_all()
            self.hider = None
        try:
            self.iface.initializationCompleted.disconnect(self.sync_icons)
        except (AttributeError, TypeError, RuntimeError):
            pass
        for dlg in list(self.dialogs.values()) + [self.author_dialog]:
            if dlg is not None:
                dlg.close()
                dlg.deleteLater()
        self.dialogs = {}
        self.author_dialog = None
        for n in list(self.actions):
            self._remove_action(n)

    # ------------------------------------------------------------ ikony
    def _add_action(self, n):
        action = QAction(numbered_icon(ICON, n), "", self.iface.mainWindow())
        action.triggered.connect(lambda _=False, g=n: self.open_group(g))
        self.actions[n] = action
        self._label_action(n)
        self.iface.addToolBarIcon(action)
        self.iface.addPluginToMenu(MENU, action)

    def _remove_action(self, n):
        action = self.actions.pop(n, None)
        if action is not None:
            self.iface.removePluginMenu(MENU, action)
            self.iface.removeToolBarIcon(action)
            action.deleteLater()

    def _label_action(self, n):
        group = catalog.Group(n)
        title = catalog.title()
        desc = group.description()
        self.actions[n].setText(
            "{} – {} {}".format(title, n, "• " + desc if desc else "").strip()
        )
        self.actions[n].setToolTip(
            tip(
                "{}{}. Kliknij, aby otworzyć kafelki tej grupy.".format(
                    esc(title), " – " + esc(desc) if desc else ""
                ),
                "{}{}. Click to open the tiles of this group.".format(
                    esc(title), " – " + esc(desc) if desc else ""
                ),
                "Grupa {}".format(n),
                "Group {}".format(n),
            )
        )

    def set_icons_off(self, value):
        """Przycisk „Wyłącz ikony / Włącz ikony” - wspólny dla grup."""
        catalog.set_icons_off(value)
        if self.log is not None:
            self.log.info(
                "Ikony wtyczek z kafelkami na paskach narzędzi: {}.".format(
                    "wyłączone" if value else "włączone"
                )
            )
        self.sync_icons()
        for dlg in self.dialogs.values():
            dlg.update_icons_button()
            dlg.repaint_tiles()

    def set_tile_scale(self, value):
        """Suwak / okienko „Skaluj ikony” - wspólne dla grup i okna autora."""
        value = catalog.set_tile_scale(value)
        dialogs = list(self.dialogs.values()) + [self.author_dialog]
        for dlg in dialogs:
            if dlg is not None:
                dlg.apply_scale()
        return value

    def update_titles(self):
        for n in self.actions:
            self._label_action(n)
        for dlg in self.dialogs.values():
            dlg.update_titles()

    # ------------------------------------------------------------ okna
    @staticmethod
    def _show(dlg):
        if dlg.windowState() & Qt.WindowState.WindowMinimized:
            dlg.setWindowState(
                dlg.windowState() & ~Qt.WindowState.WindowMinimized
            )
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def run(self):
        self.open_group(1)

    def open_group(self, n):
        dlg = self.dialogs.get(n)
        if dlg is None:
            from .dialog import LauncherDialog

            dlg = LauncherDialog(self.iface, self, group=n)
            self.dialogs[n] = dlg
        self._show(dlg)

    def open_author(self):
        if self.author_dialog is None:
            from .dialog import LauncherDialog

            self.author_dialog = LauncherDialog(
                self.iface, self, author_mode=True
            )
        self._show(self.author_dialog)

    # ------------------------------------------------------------ grupy
    def create_group(self, description=""):
        n = catalog.add_group(description)
        if n is None:
            return None
        self._add_action(n)
        self.update_titles()
        self.open_group(n)
        return n

    def delete_group(self, n):
        if n == 1:
            return
        dlg = self.dialogs.pop(n, None)
        if dlg is not None:
            dlg.close()
            dlg.deleteLater()
        catalog.remove_group(n)
        self._remove_action(n)
        self.update_titles()
        self.sync_icons()
