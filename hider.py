# -*- coding: utf-8 -*-
"""Ukrywanie ikon wtyczek z kafelkami na paskach narzędzi QGIS.

Launcher niczego nie usuwa ani nie zmienia w innych wtyczkach:
- polecenie (QAction) wtyczki jest tylko zdejmowane z paska narzędzi
  (menu Wtyczki / Wektor / Raster zostają bez zmian, polecenie działa),
- własny pasek narzędzi wtyczki jest chowany,
- przy usunięciu kafelka albo wyłączeniu launchera wszystko wraca
  na swoje miejsce.
"""

from qgis.PyQt import sip
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QToolBar
import qgis.utils

from . import catalog
from .state import _instance_actions


def _alive(obj):
    try:
        return obj is not None and not sip.isdeleted(obj)
    except TypeError:
        return False


def _find_ci(key, keys):
    low = key.lower()
    for k in keys:
        if k.lower() == low:
            return k
    return None


class IconHider:
    def __init__(self, iface, log=None):
        self.iface = iface
        self.log = log
        # klucz (małe litery) -> {"actions": [(pasek, akcja, następna)],
        #                         "toolbars": [pasek]}
        self.hidden = {}
        # pasek -> kolejność ikon zanim launcher cokolwiek z niego zdjął
        self.order = {}

    # ------------------------------------------------------------ pomocnicze
    def _toolbars(self):
        try:
            return self.iface.mainWindow().findChildren(QToolBar)
        except Exception:  # okno główne niedostępne (zamykanie QGIS)
            return []

    @staticmethod
    def _own_toolbars(instance):
        found = []
        try:
            values = list(vars(instance).values())
        except TypeError:
            return found
        for val in values:
            items = val if isinstance(val, (list, tuple)) else [val]
            for item in items:
                if isinstance(item, QToolBar) and item not in found:
                    found.append(item)
        return found

    def _note(self, text):
        if self.log is not None:
            self.log.info(text)

    # ------------------------------------------------------------ ukrywanie
    def hide(self, key):
        """Zdejmuje ikony wtyczki z pasków narzędzi. Można wołać wielokrotnie
        (np. po przeładowaniu wtyczki) - ukryje tylko to, co widać."""
        real = _find_ci(key, getattr(qgis.utils, "plugins", {}).keys())
        if real is None:
            return 0
        instance = qgis.utils.plugins.get(real)
        rec = self.hidden.setdefault(
            key.lower(), {"actions": [], "toolbars": []}
        )
        count = 0
        own = self._own_toolbars(instance)
        hidden_names = catalog.hidden_toolbars()
        for tb in own:
            if not _alive(tb) or tb in rec["toolbars"]:
                continue
            name = tb.objectName() or tb.windowTitle()
            # isHidden() = jawnie schowany (np. przez nas w poprzedniej
            # sesji - QGIS zapamiętuje stan pasków przy zamknięciu)
            user_hidden = tb.isHidden() and tb.testAttribute(
                Qt.WidgetAttribute.WA_WState_ExplicitShowHide
            )
            if user_hidden and name not in hidden_names:
                continue  # schował go użytkownik - nie ruszamy
            tb.setVisible(False)
            rec["toolbars"].append(tb)
            catalog.remember_toolbar(name, True)
            count += 1
        actions = [a for a in _instance_actions(instance) if _alive(a)]
        for tb in self._toolbars():
            if tb in own:
                continue
            tb_actions = tb.actions()
            if not any(act in tb_actions for act in actions):
                continue
            self._remember_order(tb)
            for act in actions:
                if act in tb_actions:
                    tb.removeAction(act)
                    rec["actions"].append((tb, act))
                    count += 1
        if count:
            self._note(
                "Ukryto ikony wtyczki {} na paskach narzędzi ({}).".format(
                    real, count
                )
            )
        return count

    def restore(self, key):
        rec = self.hidden.pop(key.lower(), None)
        if not rec:
            return 0
        count = 0
        for tb, act in rec["actions"]:
            if not (_alive(tb) and _alive(act)) or act in tb.actions():
                continue
            tb.insertAction(self._anchor(tb, act), act)
            count += 1
        for tb in rec["toolbars"]:
            if _alive(tb):
                tb.setVisible(True)
                catalog.remember_toolbar(
                    tb.objectName() or tb.windowTitle(), False
                )
                count += 1
        if count:
            self._note(
                "Przywrócono ikony wtyczki {} na paskach narzędzi.".format(key)
            )
        return count

    def _remember_order(self, tb):
        """Zapamiętuje kolejność ikon paska; nowe ikony (np. innej wtyczki
        włączonej później) dopisuje za ich obecnym poprzednikiem."""
        order = [a for a in self.order.get(tb, []) if _alive(a)]
        prev = None
        for act in tb.actions():
            if act not in order:
                pos = order.index(prev) + 1 if prev in order else 0
                order.insert(pos, act)
            prev = act
        self.order[tb] = order

    def _anchor(self, tb, act):
        """Ikona, przed którą wstawić przywracaną (None = na koniec),
        tak aby wróciła na swoje pierwotne miejsce."""
        order = self.order.get(tb, [])
        current = tb.actions()
        if act not in order:
            return None
        idx = order.index(act)
        for later in order[slice(idx + 1, None)]:
            if _alive(later) and later in current:
                return later
        return None

    def sync(self, keys_to_hide):
        """Ukrywa ikony wtyczek z listy, przywraca pozostałe."""
        wanted = {k.lower(): k for k in keys_to_hide}
        for low in list(self.hidden):
            if low not in wanted:
                self.restore(low)
        for low, key in wanted.items():
            self.hide(key)

    def restore_all(self):
        for low in list(self.hidden):
            self.restore(low)

    def is_hidden(self, key):
        rec = self.hidden.get(key.lower())
        return bool(rec and (rec["actions"] or rec["toolbars"]))
