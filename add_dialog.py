# -*- coding: utf-8 -*-
"""Okno „Dodaj wtyczkę”: wybór spośród wtyczek zainstalowanych w QGIS."""

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QColor, QFont, QIcon
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from . import catalog
from .i18n import esc, tip
from .icons import fallback_icon

ROLE_DATA = Qt.ItemDataRole.UserRole.value
ROLE_TEXT = Qt.ItemDataRole.UserRole.value + 1


class AddPluginDialog(QDialog):
    """Po zamknięciu przyciskiem „Dodaj”: self.chosen to lista CatalogEntry,
    a self.reset_requested mówi, czy przywrócić listę startową grupy."""

    def __init__(self, installed, entries, group_number, parent=None):
        super().__init__(parent)
        self.chosen = []
        self.reset_requested = False
        self.group_number = group_number
        self.setWindowTitle("Dodaj wtyczkę – grupa {}".format(group_number))
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumSize(480, 420)
        self.resize(620, 560)

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "Zaznacz jedną lub kilka zainstalowanych wtyczek i kliknij "
                "„Dodaj”. Wtyczki BDOO / BDOT10k są pogrubione, "
                "wyłączone - szare (po kliknięciu kafelka launcher "
                "zaproponuje włączenie).",
                wordWrap=True,
            )
        )

        self.search = QLineEdit()
        self.search.setPlaceholderText("Szukaj wśród zainstalowanych…")
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip(
            tip(
                "Filtruje listę po nazwie, identyfikatorze i opisie.",
                "Filters the list by name, identifier and description.",
            )
        )
        root.addWidget(self.search)

        self.list = QListWidget()
        self.list.setIconSize(QSize(24, 24))
        self.list.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.list.setToolTip(
            tip(
                "Kliknij, aby zaznaczyć. Ctrl+klik zaznacza kilka wtyczek. "
                "Dwuklik dodaje od razu.",
                "Click to select. Ctrl+click selects several plugins. "
                "Double-click adds immediately.",
            )
        )
        root.addWidget(self.list, 1)

        self.empty = QLabel(wordWrap=True)
        self.empty.setStyleSheet("color: #c81e1e;")
        self.empty.hide()
        root.addWidget(self.empty)

        buttons = QHBoxLayout()
        self.btn_reset = QPushButton("Przywróć listę startową")
        if group_number == 1:
            self.btn_reset.setToolTip(
                tip(
                    "Przywraca 7 wtyczek startowych w oryginalnej kolejności "
                    "i z oryginalnymi nazwami. Kafelki dodane przez Ciebie "
                    "znikną (same wtyczki zostają zainstalowane).",
                    "Restores the 7 starting plugins in the original order "
                    "and with original names. Tiles you added will be "
                    "removed (plugins stay installed).",
                )
            )
        else:
            self.btn_reset.setToolTip(
                tip(
                    "Czyści grupę - zostaje tylko kafel autora. Same "
                    "wtyczki zostają zainstalowane.",
                    "Clears the group - only the author tile remains. "
                    "Plugins stay installed.",
                )
            )
        self.btn_cancel = QPushButton("Anuluj")
        self.btn_add = QPushButton("Dodaj")
        self.btn_add.setDefault(True)
        self.btn_add.setEnabled(False)
        self.btn_add.setToolTip(
            tip(
                "Dodaje zaznaczone wtyczki jako kafelki tej grupy.",
                "Adds the selected plugins as tiles of this group.",
            )
        )
        buttons.addWidget(self.btn_reset)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_add)
        root.addLayout(buttons)

        self._fill(installed, entries)

        self.search.textChanged.connect(self._filter)
        self.list.itemSelectionChanged.connect(
            lambda: self.btn_add.setEnabled(bool(self.list.selectedItems()))
        )
        self.list.itemDoubleClicked.connect(lambda _item: self._accept())
        self.btn_add.clicked.connect(self._accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_reset.clicked.connect(self._reset)

    def _fill(self, installed, entries):
        bold = QFont()
        bold.setBold(True)
        rows = [
            r for r in installed if not catalog.contains(entries, r["key"])
        ]
        rows.sort(key=lambda r: (not catalog.matches(r), r["name"].lower()))
        for rec in rows:
            topic = catalog.matches(rec)
            label = "{}   ({})".format(rec["name"], rec["key"])
            if not rec["active"]:
                label += "  •  wyłączona"
            icon = QIcon(rec["icon"]) if rec["icon"] else None
            if icon is None or icon.isNull():
                icon = fallback_icon(rec["key"], rec["name"])
            item = QListWidgetItem(icon, label)
            item.setData(ROLE_DATA, rec)
            item.setData(
                ROLE_TEXT,
                " ".join(
                    (rec["name"], rec["key"], rec["description"])
                ).lower(),
            )
            item.setToolTip(
                tip(
                    esc(rec["description"])
                    + (
                        "<br><i>Wtyczka wyłączona.</i>"
                        if not rec["active"]
                        else ""
                    ),
                    "Installed plugin"
                    + (" (disabled)." if not rec["active"] else "."),
                    esc(rec["name"]),
                )
            )
            if topic:
                item.setFont(bold)
            if not rec["active"]:
                item.setForeground(QColor("#828282"))
            self.list.addItem(item)
        if not rows:
            self.empty.setText(
                "Wszystkie zainstalowane wtyczki są już w tej grupie. "
                "Nową wtyczkę zainstaluj w Menedżerze wtyczek QGIS, a potem "
                "dodaj jej kafelek."
            )
            self.empty.show()

    def _filter(self, *_):
        text = self.search.text().strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(bool(text) and text not in item.data(ROLE_TEXT))

    def _accept(self):
        for item in self.list.selectedItems():
            rec = item.data(ROLE_DATA)
            self.chosen.append(
                catalog.CatalogEntry(
                    rec["key"], rec["name"], rec["description"]
                )
            )
        if self.chosen:
            self.accept()

    def _reset(self):
        if self.group_number == 1:
            text = (
                "Lista wróci do 7 wtyczek startowych, a kafelki dodane przez "
                "Ciebie, zmienione nazwy kafelków i liczniki użycia znikną. "
                "Same wtyczki zostają zainstalowane w QGIS.\n\nKontynuować?"
            )
        else:
            text = (
                "Grupa {} zostanie wyczyszczona - zostanie tylko kafel "
                "autora. Same wtyczki zostają zainstalowane w QGIS.\n\n"
                "Kontynuować?".format(self.group_number)
            )
        answer = QMessageBox.question(
            self,
            "Przywróć listę startową",
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.reset_requested = True
            self.accept()
