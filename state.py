# -*- coding: utf-8 -*-
"""Integracja z QGIS: stan wtyczek, włączanie, otwieranie, Menedżer wtyczek.

Launcher niczego nie pobiera ani nie instaluje. Dane o wersjach w repozytorium
pochodzą z wbudowanego mechanizmu QGIS (pyplugin_installer), a instalację
i aktualizację użytkownik zatwierdza sam w Menedżerze wtyczek.
"""

import os
import re
import sys

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtGui import QAction  # Qt6: QAction jest w QtGui
from qgis.PyQt.QtWidgets import QApplication, QLineEdit, QMenu
from qgis.core import Qgis, QgsMessageLog, QgsSettings
import qgis.utils

from .catalog import OWN_KEYS, REPO_PAGE, CatalogEntry, is_author

# Stany kafelka
OK = "ok"  # zainstalowana i aktywna
UPDATE = "update"  # aktywna, w repozytorium jest nowsza wersja
DISABLED = "disabled"  # zainstalowana, wyłączona
BROKEN = "broken"  # zainstalowana, ale nie uruchamia się
NOT_INSTALLED = "not_installed"
UNAVAILABLE = "unavailable"  # brak w repozytorium dla tej wersji QGIS

# Zakładki Menedżera wtyczek QGIS
TAB_ALL, TAB_INSTALLED, TAB_NOT_INSTALLED, TAB_UPGRADEABLE = 0, 1, 2, 3

_SKIP_ACTION = re.compile(
    r"(pomoc|help|o wtyczce|about|informacj|ustawieni|settings|konfigur|"
    r"dokumentac|instrukcj|zgłoś|report)",
    re.IGNORECASE,
)


class PluginInfo:
    """Stan jednej wtyczki z listy."""

    def __init__(self, entry):
        self.key = entry.key
        self.custom = getattr(entry, "custom", "") or ""
        self.original = entry.label  # oryginalna nazwa wtyczki
        self.label = self.custom or entry.label  # podpis kafelka
        self.description = entry.description
        self.real_key = entry.key  # klucz z właściwą wielkością liter
        self.repo_name = entry.label
        self.state = NOT_INSTALLED
        self.version_installed = ""
        self.version_available = ""
        self.version_experimental = ""
        self.has_experimental = False
        self.icon_local = ""
        self.icon_url = ""
        self.error = ""
        self.algorithms = []  # (id, nazwa, grupa) algorytmów Processing
        self.homepage = REPO_PAGE.format(key=entry.key)

    def signature(self):
        return (
            self.state,
            self.version_installed,
            self.version_available,
            self.has_experimental,
        )


# --------------------------------------------------------------- pomocnicze
def _note(where, exc):
    """Błąd niekrytyczny: wpis do panelu Komunikaty QGIS (bez przerywania)."""
    QgsMessageLog.logMessage(
        "{}: {}".format(where, exc),
        "Centrum BDOT10k/BDOO",
        Qgis.MessageLevel.Info,
    )


def _installer_data():
    try:
        from pyplugin_installer import installer_data

        return installer_data
    except Exception:  # brak modułu (np. QGIS bez Pythonowego instalatora)
        return None


def _find_ci(key, keys):
    low = key.lower()
    for k in keys:
        if k.lower() == low:
            return k
    return None


def compare_versions(a, b):
    """1 gdy a nowsza, 2 gdy b nowsza, 0 gdy równe."""
    try:
        from pyplugin_installer.version_compare import compareVersions

        return compareVersions(a, b)
    except Exception:
        return 0 if a == b else 1


def repository_records():
    """(słownik rekordów wtyczek, czy repozytorium zostało pobrane)."""
    data = _installer_data()
    if data is None:
        return {}, False
    try:
        fetched = any(
            r.get("state") == 2 for r in data.repositories.all().values()
        )
        return data.plugins.all(), fetched
    except Exception:
        return {}, False


def plugin_dir(key):
    mod = sys.modules.get(key)
    if mod is not None and getattr(mod, "__file__", None):
        return os.path.dirname(mod.__file__)
    for base in getattr(qgis.utils, "plugin_paths", []):
        path = os.path.join(base, key)
        if os.path.isdir(path):
            return path
    return ""


def _metadata(key, field):
    try:
        value = qgis.utils.pluginMetadata(key, field)
    except Exception:
        return ""
    return "" if value in (None, "__error__") else str(value)


# --------------------------------------------------------------- odczyt stanu
def collect(catalog):
    try:
        qgis.utils.updateAvailablePlugins()
    except Exception as exc:
        _note("updateAvailablePlugins", exc)
    records, fetched = repository_records()
    available = list(getattr(qgis.utils, "available_plugins", []))
    active = list(getattr(qgis.utils, "active_plugins", []))
    loaded = getattr(qgis.utils, "plugins", {})
    settings = QgsSettings()

    result = []
    for entry in catalog:
        info = PluginInfo(entry)
        real = _find_ci(entry.key, available)
        rec_key = _find_ci(entry.key, records.keys())
        rec = records.get(rec_key) or {}
        info.real_key = real or rec_key or entry.key
        info.repo_name = rec.get("name") or entry.label
        info.original = info.repo_name
        if rec.get("description"):
            info.description = rec.get("description")
        icon = rec.get("icon") or ""
        if isinstance(icon, str) and icon.startswith("https://"):
            info.icon_url = icon
        info.version_available = rec.get("version_available") or ""
        exp = rec.get("version_available_experimental") or ""

        if real:
            info.original = _metadata(real, "name") or info.original
            info.version_installed = _metadata(real, "version")
            icon_rel = _metadata(real, "icon")
            pdir = plugin_dir(real)
            if icon_rel and pdir:
                path = os.path.join(pdir, icon_rel)
                if os.path.isfile(path):
                    info.icon_local = path
            if not info.description or info.description == entry.description:
                info.description = (
                    _metadata(real, "description") or info.description
                )
            enabled_flag = (
                str(settings.value("PythonPlugins/" + real, "false")).lower()
                == "true"
            )
            if rec.get("error") in ("incompatible", "broken", "dependent"):
                info.state = BROKEN
                info.error = rec.get("error_details") or rec.get("error")
            elif real in active and real in loaded:
                info.algorithms = plugin_algorithms(real)
                if rec.get("status") == "upgradeable":
                    info.state = UPDATE
                else:
                    info.state = OK
            elif enabled_flag and real not in active:
                info.state = BROKEN
                info.error = "wtyczka jest włączona, ale nie uruchomiła się"
            else:
                info.state = DISABLED
        else:
            if rec and rec.get("status") != "orphan":
                info.state = NOT_INSTALLED
            elif fetched:
                info.state = UNAVAILABLE
            else:
                info.state = NOT_INSTALLED

        info.label = info.custom or info.original
        if exp:
            base = (
                info.version_installed
                or rec.get("version_available_stable")
                or ""
            )
            if not base or compare_versions(exp, base) == 1:
                info.has_experimental = True
                info.version_experimental = exp
        result.append(info)
    return result, fetched


def _is_core(key, path):
    """Wtyczka dostarczana z QGIS (katalog systemowy), np. Processing."""
    core = getattr(qgis.utils, "sys_plugin_path", "") or ""
    if not core:
        return False
    if os.path.isdir(os.path.join(core, key)):
        return True
    if not path:
        return False
    try:
        return os.path.commonpath(
            [os.path.realpath(core), os.path.realpath(path)]
        ) == os.path.realpath(core)
    except ValueError:  # inne dyski w Windows
        return False


def installed_plugins():
    """Zainstalowane wtyczki z repozytorium (bez wbudowanych w QGIS),
    także wyłączone. Lista słowników posortowana po nazwie."""
    try:
        qgis.utils.updateAvailablePlugins()
    except Exception as exc:
        _note("updateAvailablePlugins", exc)
    active = set(getattr(qgis.utils, "active_plugins", []))
    result = []
    for key in getattr(qgis.utils, "available_plugins", []):
        if key.lower() in OWN_KEYS:
            continue
        pdir = plugin_dir(key)
        if _is_core(key, pdir):
            continue
        icon = _metadata(key, "icon")
        icon_path = os.path.join(pdir, icon) if icon and pdir else ""
        result.append(
            {
                "key": key,
                "name": _metadata(key, "name") or key,
                "description": _metadata(key, "description"),
                "tags": _metadata(key, "tags"),
                "icon": icon_path if os.path.isfile(icon_path) else "",
                "active": key in active,
            }
        )
    result.sort(key=lambda r: r["name"].lower())
    return result


def author_entries():
    """Wtyczki autora: z repozytorium QGIS (tylko wersje zgodne z tym QGIS
    - instalator QGIS sam pomija niezgodne) oraz zainstalowane lokalnie."""
    records, _ = repository_records()
    found = {}
    for key, rec in records.items():
        if key.lower() in OWN_KEYS or not is_author(rec.get("author_name")):
            continue
        found[key.lower()] = CatalogEntry(
            key,
            str(rec.get("name") or key),
            str(rec.get("description") or ""),
        )
    for key in getattr(qgis.utils, "available_plugins", []):
        if key.lower() in OWN_KEYS or key.lower() in found:
            continue
        if is_author(_metadata(key, "author")):
            found[key.lower()] = CatalogEntry(
                key,
                _metadata(key, "name") or key,
                _metadata(key, "description"),
            )
    return sorted(found.values(), key=lambda e: e.label.lower())


# --------------------------------------------------------------- akcje
def fetch_repository(reload=False):
    """Pobiera listę wtyczek mechanizmem QGIS (może pokazać okno postępu)."""
    try:
        import pyplugin_installer

        pyplugin_installer.instance().fetchAvailablePlugins(reload)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def enable_and_start(key):
    """Włącza zainstalowaną wtyczkę (jak zaznaczenie w Menedżerze wtyczek)."""
    settings = QgsSettings()
    settings.setValue("PythonPlugins/" + key, True)
    try:
        if not qgis.utils.loadPlugin(key):
            raise RuntimeError("nie udało się załadować kodu wtyczki")
        if not qgis.utils.startPlugin(key):
            raise RuntimeError("wtyczka nie uruchomiła się")
    except Exception as exc:
        settings.setValue("PythonPlugins/" + key, False)
        return False, str(exc)
    data = _installer_data()
    if data is not None:
        try:
            data.plugins.getAllInstalled()
            data.plugins.rebuild()
        except Exception as exc:
            _note("odświeżenie danych instalatora", exc)
    return True, ""


def _plain(text):
    return text.replace("&", "").replace("…", "").replace("...", "").strip()


def _instance_actions(instance):
    found, seen = [], set()

    def add(obj):
        if isinstance(obj, QAction):
            if id(obj) in seen or obj.isSeparator() or not _plain(obj.text()):
                return
            seen.add(id(obj))
            found.append(obj)
        elif isinstance(obj, QMenu):
            for act in obj.actions():
                add(act)

    try:
        values = list(vars(instance).values())
    except TypeError:
        values = []
    for val in values:
        if isinstance(val, (QAction, QMenu)):
            add(val)
        elif isinstance(val, (list, tuple, set)):
            for item in val:
                add(item)
        elif isinstance(val, dict):
            for item in val.values():
                add(item)
    return found


def _menu_actions(iface, name):
    """Akcje z podmenu o nazwie wtyczki (menu Wtyczki, Wektor, Raster...)."""
    target = _plain(name).lower()
    result = []

    def walk(menu, depth=0):
        if depth > 3:
            return
        for act in menu.actions():
            sub = act.menu()
            if sub is None:
                continue
            if _plain(sub.title()).lower() == target:
                result.extend(
                    a
                    for a in sub.actions()
                    if not a.isSeparator() and a.menu() is None
                )
            else:
                walk(sub, depth + 1)

    try:
        for act in iface.mainWindow().menuBar().actions():
            if act.menu() is not None:
                walk(act.menu())
    except Exception as exc:
        _note("przeszukiwanie menu", exc)
    return result


# --------------------------------------------------------------- Processing
_ALG_DIALOGS = []  # otwarte okna algorytmów (żeby nie zniknęły)


def _plugin_providers(key, instance):
    """Dostawcy Processing należący do wtyczki: zapisani w atrybutach
    wtyczki (np. self.provider) albo zdefiniowani w jej katalogu."""
    try:
        from qgis.core import QgsApplication, QgsProcessingProvider
    except ImportError:
        return []
    found = []

    def add(obj):
        if isinstance(obj, QgsProcessingProvider) and obj not in found:
            found.append(obj)

    try:
        values = list(vars(instance).values())
    except TypeError:
        values = []
    for val in values:
        if isinstance(val, (list, tuple, set)):
            for item in val:
                add(item)
        elif isinstance(val, dict):
            for item in val.values():
                add(item)
        else:
            add(val)
    try:
        registry = QgsApplication.processingRegistry()
        providers = registry.providers() if registry is not None else []
    except Exception as exc:
        _note("rejestr Processing", exc)
        providers = []
    low = key.lower()
    for prov in providers:
        module = (type(prov).__module__ or "").split(".")[0].lower()
        try:
            pid = prov.id().lower()
        except Exception:
            pid = ""
        if module == low or pid == low:
            add(prov)
    return found


def plugin_algorithms(key):
    """Algorytmy Processing wtyczki: lista (id, nazwa, grupa)."""
    instance = getattr(qgis.utils, "plugins", {}).get(key)
    if instance is None:
        return []
    algs, seen = [], set()
    for prov in _plugin_providers(key, instance):
        try:
            items = prov.algorithms()
        except Exception as exc:
            _note("algorytmy {}".format(key), exc)
            continue
        for alg in items:
            try:
                aid = alg.id()
                if aid in seen:
                    continue
                seen.add(aid)
                algs.append((aid, alg.displayName(), alg.group()))
            except Exception as exc:
                _note("algorytm {}".format(key), exc)
    algs.sort(key=lambda a: (a[2].lower(), a[1].lower()))
    return algs


def open_algorithm(alg_id):
    """Otwiera okno algorytmu Processing (jak dwuklik w panelu)."""
    import processing

    create = getattr(processing, "createAlgorithmDialog", None)
    if create is not None:
        dlg = create(alg_id, {})
        if dlg is None:
            raise RuntimeError("nie znaleziono algorytmu {}".format(alg_id))
        _ALG_DIALOGS[:] = [d for d in _ALG_DIALOGS if _alive_dialog(d)]
        _ALG_DIALOGS.append(dlg)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
    else:  # starsze QGIS - okno modalne
        processing.execAlgorithmDialog(alg_id, {})


def _alive_dialog(dlg):
    try:
        from qgis.PyQt import sip

        return not sip.isdeleted(dlg) and dlg.isVisible()
    except Exception:
        return False


def show_in_toolbox(iface, text):
    """Pokazuje panel Processing z wpisaną nazwą w polu wyszukiwania."""
    toolbox = None
    proc = getattr(qgis.utils, "plugins", {}).get("processing")
    if proc is not None:
        toolbox = getattr(proc, "toolbox", None)
    if toolbox is None:
        from qgis.PyQt.QtWidgets import QDockWidget

        toolbox = iface.mainWindow().findChild(
            QDockWidget, "ProcessingToolbox"
        )
    if toolbox is None:
        return False
    toolbox.setVisible(True)
    toolbox.raise_()
    search = getattr(toolbox, "searchBox", None)
    if search is None:
        found = toolbox.findChildren(QLineEdit)
        search = found[0] if found else None
    if search is not None:
        search.setText(text)
        search.setFocus()
    return True


# --------------------------------------------------------------- otwieranie
def open_plugin(iface, info, logger):
    """Uruchamia wtyczkę: polecenie z menu/paska albo algorytm Processing.
    Zwraca (ok, komunikat)."""
    instance = getattr(qgis.utils, "plugins", {}).get(info.real_key)
    if instance is None:
        return False, "wtyczka nie jest uruchomiona"

    actions = _instance_actions(instance) or _menu_actions(
        iface, info.repo_name
    )
    actions = [a for a in actions if a.isEnabled()]
    main = [a for a in actions if not _SKIP_ACTION.search(a.text())] or actions
    algs = plugin_algorithms(info.real_key)

    if len(main) == 1 and not algs:
        main[0].trigger()
        return True, "otwarto polecenie „{}”".format(_plain(main[0].text()))
    if len(algs) == 1 and not main:
        return _run_algorithm(algs[0])
    if main or algs:
        menu = QMenu()
        menu.setToolTipsVisible(True)
        if main and algs:
            menu.addSection("Polecenia wtyczki")
        for act in main:
            menu.addAction(act)
        chosen_alg = {}
        if algs:
            menu.addSection("Algorytmy Processing")
            for alg in algs:
                item = menu.addAction(
                    "{}  ({})".format(alg[1], alg[2]) if alg[2] else alg[1]
                )
                chosen_alg[item] = alg
        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return True, ""
        if chosen in chosen_alg:
            return _run_algorithm(chosen_alg[chosen])
        return True, "otwarto polecenie „{}”".format(_plain(chosen.text()))

    run = getattr(instance, "run", None)
    if callable(run):
        try:
            run()
            return True, "uruchomiono funkcję run()"
        except TypeError:
            pass
        except Exception as exc:
            return False, "błąd podczas uruchamiania: {}".format(exc)
    return False, (
        "nie znaleziono polecenia wtyczki w menu, na pasku narzędzi ani "
        "w panelu Processing - otwórz ją ręcznie"
    )


def _run_algorithm(alg):
    aid, name, _group = alg
    try:
        open_algorithm(aid)
    except Exception as exc:
        return False, "nie udało się otworzyć algorytmu „{}”: {}".format(
            name, exc
        )
    return True, "otwarto algorytm Processing „{}”".format(name)


def _fill_manager_filter(text, attempts=12):
    """Wpisuje nazwę wtyczki w pole wyszukiwania okna Menedżera wtyczek."""
    for widget in QApplication.topLevelWidgets():
        if not widget.isVisible():
            continue
        if widget.metaObject().className() != "QgsPluginManager":
            continue
        edit = widget.findChild(QLineEdit, "leFilter")
        if edit is None:
            for cand in widget.findChildren(QLineEdit):
                if cand.metaObject().className() == "QgsFilterLineEdit":
                    edit = cand
                    break
        if edit is not None:
            edit.setText(text)
            edit.setFocus()
            return
    if attempts > 0:
        QTimer.singleShot(
            250, lambda: _fill_manager_filter(text, attempts - 1)
        )


def open_plugin_manager(iface, search_text, tab=TAB_ALL):
    """Otwiera Menedżer wtyczek QGIS na wskazanej zakładce z wpisaną nazwą."""
    QTimer.singleShot(300, lambda: _fill_manager_filter(search_text))
    try:
        import pyplugin_installer

        pyplugin_installer.instance().showPluginManagerWhenReady(tab)
        return True
    except Exception:
        try:
            iface.actionManagePlugins().trigger()
            return True
        except Exception:
            return False
