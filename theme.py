# -*- coding: utf-8 -*-
"""
Bside Browser & AI Agent Sidebar — Design Tokens & Theme Engine
Minimalist, cozy & tactile 3D aesthetic (matches reference screenshots: warm ivory / deep slate).
"""

from version import APP_NAME, APP_VERSION

AGENT_VERSION = "1.0.2"

DARK_PALETTE = {
    "name": "dark",
    "bg": "#1D1D20",            # main workspace & newtab background
    "bg_elevated": "#252529",   # elevated cards & toolbar
    "sidebar": "#18181B",       # sidepanel & top chrome
    "card": "#27272B",          # omnibox & composer surface
    "card_hover": "#313136",    # hover state
    "popover": "#2C2C31",       # dropdown / mention menu
    "fg": "#F4F4F6",            # primary text
    "fg_muted": "#9E9EA8",      # secondary text
    "fg_subtle": "#6E6E78",     # muted labels / placeholders
    "border": "#2E2E34",        # subtle 1px neutral border
    "border_strong": "#3F3F47", # active neutral border (no glaring blue)
    "primary": "#F4F4F6",       # primary button bg in dark mode
    "primary_fg": "#18181B",    # primary button text
    "accent": "#5B5BD6",        # cozy indigo accent
    "accent_soft": "#28293E",   # subtle soft badge bg
    "accent_fg": "#A5B4FC",     # indigo badge text
    "ask_accent": "#10B981",    # emerald agent active status
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "tab_active": "#2B2B30",
    "tab_inactive": "transparent",
}

LIGHT_PALETTE = {
    "name": "light",
    "bg": "#F9F8F4",            # warm cozy ivory background (matches Image 1, 2, 4)
    "bg_elevated": "#F2F0EA",   # toolbar / soft button surface
    "sidebar": "#F3F2ED",       # sidepanel & top chrome background (matches Image 3, 4)
    "card": "#FFFFFF",          # omnibox & composer white card (matches Image 4)
    "card_hover": "#EAE8E1",    # soft tactile hover
    "popover": "#FFFFFF",
    "fg": "#1E1E20",            # crisp charcoal text
    "fg_muted": "#666560",      # warm muted gray
    "fg_subtle": "#94928B",     # placeholder gray
    "border": "#E5E3DC",        # delicate 1px warm border
    "border_strong": "#D0CEC5", # slightly stronger neutral border
    "primary": "#1E1E20",       # dark circular action button (matches Image 4 black button)
    "primary_fg": "#FFFFFF",
    "accent": "#4F46E5",
    "accent_soft": "#E0E7FF",
    "accent_fg": "#4338CA",
    "ask_accent": "#059669",
    "warning": "#D97706",
    "danger": "#DC2626",
    "tab_active": "#FFFFFF",
    "tab_inactive": "transparent",
}


def get_palette(theme_mode: str = "light") -> dict:
    return DARK_PALETTE if theme_mode == "dark" else LIGHT_PALETTE


def get_app_stylesheet(theme_mode: str = "light") -> str:
    p = get_palette(theme_mode)
    return f"""
    QMainWindow, QWidget#RootContainer {{
        background-color: {p['bg']};
        color: {p['fg']};
        font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Malgun Gothic', sans-serif;
        font-size: 13px;
    }}

    QLabel {{
        border: none;
        background: transparent;
    }}

    /* Top Tab Strip & Navigation Chrome */
    QWidget#TopChrome {{
        background-color: {p['sidebar']};
        border-bottom: 1px solid {p['border']};
    }}

    QWidget#NavToolbar {{
        background-color: {p['bg']};
        border-bottom: 1px solid {p['border']};
    }}

    QWidget#BookmarksBar {{
        background-color: {p['bg']};
        border-bottom: 1px solid {p['border']};
    }}

    /* Custom Tab Pill in Tab Bar */
    QFrame#BrowserTabPill {{
        background-color: {p['tab_inactive']};
        border: 1px solid transparent;
        border-radius: 10px;
    }}
    QFrame#BrowserTabPill[active="true"] {{
        background-color: {p['tab_active']};
        border: 1px solid {p['border']};
    }}
    QFrame#BrowserTabPill:hover {{
        background-color: {p['card_hover']};
    }}

    /* Tactile 3D-ish Navigation & Header Icon Buttons (Generous 34x34 size) */
    QPushButton.NavIconBtn {{
        background-color: transparent;
        color: {p['fg']};
        border: 1px solid transparent;
        border-radius: 9px;
        padding: 5px 8px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton.NavIconBtn:hover {{
        background-color: {p['card_hover']};
        border: 1px solid {p['border']};
    }}
    QPushButton.NavIconBtn:pressed {{
        background-color: {p['border']};
    }}
    QPushButton.NavIconBtn[active="true"] {{
        background-color: {p['card']};
        color: {p['accent']};
        border: 1px solid {p['border_strong']};
    }}

    /* Dual-Mode Address / Omnibox Bar — Soft rounded pill */
    QFrame#OmniboxContainer {{
        background-color: {p['card']};
        border: 1px solid {p['border']};
        border-radius: 12px;
    }}
    QFrame#OmniboxContainer[mode="ask"] {{
        border: 1px solid {p['border_strong']};
        background-color: {p['card']};
    }}

    QPushButton#OmniboxModeBadge {{
        background-color: {p['bg_elevated']};
        color: {p['fg_muted']};
        border: none;
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 11.5px;
        font-weight: 700;
    }}
    QPushButton#OmniboxModeBadge[mode="ask"] {{
        background-color: {p['accent']};
        color: #FFFFFF;
        border: none;
    }}

    QLineEdit#OmniboxInput {{
        background: transparent;
        color: {p['fg']};
        border: none;
        font-size: 13.5px;
        selection-background-color: {p['accent']};
    }}

    /* Bookmark Chip */
    QPushButton.BookmarkChip {{
        background-color: transparent;
        color: {p['fg_muted']};
        border: none;
        border-radius: 8px;
        padding: 4px 10px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton.BookmarkChip:hover {{
        background-color: {p['card_hover']};
        color: {p['fg']};
    }}

    /* Splitter */
    QSplitter::handle {{
        background-color: {p['border']};
        width: 1px;
    }}

    /* Dialogs & Inputs */
    QDialog {{
        background-color: {p['bg']};
        color: {p['fg']};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        background-color: {p['card']};
        color: {p['fg']};
        border: 1px solid {p['border']};
        border-radius: 9px;
        padding: 6px 10px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}
    QListWidget, QTreeWidget, QTableWidget {{
        background-color: {p['card']};
        color: {p['fg']};
        border: 1px solid {p['border']};
        border-radius: 10px;
        outline: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 7px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border_strong']};
        min-height: 24px;
        border-radius: 3px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* Crisp Speech-Bubble Tooltips (풍선말) */
    QToolTip {{
        background-color: #1E1E22;
        color: #FFFFFF;
        border: 1px solid #3F3F47;
        border-radius: 8px;
        padding: 6px 10px;
        font-family: 'Segoe UI Variable Text', 'Segoe UI', 'Malgun Gothic', sans-serif;
        font-size: 12px;
        font-weight: 600;
    }}
    """
