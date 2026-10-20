# -*- coding: utf-8 -*-
"""Okno launchera (grupa 1-10) oraz okno „Inne wtyczki autora”.

Okno grupy: kafelki wybranych wtyczek, stały kafel autora w prawym górnym
rogu, Dodaj / Usuń wtyczkę, Duplikuj ikonę, Usuń grupę.
Okno autora (author_mode=True): mały launcher z wtyczkami autora pobranymi
z repozytorium QGIS, bez edycji listy.
"""

import os

from qgis.PyQt.QtCore import (
    QEvent,
    QMimeData,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
)
from qgis.PyQt.QtGui import (
    QColor,
    QCursor,
    QDesktopServices,
    QDrag,
    QFont,
    QIcon,
    QPainter,
    QPixmap,
)
from qgis.PyQt.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QWidgetAction,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from qgis.core import Qgis, QgsSettings

from . import catalog
from . import state as st
from .add_dialog import AddPluginDialog
from .i18n import EN_COLOR, HINT_EN, HINT_PL, esc, tip
from .icons import IconProvider, author_icon, fallback_icon
from .logger import ERROR, INFO, WARNING, Logger

HERE = os.path.dirname(__file__)
MIME = "application/x-centrum-bdot-bdoo-tile"

TILE_W, TILE_H, TILE_GAP = 170, 178, 12
AUTHOR_W, AUTHOR_H = int(TILE_W * 0.75), int(TILE_H * 0.75)
DEFAULT_SIZE = QSize(900, 720)
MSG_MS, ANNOUNCE_MS = 2000, 5000

RED, GREEN, ORANGE, GREY, BLUE = (
    "#c81e1e",
    "#288c3c",
    "#d27800",
    "#828282",
    "#1e64be",
)

STATUS = {
    st.OK: ("Zainstalowana • {vi}", "Installed • {vi}", GREEN),
    st.UPDATE: (
        "Dostępna aktualizacja\n{vi} → {va}",
        "Update available {vi} → {va}",
        ORANGE,
    ),
    st.DISABLED: ("Wyłączona", "Disabled", GREY),
    st.BROKEN: ("Błąd wtyczki", "Plugin error", RED),
    st.NOT_INSTALLED: ("Nie zainstalowana", "Not installed", RED),
    st.UNAVAILABLE: (
        "Niedostępna dla\ntej wersji QGIS",
        "Not available for this QGIS version",
        RED,
    ),
}

HINT = {
    st.OK: (
        "Kliknij, aby otworzyć wtyczkę.",
        "Click to open the plugin.",
    ),
    st.UPDATE: (
        "Kliknij, aby otworzyć wtyczkę. „Aktualizuj” otwiera Menedżer "
        "wtyczek QGIS, gdzie zatwierdzisz aktualizację.",
        "Click to open the plugin. “Aktualizuj” opens the QGIS Plugin "
        "Manager where you confirm the update.",
    ),
    st.DISABLED: (
        "Wtyczka jest wyłączona. Kliknij, aby ją włączyć i otworzyć.",
        "The plugin is disabled. Click to enable and open it.",
    ),
    st.BROKEN: (
        "Wtyczka nie uruchamia się. Kliknij, aby zobaczyć szczegóły.",
        "The plugin does not start. Click to see details.",
    ),
    st.NOT_INSTALLED: (
        "Kliknij, aby otworzyć Menedżer wtyczek QGIS z wpisaną nazwą. "
        "Instalację zatwierdzasz w Menedżerze.",
        "Click to open the QGIS Plugin Manager with the name filled in. "
        "You confirm the installation there.",
    ),
    st.UNAVAILABLE: (
        "Repozytorium QGIS nie udostępnia tej wtyczki dla tej wersji QGIS.",
        "The QGIS repository has no version for this QGIS release.",
    ),
}

FILTERS = [
    ("Wszystkie stany", None),
    ("Zainstalowane", {st.OK, st.UPDATE}),
    ("Do aktualizacji", {st.UPDATE}),
    ("Wyłączone lub z błędem", {st.DISABLED, st.BROKEN}),
    ("Niezainstalowane", {st.NOT_INSTALLED, st.UNAVAILABLE}),
]

QSS = """
QFrame#tile { background: #fafafa; border: 1px solid #bebebe;
              border-radius: 8px; }
QFrame#tile:hover { border: 1px solid #1e64be; }
QFrame#tile[selected="true"] { background: #cde1fa;
                               border: 2px solid #1e64be; }
QFrame#authorTile { background: #faf4e1; border: 2px solid #c8a03c;
                    border-radius: 8px; }
QFrame#authorTile:hover { border: 2px solid #1e64be; }
QLabel#tileName { color: #1e1e1e; font-weight: bold; }
QLabel#tileNameOff { color: #828282; font-weight: bold; }
QLabel#expBadge { background: #6e50aa; color: white; border-radius: 4px;
                  padding: 1px 4px; font-weight: bold; font-size: 8pt; }
QLabel#groupBadge { background: #3c78c8; color: white; border-radius: 4px;
                    padding: 1px 7px; font-weight: bold; }
QLabel#msgWarn { background: #ffe6e6; color: #c81e1e;
                 border: 1px solid #c81e1e; padding: 5px 8px; }
QLabel#msgInfo { background: #e8f0fb; color: #1e1e1e;
                 border: 1px solid #1e64be; padding: 5px 8px; }
"""


def _plural(n):
    if n == 1:
        return "1 wtyczka"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return "{} wtyczki".format(n)
    return "{} wtyczek".format(n)


def _pos(event):
    """Położenie kursora w zdarzeniu (Qt6: position() zamiast pos())."""
    return event.position().toPoint()


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)


class Tile(QFrame):
    clicked = pyqtSignal(str)
    menuRequested = pyqtSignal(str)

    def __init__(self, key, parent=None, draggable=True):
        super().__init__(parent)
        self.key = key
        self.draggable = draggable
        self._press = None
        self._dragged = False
        self.setObjectName("tile")
        self.scale = 1.0
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("selected", False)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 10, 8, 8)
        lay.setSpacing(4)
        self.icon = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.icon.setFixedHeight(72)
        self.name = QLabel(
            alignment=Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop,
            wordWrap=True,
        )
        self.name.setObjectName("tileName")
        self.status = QLabel(
            alignment=Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop,
            wordWrap=True,
        )
        lay.addWidget(self.icon)
        lay.addWidget(self.name)
        lay.addWidget(self.status)
        lay.addStretch(1)
        self.exp = QLabel("EXP", self)
        self.exp.setObjectName("expBadge")
        self.exp.adjustSize()
        self.exp.move(6, 6)
        self.exp.hide()
        self._base_pt = self.name.font().pointSizeF()
        self.apply_scale(1.0)

    def apply_scale(self, scale):
        """Rozmiar kafelka, ikony i czcionek (scale 0.7-1.0)."""
        self.scale = scale
        self.setFixedSize(int(TILE_W * scale), int(TILE_H * scale))
        self.icon.setFixedHeight(int(72 * scale))
        m = max(4, int(8 * scale))
        self.layout().setContentsMargins(m, int(10 * scale), m, m)
        if self._base_pt > 0:
            font = QFont(self.name.font())
            font.setPointSizeF(self._base_pt * scale)
            self.name.setFont(font)

    def set_selected(self, value):
        self.setProperty("selected", bool(value))
        _repolish(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._press = _pos(event)
            self._dragged = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self.draggable
            and self._press is not None
            and event.buttons() & Qt.MouseButton.LeftButton
            and (_pos(event) - self._press).manhattanLength()
            >= QApplication.startDragDistance()
        ):
            self._dragged = True
            self._press = None
            mime = QMimeData()
            mime.setData(MIME, self.key.encode("utf-8"))
            drag = QDrag(self)
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.setHotSpot(_pos(event))
            drag.exec(Qt.DropAction.MoveAction)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self._dragged
            and self.rect().contains(_pos(event))
        ):
            self.clicked.emit(self.key)
        self._press = None
        self._dragged = False
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        self.menuRequested.emit(self.key)


class AuthorTile(QFrame):
    """Stały kafel „Inne wtyczki autora” (75% rozmiaru, bez edycji)."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("authorTile")
        self.setFixedSize(AUTHOR_W, AUTHOR_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 8, 6, 6)
        lay.setSpacing(2)
        icon = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        icon.setPixmap(author_icon(48).pixmap(48, 48))
        name = QLabel(
            "Inne wtyczki\nautora",
            alignment=Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop,
        )
        name.setObjectName("tileName")
        self.count = QLabel(alignment=Qt.AlignmentFlag.AlignHCenter)
        self.count.setStyleSheet("color: #96701e; font-size: 8pt;")
        lay.addWidget(icon)
        lay.addWidget(name)
        lay.addWidget(self.count)
        lay.addStretch(1)
        self.set_count(None)

    def set_count(self, n):
        self.count.setText(_plural(n) if n is not None else "")
        self.setToolTip(
            tip(
                "Wtyczki autora {} zgodne z tą wersją QGIS. Lista pochodzi "
                "z repozytorium QGIS i aktualizuje się sama. Kafla nie można "
                "usunąć, przenieść ani przemianować.".format(catalog.AUTHOR),
                "Plugins by {} compatible with this QGIS version. The list "
                "comes from the QGIS repository and updates itself. This tile "
                "cannot be removed, moved or renamed.".format(catalog.AUTHOR),
                "Inne wtyczki autora",
                "More plugins by the author",
            )
        )

    def mouseReleaseEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and self.rect().contains(_pos(event))
        ):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class TileGrid(QWidget):
    """Obszar kafelków przyjmujący upuszczony kafelek."""

    dropped = pyqtSignal(str, object)
    MARGIN = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.corner = None  # kafel autora przypięty w prawym górnym rogu

    def place_corner(self):
        if self.corner is not None:
            self.corner.move(
                self.width() - self.MARGIN - self.corner.width(), self.MARGIN
            )
            self.corner.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.place_corner()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(MIME):
            key = bytes(event.mimeData().data(MIME)).decode("utf-8")
            event.acceptProposedAction()
            self.dropped.emit(key, _pos(event))


class LauncherDialog(QDialog):
    def __init__(self, iface, controller, group=1, author_mode=False):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.controller = controller
        self.author_mode = author_mode
        self.group = None if author_mode else catalog.Group(group)
        self.settings_prefix = (
            "centrum_bdot_bdoo/author/"
            if author_mode
            else self.group.prefix + "window/"
        )
        self.log = Logger(self)
        self.icons = IconProvider(self)
        self.icons.iconReady.connect(self._icon_ready)
        self.catalog = [] if author_mode else self.group.load()
        self.order_keys = [] if author_mode else self._usage_order()
        self.infos = {}
        self.tiles = {}
        self.selected = None
        self._columns = 0
        self._max_cols = 0
        self._last_sig = {}
        self._first_show = True
        self._busy = False
        self.scale = catalog.tile_scale() / 100.0

        self.setWindowIcon(QIcon(os.path.join(HERE, "icon.png")))
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(560 if author_mode else 760, 460)
        self.setStyleSheet(QSS)
        self._build()
        self.update_titles()
        self.log.message.connect(self._append_log)
        self._restore_settings()

    def _usage_order(self):
        return [e.key for e in self.group.sorted_by_usage(self.catalog)]

    # ------------------------------------------------------------ interfejs
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(8)

        if not self.author_mode:
            # podpowiedź tuż pod paskiem tytułu: polski, pod nim angielski
            self.hint_label = QLabel(
                '<span style="color:#828282">{}</span><br>'
                '<span style="color:{}">{}</span>'.format(
                    esc(HINT_PL), EN_COLOR, esc(HINT_EN)
                )
            )
            self.hint_label.setTextFormat(Qt.TextFormat.RichText)
            self.hint_label.setWordWrap(True)
            small = QFont(self.hint_label.font())
            small.setPointSizeF(small.pointSizeF() * 0.9)
            self.hint_label.setFont(small)
            root.addWidget(self.hint_label)

        head = QHBoxLayout()
        flag = QLabel()
        flag.setPixmap(
            QIcon(os.path.join(HERE, "flag_pl.svg")).pixmap(QSize(36, 22))
        )
        flag.setToolTip(
            tip("Wtyczka polskojęzyczna.", "Polish-language plugin.")
        )
        self.title_label = QLabel(wordWrap=True)
        font = QFont(self.title_label.font())
        font.setPointSizeF(font.pointSizeF() * 1.45)
        font.setBold(True)
        self.title_label.setFont(font)
        head.addWidget(flag)
        head.addSpacing(8)
        head.addWidget(self.title_label, 1)
        if not self.author_mode:
            self.title_label.setToolTip(
                tip(
                    "Prawy przycisk myszy: zmiana nazwy launchera lub "
                    "opisu grupy.",
                    "Right-click: rename the launcher or change the group "
                    "description.",
                )
            )
            self.title_label.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            self.title_label.customContextMenuRequested.connect(
                self._title_menu
            )
            self.badge = QLabel(str(self.group.number))
            self.badge.setObjectName("groupBadge")
            self.group_label = QLabel()
            self.group_label.setStyleSheet("color: #828282;")
            self.group_label.setToolTip(self.title_label.toolTip())
            self.group_label.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )
            self.group_label.customContextMenuRequested.connect(
                self._title_menu
            )
            head.addSpacing(8)
            head.addWidget(self.badge)
            head.addWidget(self.group_label)
        root.addLayout(head)
        self.subtitle = QLabel(wordWrap=True)
        self.subtitle.setStyleSheet("color: #828282;")
        root.addWidget(self.subtitle)

        bar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Szukaj wtyczki…")
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumWidth(140)
        self.search.setToolTip(
            tip(
                "Filtruje kafelki po nazwie lub opisie wtyczki.",
                "Filters tiles by plugin name or description.",
            )
        )
        self.search.textChanged.connect(self._apply_filter)
        self.filter = QComboBox()
        for label, _ in FILTERS:
            self.filter.addItem(label)
        self.filter.setToolTip(
            tip(
                "Pokazuje tylko wtyczki w wybranym stanie.",
                "Shows only plugins in the selected state.",
            )
        )
        self.filter.currentIndexChanged.connect(self._apply_filter)
        bar.addWidget(self.search, 2)
        bar.addWidget(self.filter, 1)
        if not self.author_mode:
            self.btn_add = QPushButton("Dodaj wtyczkę")
            self.btn_add.setToolTip(
                tip(
                    "Dodaje kafelek wtyczki zainstalowanej w QGIS "
                    "(także wyłączonej).",
                    "Adds a tile for a plugin installed in QGIS "
                    "(also a disabled one).",
                )
            )
            self.btn_add.clicked.connect(self._add_plugins)
            self.btn_remove = QPushButton("Usuń wtyczkę")
            self.btn_remove.setToolTip(
                tip(
                    "Usuwa zaznaczony kafelek z tej grupy. Sama wtyczka "
                    "zostaje zainstalowana w QGIS.",
                    "Removes the selected tile from this group. The plugin "
                    "stays installed in QGIS.",
                )
            )
            self.btn_remove.clicked.connect(self._remove_selected)
            self.btn_dup = QPushButton("Duplikuj ikonę")
            self.btn_dup.setToolTip(
                tip(
                    "Tworzy kolejną grupę z własną ikoną na pasku narzędzi "
                    "(numer 2-10) i własnym zestawem kafelków.",
                    "Creates another group with its own toolbar icon "
                    "(number 2-10) and its own set of tiles.",
                )
            )
            self.btn_dup.clicked.connect(self._duplicate)
            self.dup_count = QLabel()
            self.dup_count.setStyleSheet("color: #828282;")
            bar.addWidget(self.btn_add)
            bar.addWidget(self.btn_remove)
            bar.addWidget(self.btn_dup)
            bar.addWidget(self.dup_count)
            if self.group.number != 1:
                self.btn_delgroup = QPushButton("Usuń grupę")
                self.btn_delgroup.setToolTip(
                    tip(
                        "Usuwa tę grupę i jej ikonę z paska narzędzi. "
                        "Wtyczki zostają zainstalowane w QGIS.",
                        "Deletes this group and its toolbar icon. Plugins "
                        "stay installed in QGIS.",
                    )
                )
                self.btn_delgroup.clicked.connect(self._delete_group)
                bar.addWidget(self.btn_delgroup)
        root.addLayout(bar)

        self.announce = QLabel(wordWrap=True)
        self.announce.setObjectName("msgWarn")
        self.announce.hide()
        self.announce_timer = QTimer(self)
        self.announce_timer.setSingleShot(True)
        self.announce_timer.timeout.connect(self.announce.hide)
        root.addWidget(self.announce)
        self.msg = QLabel(wordWrap=True)
        self.msg.hide()
        self.msg_timer = QTimer(self)
        self.msg_timer.setSingleShot(True)
        self.msg_timer.timeout.connect(self.msg.hide)
        root.addWidget(self.msg)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.grid_host = TileGrid()
        self.grid_host.dropped.connect(self._tile_dropped)
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(12, 12, 12, 12)
        self.grid.setSpacing(TILE_GAP)
        self.grid.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        self.scroll.setWidget(self.grid_host)
        self.scroll.viewport().installEventFilter(self)
        root.addWidget(self.scroll, 3)

        self.author_tile = None
        self.empty_label = QLabel(self.grid_host)
        self.empty_label.setWordWrap(True)
        self.empty_label.setStyleSheet("color: #828282;")
        self.empty_label.hide()
        if not self.author_mode:
            self.author_tile = AuthorTile(self.grid_host)
            self.grid_host.corner = self.author_tile
            self.author_tile.clicked.connect(self.controller.open_author)
            self.empty_label.setText(
                "Brak kafelków. Kliknij „Dodaj wtyczkę”, aby dodać "
                "zainstalowane wtyczki."
            )
        else:
            self.empty_label.setText(
                "Brak wtyczek autora. Kliknij „Odśwież” (potrzebny jest "
                "internet)."
            )
        self._sync_tiles()

        self.log_toggle = QToolButton()
        self.log_toggle.setText("Log")
        self.log_toggle.setCheckable(True)
        self.log_toggle.setChecked(not self.author_mode)
        self.log_toggle.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.log_toggle.setArrowType(Qt.ArrowType.DownArrow)
        self.log_toggle.setAutoRaise(True)
        self.log_toggle.setToolTip(
            tip(
                "Pokazuje lub ukrywa log. Pełny log jest zapisywany w pliku "
                "centrum_bdot_bdoo.log w katalogu profilu QGIS.",
                "Shows or hides the log. The full log is saved to "
                "centrum_bdot_bdoo.log in the QGIS profile folder.",
            )
        )
        self.log_toggle.toggled.connect(self._toggle_log)
        # wiersz logu: Log | Skaluj ikony (środek) | Wyłącz ikony (prawo)
        log_row = QGridLayout()
        log_row.setColumnStretch(0, 1)
        log_row.setColumnStretch(2, 1)
        log_row.addWidget(self.log_toggle, 0, 0, Qt.AlignmentFlag.AlignLeft)
        self.btn_icons = None
        self.btn_scale = None
        if not self.author_mode:
            self.btn_scale = QPushButton()
            self.btn_scale.setToolTip(
                tip(
                    "Zmienia rozmiar kafelków z wtyczkami od 70% do 100% "
                    "(suwak albo wpisana wartość). Rozmiar jest wspólny dla "
                    "wszystkich grup i okna „Inne wtyczki autora” "
                    "i zostaje zapamiętany. Kafel autora się nie zmienia.",
                    "Changes the size of plugin tiles from 70% to 100% "
                    "(slider or typed value). The size is shared by all "
                    "groups and the author window and is remembered. "
                    "The author tile keeps its size.",
                )
            )
            self.btn_scale.clicked.connect(self._scale_popup)
            self.btn_scale.setText(self._scale_text())
            log_row.addWidget(
                self.btn_scale, 0, 1, Qt.AlignmentFlag.AlignCenter
            )
            self.btn_icons = QPushButton()
            self.btn_icons.clicked.connect(
                lambda: self.controller.set_icons_off(not catalog.icons_off())
            )
            log_row.addWidget(
                self.btn_icons, 0, 2, Qt.AlignmentFlag.AlignRight
            )
            self.update_icons_button()
        root.addLayout(log_row)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(500)
        self.log_view.setFixedHeight(96)
        self.log_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        root.addWidget(self.log_view)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        root.addWidget(line)

        buttons = QHBoxLayout()
        self.btn_close = QPushButton("Zamknij")
        self.btn_close.setToolTip(
            tip(
                "Zamyka okno. Otwarte wtyczki działają dalej.",
                "Closes the window. Opened plugins keep running.",
            )
        )
        self.btn_close.clicked.connect(self.close)
        self.btn_refresh = QPushButton("Odśwież")
        self.btn_refresh.setToolTip(
            tip(
                "Ponownie pobiera z repozytorium QGIS informacje o wersjach "
                "i odświeża kafelki.",
                "Downloads version information from the QGIS repository "
                "again and refreshes the tiles.",
            )
        )
        self.btn_refresh.clicked.connect(
            lambda: self.refresh(fetch=True, reload=True)
        )
        self.btn_update = QPushButton("Aktualizuj")
        self.btn_update.setToolTip(
            tip(
                "Otwiera Menedżer wtyczek QGIS na zakładce aktualizacji "
                "z wpisaną nazwą zaznaczonej wtyczki.",
                "Opens the QGIS Plugin Manager on the upgrade tab with the "
                "selected plugin's name filled in.",
            )
        )
        self.btn_update.clicked.connect(self._update_selected)
        self.btn_open = QPushButton("Otwórz")
        self.btn_open.setDefault(True)
        self.btn_open.setToolTip(
            tip(
                "Otwiera zaznaczoną wtyczkę. Dla niezainstalowanej - "
                "Menedżer wtyczek QGIS.",
                "Opens the selected plugin. For a plugin that is not "
                "installed - the QGIS Plugin Manager.",
            )
        )
        self.btn_open.clicked.connect(
            lambda: self.selected and self._activate(self.selected)
        )
        buttons.addWidget(self.btn_close)
        buttons.addStretch(1)
        for btn in (self.btn_refresh, self.btn_update, self.btn_open):
            buttons.addWidget(btn)
        root.addLayout(buttons)
        self._update_buttons()

    def update_titles(self):
        """Tytuł w oknie, na pasku tytułu i licznik grup."""
        if self.author_mode:
            self.title_label.setText("Inne wtyczki autora")
            self.setWindowTitle(
                "Inne wtyczki autora / More plugins by the author"
            )
            return
        name = catalog.title()
        self.title_label.setText(name)
        self.group_label.setText(
            "Grupa {} • {}".format(self.group.number, self.group.label())
            if self.group.description()
            else "Grupa {}".format(self.group.number)
        )
        self.setWindowTitle("{} – {}".format(name, self.group.label()))
        count = len(catalog.groups())
        self.dup_count.setText("({} / {})".format(count, catalog.MAX_GROUPS))
        self.btn_dup.setEnabled(count < catalog.MAX_GROUPS)

    # ------------------------------------------------------------ ustawienia
    def _restore_settings(self):
        s = QgsSettings()
        p = self.settings_prefix
        geom = s.value(p + "geometry")
        if geom is None or not self.restoreGeometry(geom):
            self._default_geometry()
        self.search.setText(s.value(p + "search", "", type=str))
        idx = s.value(p + "filter", 0, type=int)
        self.filter.setCurrentIndex(idx if 0 <= idx < len(FILTERS) else 0)
        self.log_toggle.setChecked(
            s.value(p + "log_visible", not self.author_mode, type=bool)
        )

    def _save_settings(self):
        s = QgsSettings()
        p = self.settings_prefix
        s.setValue(p + "geometry", self.saveGeometry())
        s.setValue(p + "search", self.search.text())
        s.setValue(p + "filter", self.filter.currentIndex())
        s.setValue(p + "log_visible", self.log_toggle.isChecked())

    def _default_geometry(self):
        size = QSize(DEFAULT_SIZE)
        screen = QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            size = size.boundedTo(
                QSize(int(area.width() * 0.9), int(area.height() * 0.9))
            )
            self.resize(size)
            self.move(
                area.center().x() - size.width() // 2,
                area.center().y() - size.height() // 2,
            )
        else:
            self.resize(size)

    # ------------------------------------------------------------ zdarzenia
    def showEvent(self, event):
        super().showEvent(event)
        if event.spontaneous():  # przywrócenie z paska zadań
            return
        if not self.author_mode:
            self.catalog = self.group.load()
            self.order_keys = self._usage_order()
            self._sync_tiles()
            self._relayout(force=True)
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(
                0, lambda: self.refresh(fetch=True, reload=False, first=True)
            )
        elif not self.author_mode:
            QTimer.singleShot(0, self._announce)

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if (
            event.type() == QEvent.Type.ActivationChange
            and self.isActiveWindow()
            and not self._first_show
            and not self._busy
        ):
            QTimer.singleShot(0, lambda: self.refresh(fetch=False))

    def eventFilter(self, obj, event):
        if (
            obj is self.scroll.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self._relayout()
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------ komunikaty
    def notify(self, text, level=INFO):
        """Krótki komunikat w oknie (znika po 2 s) i wpis do logu."""
        self.msg.setObjectName(
            "msgWarn" if level in (WARNING, ERROR) else "msgInfo"
        )
        _repolish(self.msg)
        self.msg.setText(("⚠  " if level != INFO else "") + text)
        self.msg.show()
        self.msg_timer.start(MSG_MS)
        self.log.write(text, level)

    def _announce(self):
        """Ogłoszenie nowych wtyczek BDOO/BDOT10k: 5 s, 3 kolejne otwarcia."""
        items = catalog.announce_next()
        if not items:
            return
        parts = []
        for name, installed, shown in items:
            hint = (
                "zainstalowana - dodaj kafelek"
                if installed
                else "zainstaluj w Menedżerze wtyczek, potem dodaj kafelek"
            )
            parts.append(
                "{} ({}) [{}/{}]".format(
                    name, hint, shown, catalog.ANNOUNCE_TIMES
                )
            )
        self.announce.setText(
            "⚠  Nowe wtyczki BDOO / BDOT10k w repozytorium: "
            + "; ".join(parts)
        )
        self.announce.show()
        self.announce_timer.start(ANNOUNCE_MS)

    def _append_log(self, line, level):
        color = {WARNING: ORANGE, ERROR: RED}.get(level, "#1e1e1e")
        self.log_view.appendHtml(
            '<span style="color:{}">{}</span>'.format(color, esc(line))
        )

    def _toggle_log(self, visible):
        self.log_view.setVisible(visible)
        self.log_toggle.setArrowType(
            Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow
        )

    # ------------------------------------------------------------ odświeżanie
    def refresh(self, fetch=False, reload=False, first=False):
        if self._busy:
            return
        self._busy = True
        try:
            if fetch:
                ok, err = st.fetch_repository(reload)
                if not ok:
                    self.log.warning(
                        "Nie udało się pobrać listy wtyczek z repozytorium "
                        "QGIS: {}".format(err or "nieznany błąd")
                    )
                if reload:
                    self.icons.forget_cache()
            authors = st.author_entries()
            if self.author_mode:
                self.catalog = authors
                self.order_keys = [e.key for e in authors]
                self._sync_tiles()
            infos, fetched = st.collect(self.catalog)
            records, _ = st.repository_records()
            installed = (
                []
                if self.author_mode
                else [r["key"] for r in st.installed_plugins()]
            )
        finally:
            self._busy = False

        if self.author_tile is not None:
            self.author_tile.set_count(len(authors))
        self.infos = {i.key: i for i in infos}
        for info in infos:
            self._paint_tile(info)
        self._apply_filter()
        version = Qgis.QGIS_VERSION.split("-")[0]
        if self.author_mode:
            self.subtitle.setText(
                "{}  •  wtyczki zgodne z QGIS {}  •  lista z repozytorium "
                "QGIS, aktualizuje się sama".format(catalog.AUTHOR, version)
            )
        else:
            self.subtitle.setText(
                "QGIS {}  •  kliknij kafelek, aby otworzyć wtyczkę".format(
                    version
                )
            )
        if fetch and not fetched:
            self.notify(
                "Brak połączenia z repozytorium QGIS - informacje o "
                "aktualizacjach i część ikon mogą być niedostępne. "
                "Spróbuj „Odśwież”.",
                WARNING,
            )
        self._log_changes(infos, summary=fetch or first)
        fresh = []
        if fetched and not self.author_mode:
            fresh = self._scan(records, installed)
        if not self.author_mode and (first or fresh):
            self._announce()
        # ikony wtyczek z kafelkami znikają z pasków narzędzi QGIS
        self.controller.sync_icons()
        self._update_buttons()

    def _scan(self, records, installed):
        all_keys = set()
        for n in catalog.groups():
            all_keys.update(e.key for e in catalog.Group(n).load())
        fresh = catalog.scan(records, all_keys, installed)
        for key, name, is_installed in fresh:
            if is_installed:
                self.log.warning(
                    "Nowa wtyczka BDOO / BDOT10k: {} ({}) jest zainstalowana "
                    "- dodasz jej kafelek przyciskiem „Dodaj wtyczkę”.".format(
                        name, key
                    )
                )
            else:
                self.log.warning(
                    "W repozytorium jest nowa wtyczka BDOO / BDOT10k: {} "
                    "({}). Zainstaluj ją w Menedżerze wtyczek, a potem "
                    "dodaj kafelek.".format(name, key)
                )
        return fresh

    def _log_changes(self, infos, summary):
        if summary:
            count = {}
            for i in infos:
                count[i.state] = count.get(i.state, 0) + 1
            self.log.info(
                "{}: sprawdzono {} wtyczek: {} zainstalowane, {} do "
                "aktualizacji, {} wyłączone, {} z błędem, {} brak.".format(
                    (
                        "Okno autora"
                        if self.author_mode
                        else "Grupa {}".format(self.group.number)
                    ),
                    len(infos),
                    count.get(st.OK, 0) + count.get(st.UPDATE, 0),
                    count.get(st.UPDATE, 0),
                    count.get(st.DISABLED, 0),
                    count.get(st.BROKEN, 0),
                    count.get(st.NOT_INSTALLED, 0)
                    + count.get(st.UNAVAILABLE, 0),
                )
            )
        for i in infos:
            sig = i.signature()
            if not summary and self._last_sig.get(i.key) == sig:
                continue
            self._last_sig[i.key] = sig
            if i.state == st.UPDATE:
                self.log.warning(
                    "{}: dostępna aktualizacja {} → {}.".format(
                        i.label, i.version_installed, i.version_available
                    )
                )
            elif i.state == st.NOT_INSTALLED:
                self.log.error(
                    "{}: brak wtyczki - zainstaluj ją z repozytorium "
                    "QGIS.".format(i.label)
                )
            elif i.state == st.UNAVAILABLE:
                self.log.error(
                    "{}: niedostępna dla tej wersji QGIS.".format(i.label)
                )
            elif i.state == st.BROKEN:
                self.log.error(
                    "{}: błąd wtyczki - {}.".format(i.label, i.error)
                )
            elif i.state == st.DISABLED and not summary:
                self.log.info("{}: wtyczka jest wyłączona.".format(i.label))
            elif not summary:
                self.log.info(
                    "{}: zainstalowana {}.".format(
                        i.label, i.version_installed
                    )
                )

    def _paint_tile(self, info):
        tile = self.tiles.get(info.key)
        if tile is None:
            return
        off = info.state in (
            st.DISABLED,
            st.NOT_INSTALLED,
            st.UNAVAILABLE,
            st.BROKEN,
        )
        icon = self.icons.icon(info) or fallback_icon(info.key, info.label)
        mode = QIcon.Mode.Disabled if off else QIcon.Mode.Normal
        size = int(64 * self.scale)
        tile.icon.setPixmap(
            self._compose(
                icon.pixmap(QSize(size, size), mode),
                info.state == st.UPDATE,
                self.scale,
            )
        )
        name = info.label
        if len(name) > 40:  # pełna nazwa jest w dymku
            name = name[:38].rstrip() + "…"
        tile.name.setText(name.replace("_", "_\u200b"))
        tile.name.setObjectName(
            "tileNameOff"
            if info.state in (st.NOT_INSTALLED, st.UNAVAILABLE)
            else "tileName"
        )
        _repolish(tile.name)
        pl, _en, color = STATUS[info.state]
        status = pl.format(
            vi=info.version_installed or "?", va=info.version_available or "?"
        )
        if info.has_experimental:
            status += "\njest wersja eksperym."
        tile.status.setText(status)
        tile.status.setStyleSheet(
            "color: {}; font-size: {:.1f}pt;".format(color, 8 * self.scale)
        )
        tile.exp.setVisible(info.has_experimental)
        tile.setToolTip(self._tooltip(info))

    @staticmethod
    def _compose(pix, update_badge, scale=1.0):
        def s(v):
            return int(v * scale)

        canvas = QPixmap(s(88), s(72))
        canvas.fill(Qt.GlobalColor.transparent)
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.drawPixmap(s(12), s(4), pix)
        if update_badge:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ORANGE))
            p.drawEllipse(s(64), 0, s(22), s(22))
            p.setPen(QColor("white"))
            font = QFont()
            font.setBold(True)
            font.setPixelSize(max(9, s(15)))
            p.setFont(font)
            p.drawText(
                s(64), 0, s(22), s(22), Qt.AlignmentFlag.AlignCenter, "↑"
            )
        p.end()
        return canvas

    def _tooltip(self, info):
        vi = info.version_installed or "?"
        va = info.version_available or "?"
        pl, en, _c = STATUS[info.state]
        state_pl = pl.replace("\n", " ").format(vi=vi, va=va)
        state_en = en.format(vi=vi, va=va)
        lines_pl = [esc(info.description), "Stan: {}.".format(esc(state_pl))]
        lines_en = ["Status: {}.".format(esc(state_en))]
        if info.has_experimental:
            lines_pl.append(
                "W repozytorium jest wersja eksperymentalna {}. W Menedżerze "
                "wtyczek włącz: Ustawienia → „Pokaż także wtyczki "
                "eksperymentalne”.".format(esc(info.version_experimental))
            )
            lines_en.append(
                "An experimental version {} is available. In the Plugin "
                "Manager enable: Settings → “Show also experimental "
                "plugins”.".format(esc(info.version_experimental))
            )
        if info.state == st.BROKEN and info.error:
            lines_pl.append(
                '<span style="color:{}">{}</span>'.format(RED, esc(info.error))
            )
        if info.algorithms:
            n = len(info.algorithms)
            names = ", ".join(esc(a[1]) for a in info.algorithms[:3])
            if n > 3:
                names += ", …"
            lines_pl.append(
                "Algorytmy Processing ({}): {}. Kliknięcie otwiera okno "
                "algorytmu{}.".format(
                    n, names, "" if n == 1 else " (lista do wyboru)"
                )
            )
            lines_en.append(
                "Processing algorithms ({}): click opens the algorithm "
                "window{}.".format(n, "" if n == 1 else " (choose from list)")
            )
        hint_pl, hint_en = HINT[info.state]
        lines_pl.append("<i>{}</i>".format(hint_pl))
        lines_en.append("<i>{}</i>".format(hint_en))
        if not self.author_mode:
            lines_pl.append(
                "Przeciągnij, aby zmienić kolejność. Prawy przycisk: zmiana "
                "nazwy, usunięcie."
            )
            lines_en.append("Drag to reorder. Right-click: rename, remove.")
            if not catalog.icons_off():
                lines_pl.append("Ikona na pasku narzędzi QGIS: widoczna.")
                lines_en.append("QGIS toolbar icon: shown.")
            elif info.key.lower() in catalog.shown_icons():
                lines_pl.append(
                    "Ikona na pasku narzędzi QGIS: widoczna (wyjątek)."
                )
                lines_en.append("QGIS toolbar icon: shown (exception).")
            else:
                lines_pl.append(
                    "Ikona na pasku narzędzi QGIS: ukryta (prawy przycisk "
                    "→ „Pokaż ikonę na pasku narzędzi”)."
                )
                lines_en.append(
                    "QGIS toolbar icon: hidden (right-click → “Pokaż ikonę "
                    "na pasku narzędzi” to show it)."
                )
        title_en = info.original if info.custom else ""
        return tip(
            "<br>".join(lines_pl),
            "<br>".join(lines_en),
            esc(info.label),
            esc(title_en),
        )

    def _icon_ready(self, key):
        info = self.infos.get(key)
        if info is not None:
            self._paint_tile(info)

    # ------------------------------------------------------------ układ siatki
    def _visible_tiles(self):
        return [
            self.tiles[k]
            for k in self.order_keys
            if k in self.tiles and not self.tiles[k].isHidden()
        ]

    def _relayout(self, force=False):
        width = self.scroll.viewport().width() - 24
        tile_w = int(TILE_W * self.scale)
        cols = max(1, (width + TILE_GAP) // (tile_w + TILE_GAP))
        if cols == self._columns and not force:
            return
        self._columns = cols
        while self.grid.count():
            self.grid.takeAt(0)
        for c in range(max(self._max_cols, cols)):
            self.grid.setColumnMinimumWidth(c, tile_w if c < cols else 0)
        self._max_cols = max(self._max_cols, cols)
        tiles = self._visible_tiles()
        cells = []
        row = 0
        if self.author_tile is not None:
            # kafel autora zawsze w prawym górnym rogu obszaru kafelków;
            # w pierwszym wierszu zostaje dla niego wolne miejsce
            # ile kafelków mieści się obok kafla autora (ma stały rozmiar)
            first = (width - AUTHOR_W) // (tile_w + TILE_GAP)
            cells = [(0, c) for c in range(max(0, min(cols - 1, first)))]
            row = 1
            self.grid.setRowMinimumHeight(0, AUTHOR_H)
            self.author_tile.show()
            self.grid_host.place_corner()
        while len(cells) < len(tiles):
            cells.extend((row, c) for c in range(cols))
            row += 1
        for tile, (r, c) in zip(tiles, cells):
            self.grid.addWidget(tile, r, c)
        if not tiles:
            span = max(1, cols - 1) if self.author_tile is not None else cols
            self.grid.addWidget(self.empty_label, 0, 0, 1, span)
            self.empty_label.show()
        else:
            self.empty_label.hide()

    def _apply_filter(self, *_):
        text = self.search.text().strip().lower()
        allowed = FILTERS[self.filter.currentIndex()][1]
        for entry in self.catalog:
            info = self.infos.get(entry.key)
            tile = self.tiles.get(entry.key)
            if tile is None:
                continue
            show = True
            if (
                info is not None
                and allowed is not None
                and info.state not in allowed
            ):
                show = False
            label = info.label if info else entry.label
            if (
                text
                and text not in label.lower()
                and (info is None or text not in info.description.lower())
            ):
                show = False
            tile.setHidden(not show)
        self._relayout(force=True)

    # ------------------------------------------------------------ akcje
    def _select(self, key):
        self.selected = key
        for k, tile in self.tiles.items():
            tile.set_selected(k == key)
        self._update_buttons()

    def _update_buttons(self):
        info = self.infos.get(self.selected)
        self.btn_open.setEnabled(
            info is not None and info.state != st.UNAVAILABLE
        )
        self.btn_update.setEnabled(
            info is not None and info.state == st.UPDATE
        )
        if not self.author_mode:
            self.btn_remove.setEnabled(info is not None)
        if info is not None and info.state == st.NOT_INSTALLED:
            self.btn_open.setText("Zainstaluj…")
        elif info is not None and info.state == st.DISABLED:
            self.btn_open.setText("Włącz i otwórz")
        else:
            self.btn_open.setText("Otwórz")

    def _tile_clicked(self, key):
        self._select(key)
        self._activate(key)

    def _activate(self, key):
        info = self.infos.get(key)
        if info is None:
            return
        if info.state in (st.OK, st.UPDATE):
            self._open(info)
        elif info.state == st.DISABLED:
            answer = QMessageBox.question(
                self,
                catalog.title(),
                "Wtyczka „{}” jest zainstalowana, ale wyłączona.\n\n"
                "Włączyć ją teraz?".format(info.label),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            ok, err = st.enable_and_start(info.real_key)
            if not ok:
                self.notify(
                    "{}: nie udało się włączyć wtyczki - {}.".format(
                        info.label, err
                    ),
                    ERROR,
                )
                self.refresh()
                return
            self.log.info("{}: wtyczka włączona.".format(info.label))
            self.refresh()
            info = self.infos.get(key)
            if info is not None and info.state in (st.OK, st.UPDATE):
                self._open(info)
        elif info.state == st.NOT_INSTALLED:
            box = QMessageBox(
                QMessageBox.Icon.Warning,
                catalog.title(),
                "Wtyczka „{}” nie jest zainstalowana.\n\n"
                "Zainstaluj wtyczkę z repozytorium QGIS.".format(info.label),
                parent=self,
            )
            go = box.addButton(
                "Otwórz Menedżer wtyczek", QMessageBox.ButtonRole.AcceptRole
            )
            box.addButton("Anuluj", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is go:
                self._manager(info, st.TAB_ALL)
        elif info.state == st.BROKEN:
            box = QMessageBox(
                QMessageBox.Icon.Critical,
                catalog.title(),
                "Wtyczka „{}” nie uruchamia się.\n\n{}\n\n"
                "Szczegóły znajdziesz w panelu „Komunikaty” QGIS "
                "(zakładka „Błędy Pythona”).".format(info.label, info.error),
                parent=self,
            )
            go = box.addButton(
                "Otwórz Menedżer wtyczek", QMessageBox.ButtonRole.AcceptRole
            )
            box.addButton("Zamknij", QMessageBox.ButtonRole.RejectRole)
            box.exec()
            if box.clickedButton() is go:
                self._manager(info, st.TAB_INSTALLED)
        else:
            self.notify(
                "{}: niedostępna dla tej wersji QGIS.".format(info.label),
                WARNING,
            )

    def _open(self, info):
        ok, msg = st.open_plugin(self.iface, info, self.log)
        if ok:
            if msg:
                if not self.author_mode:
                    self.group.count_use(info.key)
                self.log.info("{}: {}.".format(info.label, msg))
        else:
            self.notify("{}: {}.".format(info.label, msg), ERROR)

    def _update_selected(self):
        info = self.infos.get(self.selected)
        if info is not None and info.state == st.UPDATE:
            self._manager(info, st.TAB_UPGRADEABLE)

    def _manager(self, info, tab):
        self.log.info("{}: otwieram Menedżer wtyczek QGIS.".format(info.label))
        if not st.open_plugin_manager(self.iface, info.repo_name, tab):
            self.notify(
                "Nie udało się otworzyć Menedżera wtyczek. Otwórz go z menu "
                "Wtyczki → Zarządzaj wtyczkami.",
                ERROR,
            )
        QTimer.singleShot(0, lambda: self.refresh())

    def _tile_menu(self, key):
        info = self.infos.get(key)
        if info is None:
            return
        self._select(key)
        menu = QMenu(self)
        act_open = menu.addAction(self.btn_open.text())
        act_open.setEnabled(info.state != st.UNAVAILABLE)
        act_rename = act_orig = act_remove = None
        if not self.author_mode:
            menu.addSeparator()
            act_rename = menu.addAction("Zmień nazwę kafelka…")
            act_orig = menu.addAction(
                "Przywróć oryginalną nazwę („{}”)".format(info.original)
            )
            act_orig.setEnabled(bool(info.custom))
            act_remove = menu.addAction("Usuń kafelek…")
            act_icon = menu.addAction("Pokaż ikonę na pasku narzędzi")
            act_icon.setCheckable(True)
            act_icon.setChecked(info.key.lower() in catalog.shown_icons())
            # wyjątek ma sens tylko, gdy ikony są wyłączone
            act_icon.setEnabled(catalog.icons_off())
            act_icon.setToolTip(
                tip(
                    "Po „Wyłącz ikony” wtyczki z kafelkiem nie mają ikony "
                    "na pasku narzędzi QGIS. Zaznacz, aby zostawić ikonę tej "
                    "wtyczki. Gdy ikony są włączone - nieaktywne.",
                    "After “Wyłącz ikony” plugins with a tile have no icon "
                    "on the QGIS toolbar. Check to keep this plugin's icon. "
                    "Inactive while icons are on.",
                )
            )
            menu.setToolTipsVisible(True)
        else:
            act_icon = None
        menu.addSeparator()
        act_tb = None
        if info.algorithms:
            act_tb = menu.addAction("Pokaż w panelu Processing")
        act_mgr = menu.addAction("Pokaż w Menedżerze wtyczek")
        act_web = menu.addAction("Strona wtyczki w repozytorium QGIS")
        chosen = menu.exec(QCursor.pos())
        if chosen is None:
            return
        if act_tb is not None and chosen is act_tb:
            # panel filtruje po nazwie / identyfikatorze algorytmu:
            # jeden algorytm -> jego nazwa, kilka -> id dostawcy (przedrostek)
            if len(info.algorithms) == 1:
                text = info.algorithms[0][1]
            else:
                text = info.algorithms[0][0].split(":")[0]
            if not st.show_in_toolbox(self.iface, text):
                self.notify("Panel Processing jest niedostępny.", WARNING)
            return
        if chosen is act_icon:
            catalog.set_show_icon(info.key, act_icon.isChecked())
            self.log.info(
                "{}: ikona na pasku narzędzi {}.".format(
                    info.label,
                    "widoczna" if act_icon.isChecked() else "ukryta",
                )
            )
            self.controller.sync_icons()
            self._paint_tile(info)
        elif chosen is act_rename:
            self._rename_tile(info)
        elif chosen is act_orig:
            self._set_custom(info, "")
        elif chosen is act_remove:
            self._remove_selected()
        elif chosen is act_open:
            self._activate(key)
        elif chosen is act_mgr:
            tab = (
                st.TAB_ALL
                if info.state in (st.NOT_INSTALLED, st.UNAVAILABLE)
                else st.TAB_INSTALLED
            )
            self._manager(info, tab)
        elif chosen is act_web:
            QDesktopServices.openUrl(QUrl(info.homepage))

    # ------------------------------------------------------------ lista
    def _sync_tiles(self):
        keys = {e.key for e in self.catalog}
        for key in list(self.tiles):
            if key not in keys:
                tile = self.tiles.pop(key)
                self.grid.removeWidget(tile)
                tile.hide()
                tile.deleteLater()
                self.infos.pop(key, None)
        for entry in self.catalog:
            if entry.key not in self.tiles:
                tile = Tile(
                    entry.key, self.grid_host, draggable=not self.author_mode
                )
                tile.apply_scale(self.scale)
                tile.clicked.connect(self._tile_clicked)
                tile.menuRequested.connect(self._tile_menu)
                self.tiles[entry.key] = tile
        self.order_keys = [k for k in self.order_keys if k in keys]
        for entry in self.catalog:
            if entry.key not in self.order_keys:
                self.order_keys.append(entry.key)
        if self.selected not in keys:
            self.selected = None

    def _catalog_changed(self):
        self.group.save(self.catalog)
        self._sync_tiles()
        self.refresh()

    def _add_plugins(self):
        dlg = AddPluginDialog(
            st.installed_plugins(), self.catalog, self.group.number, self
        )
        if not dlg.exec():
            return
        if dlg.reset_requested:
            self.catalog = self.group.reset()
            self.order_keys = [e.key for e in self.catalog]
            self._sync_tiles()
            self.refresh()
            self.notify("Przywrócono listę startową wtyczek.")
            return
        added = [
            e for e in dlg.chosen if not catalog.contains(self.catalog, e.key)
        ]
        if not added:
            return
        self.catalog.extend(added)
        self._catalog_changed()
        for e in added:
            self.log.info(
                "Grupa {}: dodano kafelek {} ({}).".format(
                    self.group.number, e.label, e.key
                )
            )
        self.notify("Dodano wtyczki: {}.".format(len(added)))
        self._select(added[-1].key)

    def _remove_selected(self):
        entry = next((e for e in self.catalog if e.key == self.selected), None)
        if entry is None:
            return
        info = self.infos.get(entry.key)
        label = info.label if info else entry.label
        answer = QMessageBox.question(
            self,
            catalog.title(),
            "Usunąć kafelek „{}” z tej grupy?\n\n"
            "Sama wtyczka zostaje zainstalowana w QGIS.".format(label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.catalog = [e for e in self.catalog if e.key != entry.key]
        self.selected = None
        self._catalog_changed()
        self.notify("Usunięto kafelek: {}.".format(label))

    # ------------------------------------------------------------ grupy
    def _duplicate(self):
        existing = catalog.groups()
        free = [
            n for n in range(2, catalog.MAX_GROUPS + 1) if n not in existing
        ]
        if not free:
            QMessageBox.warning(
                self,
                "Limit grup",
                "Osiągnięto maksymalną liczbę grup ({}).\n\nUsuń nieużywaną "
                "grupę, aby utworzyć nową.".format(catalog.MAX_GROUPS),
            )
            return
        text, ok = QInputDialog.getText(
            self,
            "Duplikuj ikonę",
            "Utworzyć nową grupę nr {0}?\n\nNa pasku narzędzi pojawi się "
            "ikona z numerem {0}. Grupa startuje pusta (tylko kafel autora)."
            "\n\nOpis tematyczny grupy (pokazywany w dymku), np. Raster, "
            "Wektor, AI:".format(free[0]),
            QLineEdit.EchoMode.Normal,
            "",
        )
        if not ok:
            return
        n = self.controller.create_group(text)
        if n is not None:
            self.log.info(
                "Utworzono grupę {} „{}”.".format(n, catalog.Group(n).label())
            )

    def _delete_group(self):
        answer = QMessageBox.question(
            self,
            "Usuń grupę",
            "Usunąć grupę {} „{}”?\n\nZniknie jej ikona z paska narzędzi "
            "i jej kafelki. Same wtyczki zostają zainstalowane w QGIS.".format(
                self.group.number, self.group.label()
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.log.info(
                "Usunięto grupę {} „{}”.".format(
                    self.group.number, self.group.label()
                )
            )
            self.controller.delete_group(self.group.number)

    # ------------------------------------------------------------ kolejność
    def _tile_dropped(self, key, pos):
        if self.author_mode or key not in self.order_keys:
            return
        target, after = None, False
        for tile in self._visible_tiles():
            geom = tile.geometry()
            if geom.contains(pos):
                target = tile.key
                after = pos.x() > geom.center().x()
                break
        if target == key:
            return
        order = [k for k in self.order_keys if k != key]
        if target is None:
            order.append(key)
        else:
            order.insert(order.index(target) + (1 if after else 0), key)
        self.order_keys = order
        by_key = {e.key: e for e in self.catalog}
        self.catalog = [by_key[k] for k in order if k in by_key]
        self.group.save(self.catalog)
        self.group.clear_usage()
        self._relayout(force=True)
        self.log.info(
            "Grupa {}: zmieniono kolejność kafelków; liczniki użycia "
            "wyzerowane.".format(self.group.number)
        )

    # ------------------------------------------------------------ nazwy
    def _set_custom(self, info, text):
        text = (text or "").strip()
        if text == info.original:
            text = ""
        self.catalog = [
            e._replace(custom=text) if e.key == info.key else e
            for e in self.catalog
        ]
        self.group.save(self.catalog)
        self.log.info(
            "Kafelek „{}”: {}.".format(
                info.original,
                (
                    "nowa nazwa „{}”".format(text)
                    if text
                    else "przywrócono oryginalną nazwę"
                ),
            )
        )
        self.refresh()

    def _rename_tile(self, info):
        text, ok = QInputDialog.getText(
            self,
            "Zmień nazwę kafelka",
            "Nowa nazwa kafelka (puste pole = oryginalna nazwa\n„{}”):".format(
                info.original
            ),
            QLineEdit.EchoMode.Normal,
            info.label,
        )
        if ok:
            self._set_custom(info, text)

    def _title_menu(self, _pos):
        menu = QMenu(self)
        act_rename = menu.addAction("Zmień nazwę launchera…")
        act_orig = menu.addAction("Przywróć oryginalną nazwę launchera")
        act_orig.setEnabled(catalog.title() != catalog.DEFAULT_TITLE)
        menu.addSeparator()
        act_desc = menu.addAction(
            "Zmień opis grupy {}…".format(self.group.number)
        )
        chosen = menu.exec(QCursor.pos())
        if chosen is act_rename:
            text, ok = QInputDialog.getText(
                self,
                "Zmień nazwę launchera",
                "Nowa nazwa (puste pole = oryginalna nazwa\n„{}”):".format(
                    catalog.DEFAULT_TITLE
                ),
                QLineEdit.EchoMode.Normal,
                catalog.title(),
            )
            if ok:
                catalog.set_title(text)
                self.log.info("Nazwa launchera: „{}”.".format(catalog.title()))
                self.controller.update_titles()
        elif chosen is act_orig:
            catalog.set_title("")
            self.log.info("Przywrócono oryginalną nazwę launchera.")
            self.controller.update_titles()
        elif chosen is act_desc:
            text, ok = QInputDialog.getText(
                self,
                "Zmień opis grupy",
                "Nowy opis grupy {0} (puste pole = „Grupa {0}”):".format(
                    self.group.number
                ),
                QLineEdit.EchoMode.Normal,
                self.group.description(),
            )
            if ok:
                self.group.set_description(text)
                self.log.info(
                    "Grupa {}: opis „{}”.".format(
                        self.group.number, self.group.label()
                    )
                )
                self.controller.update_titles()

    # ------------------------------------------------------------ ikony pasków
    def update_icons_button(self):
        if self.btn_icons is None:
            return
        if catalog.icons_off():
            self.btn_icons.setText("Włącz ikony")
            self.btn_icons.setToolTip(
                tip(
                    "Ikony wtyczek z kafelkami są teraz schowane z pasków "
                    "narzędzi QGIS. Kliknij, aby przywrócić je na pasek "
                    "(we wszystkich grupach). Menu QGIS się nie zmienia.",
                    "Toolbar icons of plugins with tiles are now hidden. "
                    "Click to put them back on the QGIS toolbars (all "
                    "groups). QGIS menus are not changed.",
                )
            )
        else:
            self.btn_icons.setText("Wyłącz ikony")
            self.btn_icons.setToolTip(
                tip(
                    "Chowa z pasków narzędzi QGIS ikony wtyczek, które mają "
                    "kafelek w którejkolwiek grupie - uruchamiasz je "
                    "z kafelków. Menu QGIS się nie zmienia. Wyjątki: prawy "
                    "przycisk na kafelku → „Pokaż ikonę na pasku narzędzi”.",
                    "Hides from the QGIS toolbars the icons of plugins that "
                    "have a tile in any group - you start them from the "
                    "tiles. QGIS menus are not changed. Exceptions: "
                    "right-click a tile → “Pokaż ikonę na pasku narzędzi”.",
                )
            )

    def repaint_tiles(self):
        for info in self.infos.values():
            self._paint_tile(info)

    # ------------------------------------------------------------ skalowanie
    def _scale_text(self):
        return "Skaluj ikony ({}%)".format(catalog.tile_scale())

    def apply_scale(self):
        """Nowy rozmiar kafelków (wołane przez kontroler dla wszystkich
        okien)."""
        self.scale = catalog.tile_scale() / 100.0
        for tile in self.tiles.values():
            tile.apply_scale(self.scale)
        for info in self.infos.values():
            self._paint_tile(info)
        if self.btn_scale is not None:
            self.btn_scale.setText(self._scale_text())
        self._relayout(force=True)

    def _scale_popup(self):
        """Suwak 70-100% połączony z okienkiem do wpisania wartości."""
        menu = QMenu(self)
        box = QWidget(menu)
        lay = QHBoxLayout(box)
        lay.setContentsMargins(10, 6, 10, 6)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(catalog.SCALE_MIN, catalog.SCALE_MAX)
        slider.setSingleStep(1)
        slider.setPageStep(5)
        slider.setMinimumWidth(180)
        slider.setValue(catalog.tile_scale())
        spin = QSpinBox()
        spin.setRange(catalog.SCALE_MIN, catalog.SCALE_MAX)
        spin.setSuffix(" %")
        spin.setValue(catalog.tile_scale())
        hint = tip(
            "Rozmiar kafelków: 70-100%. Przesuń suwak albo wpisz liczbę.",
            "Tile size: 70-100%. Move the slider or type a number.",
        )
        slider.setToolTip(hint)
        spin.setToolTip(hint)
        lay.addWidget(QLabel("70%"))
        lay.addWidget(slider)
        lay.addWidget(QLabel("100%"))
        lay.addWidget(spin)

        def changed(value):
            if slider.value() != value:
                slider.setValue(value)
            if spin.value() != value:
                spin.setValue(value)
            self.controller.set_tile_scale(value)

        slider.valueChanged.connect(changed)
        spin.valueChanged.connect(changed)
        action = QWidgetAction(menu)
        action.setDefaultWidget(box)
        menu.addAction(action)
        pos = self.btn_scale.mapToGlobal(self.btn_scale.rect().bottomLeft())
        menu.exec(pos)
        self.log.info("Rozmiar kafelków: {}%.".format(catalog.tile_scale()))
