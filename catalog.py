# -*- coding: utf-8 -*-
"""Ustawienia launchera: grupy (1-10), lista kafelków każdej grupy, nazwy,
kolejność, liczniki użycia, skanowanie repozytorium i ogłoszenia.

Wszystko jest zapisywane w ustawieniach QGIS (QgsSettings).

CatalogEntry:
  key         - identyfikator wtyczki (nazwa katalogu wtyczki, jak w adresie
                plugins.qgis.org/plugins/<key>/)
  label       - nazwa zapasowa, gdy nie ma oryginalnej nazwy z metadanych
  description - opis zapasowy
  custom      - podpis nadany przez użytkownika ("" = oryginalna nazwa)
"""

import json
import re
import unicodedata
from collections import namedtuple

from qgis.core import QgsSettings

CatalogEntry = namedtuple("CatalogEntry", "key label description custom")
CatalogEntry.__new__.__defaults__ = ("",)

OWN_KEY = "centrum_bdot_bdoo"
# obie odmiany launchera nie trafiają na listy wtyczek
OWN_KEYS = {
    "centrum_bdot_bdoo",
    "centrum_bdot_bdoo_ukryj",
    "centrum_bdot_bdoo_qgis4",
}
REPO_PAGE = "https://plugins.qgis.org/plugins/{key}/"
DEFAULT_TITLE = "Centrum wtyczek BDOT10k / BDOO"
AUTHOR = "Sławek Szymański"
MAX_GROUPS = 10
ANNOUNCE_TIMES = 3

# Hasła skanowania repozytorium (nazwa, opis, tagi, identyfikator)
SCAN_PATTERN = re.compile(r"bdoo|bdot", re.IGNORECASE)

_ROOT = "centrum_bdot_bdoo/"
_KEY_GROUPS = _ROOT + "groups"
_KEY_SEEN = _ROOT + "scan_seen"
_KEY_ANNOUNCE = _ROOT + "announce"
_KEY_TITLE = _ROOT + "title"
_KEY_SHOW_ICON = _ROOT + "show_toolbar_icon"
_KEY_HIDDEN_TB = _ROOT + "hidden_toolbars"
_KEY_ICONS_OFF = _ROOT + "toolbar_icons_off"
_KEY_SCALE = _ROOT + "tile_scale"
SCALE_MIN, SCALE_MAX = 70, 100

DEFAULT_PLUGINS = [
    CatalogEntry(
        "bdot10k_import_qgis4",
        "BDOT10k Import (QGIS 4.x)",
        "Import i scalanie powiatowych baz BDOT10k (GML) z automatycznym "
        "rozpoznawaniem starego i nowego schematu.",
    ),
    CatalogEntry(
        "bdot10k",
        "BDOT10k",
        "Pobieranie danych BDOT10k dla wybranych powiatów.",
    ),
    CatalogEntry(
        "BDOT10k_GML_SHP_Loader",
        "BDOT10k_GML_SHP",
        "Wczytywanie plików BDOT10k (SHP lub GML) do QGIS z symbolizacją "
        "zbliżoną do mapy topograficznej 1:10 000.",
    ),
    CatalogEntry(
        "pobieracz_danych_gugik",
        "Pobieracz danych GUGiK",
        "Pobieranie danych z zasobów GUGiK bezpośrednio z interfejsu QGIS.",
    ),
    CatalogEntry(
        "Walidator_plikow_gml",
        "Walidator plików GML",
        "Walidacja i kontrola plików GML baz BDOO, BDOT10k, PRNG, EGiB "
        "i innych.",
    ),
    CatalogEntry(
        "BDOO_import_qgis4",
        "Import BDOO (QGIS 4.x)",
        "Import i scalanie wojewódzkich baz BDOO (GML) do jednej bazy "
        "wynikowej.",
    ),
    CatalogEntry(
        "BDOO_GML_Loader",
        "BDOO_GML",
        "Wczytywanie plików BDOO (GML) do QGIS.",
    ),
]


def _json(name, default):
    raw = QgsSettings().value(name, "", type=str)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return default


def _store(name, value):
    QgsSettings().setValue(name, json.dumps(value, ensure_ascii=False))


def contains(entries, key):
    low = key.lower()
    return any(e.key.lower() == low for e in entries)


# ------------------------------------------------------------ grupy
def groups():
    """Numery istniejących grup (zawsze z grupą 1), rosnąco."""
    data = _json(_KEY_GROUPS, [1])
    nums = {1}
    if isinstance(data, list):
        for n in data:
            try:
                n = int(n)
            except (TypeError, ValueError):
                continue
            if 1 <= n <= MAX_GROUPS:
                nums.add(n)
    return sorted(nums)


def add_group(description=""):
    """Tworzy grupę o najniższym wolnym numerze; None gdy limit."""
    nums = groups()
    free = [n for n in range(2, MAX_GROUPS + 1) if n not in nums]
    if not free:
        return None
    n = free[0]
    _store(_KEY_GROUPS, sorted(nums + [n]))
    group = Group(n)
    group.save([])
    group.set_description(description)
    return n


def remove_group(n):
    if n == 1:
        return
    _store(_KEY_GROUPS, [g for g in groups() if g != n])
    QgsSettings().remove(Group(n).prefix.rstrip("/"))


class Group:
    """Ustawienia jednej grupy kafelków."""

    def __init__(self, number):
        self.number = number
        # grupa 1 korzysta z kluczy wersji 1.2 (zgodność wstecz)
        self.prefix = (
            _ROOT if number == 1 else "{}group{}/".format(_ROOT, number)
        )

    # --- opis
    def description(self):
        default = "BDOT10k / BDOO" if self.number == 1 else ""
        return QgsSettings().value(
            self.prefix + "description", default, type=str
        )

    def label(self):
        return self.description() or "Grupa {}".format(self.number)

    def set_description(self, text):
        QgsSettings().setValue(
            self.prefix + "description", (text or "").strip()
        )

    # --- lista kafelków
    def defaults(self):
        return list(DEFAULT_PLUGINS) if self.number == 1 else []

    def load(self):
        items = _json(self.prefix + "plugins", None)
        if not isinstance(items, list):
            return self.defaults()
        result, seen = [], set()
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or "").strip()
            if not key or key.lower() in seen:
                continue
            seen.add(key.lower())
            result.append(
                CatalogEntry(
                    key,
                    str(item.get("label") or key),
                    str(item.get("description") or ""),
                    str(item.get("custom") or ""),
                )
            )
        return result

    def save(self, entries):
        _store(self.prefix + "plugins", [e._asdict() for e in entries])

    def reset(self):
        QgsSettings().remove(self.prefix + "plugins")
        self.clear_usage()
        if self.number != 1:
            self.save([])
        return self.defaults()

    # --- użycie
    def usage(self):
        data = _json(self.prefix + "usage", {})
        return data if isinstance(data, dict) else {}

    def count_use(self, key):
        data = self.usage()
        data[key] = int(data.get(key, 0)) + 1
        _store(self.prefix + "usage", data)

    def clear_usage(self):
        QgsSettings().remove(self.prefix + "usage")

    def sorted_by_usage(self, entries):
        """Najczęściej używane na początku; remisy w kolejności ręcznej."""
        counts = self.usage()
        order = {e.key: n for n, e in enumerate(entries)}
        return sorted(
            entries,
            key=lambda e: (-int(counts.get(e.key, 0)), order[e.key]),
        )


# ------------------------------------------------------------ nazwa
def title():
    return QgsSettings().value(_KEY_TITLE, "", type=str) or DEFAULT_TITLE


def set_title(text):
    text = (text or "").strip()
    if not text or text == DEFAULT_TITLE:
        QgsSettings().remove(_KEY_TITLE)
    else:
        QgsSettings().setValue(_KEY_TITLE, text)


# ------------------------------------------------------------ autor
def _plain(text):
    text = str(text or "").replace("ł", "l").replace("Ł", "L")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.lower().split())


def is_author(name):
    return _plain(AUTHOR) in _plain(name)


# ------------------------------------------------------------ skanowanie
def matches(record):
    """Czy wtyczka dotyczy BDOO / BDOT10k (nazwa, id, opis, tagi)."""
    tags = record.get("tags") or ""
    if isinstance(tags, (list, tuple)):
        tags = " ".join(tags)
    text = " ".join(
        str(record.get(f) or "") for f in ("id", "key", "name", "description")
    )
    return bool(SCAN_PATTERN.search(text + " " + str(tags)))


def scan(records, all_keys, installed_keys):
    """Nowo wykryte wtyczki BDOO/BDOT10k spoza wszystkich grup:
    lista (klucz, nazwa, czy_zainstalowana). Każda zgłaszana raz;
    trafia też do kolejki ogłoszeń (3 wyświetlenia)."""
    seen = {str(k).lower() for k in _json(_KEY_SEEN, [])}
    have = {k.lower() for k in all_keys}
    installed = {k.lower() for k in installed_keys}
    fresh = []
    for key, rec in records.items():
        low = key.lower()
        if low in OWN_KEYS or low in seen or low in have or not matches(rec):
            continue
        seen.add(low)
        fresh.append((key, str(rec.get("name") or key), low in installed))
    if fresh:
        _store(_KEY_SEEN, sorted(seen))
        queue = _announce_queue()
        for key, name, inst in fresh:
            queue[key] = {"name": name, "installed": inst, "shown": 0}
        _store(_KEY_ANNOUNCE, queue)
    return fresh


def _announce_queue():
    data = _json(_KEY_ANNOUNCE, {})
    return data if isinstance(data, dict) else {}


def announce_next():
    """Ogłoszenia do pokazania przy tym otwarciu okna: lista
    (nazwa, czy_zainstalowana, które_wyświetlenie). Zwiększa licznik."""
    queue = _announce_queue()
    result = []
    for key, item in list(queue.items()):
        if not isinstance(item, dict):
            queue.pop(key)
            continue
        shown = int(item.get("shown", 0))
        if shown >= ANNOUNCE_TIMES:
            queue.pop(key)
            continue
        shown += 1
        item["shown"] = shown
        result.append(
            (str(item.get("name") or key), bool(item.get("installed")), shown)
        )
        if shown >= ANNOUNCE_TIMES:
            queue.pop(key)
    _store(_KEY_ANNOUNCE, queue)
    return result


# ------------------------------------------------------------ ikony pasków
def all_tile_keys():
    """Klucze wtyczek, które mają kafelek w którejkolwiek grupie."""
    keys = {}
    for n in groups():
        for e in Group(n).load():
            keys[e.key.lower()] = e.key
    return set(keys.values())


def shown_icons():
    """Wtyczki, dla których użytkownik zostawił ikonę na pasku narzędzi."""
    data = _json(_KEY_SHOW_ICON, [])
    return {str(k).lower() for k in data} if isinstance(data, list) else set()


def set_show_icon(key, show):
    keys = shown_icons()
    if show:
        keys.add(key.lower())
    else:
        keys.discard(key.lower())
    _store(_KEY_SHOW_ICON, sorted(keys))


def icons_off():
    """Czy włączone jest chowanie ikon (przycisk „Wyłącz ikony”).
    Domyślnie nie - ikony są widoczne."""
    return QgsSettings().value(_KEY_ICONS_OFF, False, type=bool)


def tile_scale():
    """Rozmiar kafelków w procentach (70-100), wspólny dla wszystkich okien."""
    value = QgsSettings().value(_KEY_SCALE, SCALE_MAX, type=int)
    return max(SCALE_MIN, min(SCALE_MAX, int(value)))


def set_tile_scale(value):
    value = max(SCALE_MIN, min(SCALE_MAX, int(value)))
    QgsSettings().setValue(_KEY_SCALE, value)
    return value


def set_icons_off(value):
    QgsSettings().setValue(_KEY_ICONS_OFF, bool(value))


def keys_to_hide():
    if not icons_off():
        return set()
    show = shown_icons()
    return {k for k in all_tile_keys() if k.lower() not in show}


def hidden_toolbars():
    """Paski narzędzi wtyczek schowane przez launcher (nazwy obiektów)."""
    data = _json(_KEY_HIDDEN_TB, [])
    return set(map(str, data)) if isinstance(data, list) else set()


def remember_toolbar(name, hidden):
    names = hidden_toolbars()
    if hidden:
        names.add(name)
    else:
        names.discard(name)
    _store(_KEY_HIDDEN_TB, sorted(names))
