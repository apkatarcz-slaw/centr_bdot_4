# -*- coding: utf-8 -*-
"""Dymki dwujęzyczne: tekst polski, a pod nim angielski."""

import html

EN_COLOR = "#1e64be"


def tip(pl, en, title_pl="", title_en=""):
    """Dymek: opcjonalny pogrubiony tytuł, polski tekst, angielski pod nim.
    Teksty są wstawiane bez zmian (mogą zawierać proste znaczniki HTML)."""
    parts = []
    if title_pl:
        head = "<b>{}</b>".format(title_pl)
        if title_en and title_en != title_pl:
            head += ' <span style="color:{}">/ {}</span>'.format(
                EN_COLOR, title_en
            )
        parts.append(head)
    parts.append(pl)
    parts.append('<span style="color:{}">{}</span>'.format(EN_COLOR, en))
    return '<qt><div style="max-width:340px">{}</div></qt>'.format(
        "<br>".join(parts)
    )


def esc(text):
    return html.escape(str(text or ""))


HINT_PL = (
    "(W celu zmiany nazwy wtyczki najedź na jej nazwę w oknie i kliknij "
    "prawym klawiszem)"
)
HINT_EN = "(To rename, hover over its name in the window and right-click)"
