"""
Adaptive light/dark theme for floating panels and widget context menus.

Provides:
- ThemePalette dataclass with all named color tokens
- DARK_PALETTE / LIGHT_PALETTE presets
- current_palette() — auto-detects Windows desktop theme via Qt
- is_dark_mode() — quick boolean check
- Stylesheet generator functions that accept a ThemePalette and return QSS
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# ThemePalette — all named colour tokens
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThemePalette:
    """Named colour tokens for a single theme variant.

    Every token is a hex colour string (e.g. "#1a1a1a") that can be
    interpolated directly into QSS templates.
    """

    # Backgrounds
    bg: str
    surface: str
    surface_alt: str
    surface_hover: str
    dialog_bg: str

    # Borders
    border: str
    border_light: str
    border_strong: str

    # Text
    text: str
    text_secondary: str
    text_tertiary: str
    text_disabled: str

    # Semantic colours
    accent: str
    accent_text: str
    danger: str
    info: str

    # Resize grip
    grip_bg: str
    grip_hover: str

    # Badge / overlay
    badge_bg: str
    separator: str


# ---------------------------------------------------------------------------
# Preset palettes — dark values extracted from current floating_panels.py
# ---------------------------------------------------------------------------

DARK_PALETTE = ThemePalette(
    bg="#1a1a1a",
    surface="#2a2a2a",
    surface_alt="#333333",
    surface_hover="#3a3a3a",
    dialog_bg="#1a1a1a",
    border="#444444",
    border_light="#555555",
    border_strong="#666666",
    text="#ffffff",
    text_secondary="#dddddd",
    text_tertiary="#aaaaaa",
    text_disabled="#555555",
    accent="#4CAF50",
    accent_text="#ffffff",
    danger="#F44336",
    info="#4FC3F7",
    grip_bg="rgba(255, 255, 255, 60)",
    grip_hover="rgba(255, 255, 255, 120)",
    badge_bg="rgba(30, 30, 30, 210)",
    separator="#444444",
)

LIGHT_PALETTE = ThemePalette(
    bg="#ffffff",
    surface="#f5f5f5",
    surface_alt="#e0e0e0",
    surface_hover="#d6d6d6",
    dialog_bg="#ffffff",
    border="#bdbdbd",
    border_light="#cccccc",
    border_strong="#999999",
    text="#212121",
    text_secondary="#424242",
    text_tertiary="#757575",
    text_disabled="#9e9e9e",
    accent="#2E7D32",
    accent_text="#ffffff",
    danger="#C62828",
    info="#0277BD",
    grip_bg="rgba(0, 0, 0, 50)",
    grip_hover="rgba(0, 0, 0, 100)",
    badge_bg="rgba(255, 255, 255, 230)",
    separator="#bdbdbd",
)


# ---------------------------------------------------------------------------
# Theme detection helpers
# ---------------------------------------------------------------------------

def current_palette() -> ThemePalette:
    """Return the active palette based on the desktop colour scheme.

    Uses ``QGuiApplication.styleHints().colorScheme`` to detect the
    Windows light/dark theme.  Falls back to ``DARK_PALETTE`` when the
    scheme is ``Unknown`` or when Qt is unavailable (e.g. during tests
    without a QApplication).

    Returns:
        ThemePalette — either LIGHT_PALETTE or DARK_PALETTE.
    """
    try:
        from PyQt6.QtGui import QGuiApplication
        hints = QGuiApplication.styleHints()
        if hints is None:
            logger.info("Theme detection: no styleHints, falling back to dark")
            return DARK_PALETTE
        scheme = hints.colorScheme()
        if scheme is None:
            logger.info("Theme detection: scheme is None, falling back to dark")
            return DARK_PALETTE
        # Import the enum for comparison
        from PyQt6.QtGui import QtColorScheme
        if scheme == QtColorScheme.Dark:
            logger.debug("Theme detected: Dark")
            return DARK_PALETTE
        elif scheme == QtColorScheme.Light:
            logger.info("Theme detected: Light")
            return LIGHT_PALETTE
        else:
            logger.info("Theme detected: Unknown, falling back to dark")
            return DARK_PALETTE
    except (ImportError, RuntimeError) as exc:
        logger.info("Theme detection unavailable (%s), falling back to dark", exc)
        return DARK_PALETTE


def is_dark_mode() -> bool:
    """Return True when the active theme is the dark palette."""
    return current_palette() is DARK_PALETTE


# ---------------------------------------------------------------------------
# Stylesheet generators — each accepts a ThemePalette and returns QSS
# ---------------------------------------------------------------------------

def panel_base_css(p: ThemePalette, class_name: str = "QWidget") -> str:
    """Panel background, border, and border-radius.

    Args:
        p: Active theme palette.
        class_name: QWidget subclass name for the QSS selector.

    Returns:
        QSS string for the panel base.
    """
    return f"""
        {class_name} {{
            background-color: {p.bg};
            border: 2px solid {p.border};
            border-radius: 10px;
        }}
    """


def title_css(p: ThemePalette) -> str:
    """Panel title label — accent-coloured, bold.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for the title QLabel.
    """
    return f"""
        QLabel {{
            color: {p.accent};
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
        }}
    """


def header_button_css(p: ThemePalette, variant: str = "close") -> str:
    """Header button (close or legend toggle).

    Args:
        p: Active theme palette.
        variant: 'close' or 'legend'.

    Returns:
        QSS string for the button.
    """
    hover_bg = p.danger if variant == "close" else p.surface_hover
    hover_border = p.danger if variant == "close" else p.accent
    checked_bg = p.danger if variant == "close" else p.accent
    checked_text = p.text if variant == "close" else p.accent_text

    return f"""
        QPushButton {{
            background-color: {p.surface_alt};
            color: {p.text};
            border: 1px solid {p.border_light};
            border-radius: 12px;
            font-size: 16px;
            font-weight: bold;
            padding: 0;
        }}
        QPushButton:hover {{
            background-color: {hover_bg};
            border-color: {hover_border};
        }}
        QPushButton:checked {{
            background-color: {checked_bg};
            color: {checked_text};
            border-color: {checked_bg};
        }}
    """


def tab_widget_css(p: ThemePalette) -> str:
    """QTabWidget::pane and QTabBar::tab styles.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for tab widget and tab bar.
    """
    return f"""
        QTabWidget::pane {{
            border: 1px solid {p.border};
            border-radius: 5px;
            background-color: {p.bg};
        }}
        QTabBar::tab {{
            background-color: {p.surface};
            color: {p.text_tertiary};
            padding: 6px 14px;
            border: 1px solid {p.border};
            border-bottom: none;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            background-color: {p.surface_alt};
            color: {p.accent};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            background-color: {p.surface_hover};
        }}
    """


def text_area_css(p: ThemePalette) -> str:
    """QTextEdit / QTextBrowser styling.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for text areas.
    """
    return f"""
        QTextEdit {{
            background-color: {p.surface};
            color: {p.text};
            border: none;
            border-radius: 5px;
            padding: 8px;
            font-size: 13px;
            line-height: 1.4;
        }}
        QTextBrowser {{
            background-color: {p.surface};
            color: {p.text};
            border: none;
            border-radius: 5px;
            padding: 8px;
            font-size: 13px;
            line-height: 1.4;
        }}
    """


def combo_box_css(p: ThemePalette, accent_color: str | None = None) -> str:
    """QComboBox with optional accent colour override.

    Args:
        p: Active theme palette.
        accent_color: Override for hover border (defaults to palette accent).

    Returns:
        QSS string for combo boxes.
    """
    accent = accent_color or p.accent
    return f"""
        QComboBox {{
            background-color: {p.surface};
            color: {p.text_secondary};
            border: 1px solid {p.border_light};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border-color: {accent};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {p.text_tertiary};
        }}
        QComboBox QAbstractItemView {{
            background-color: {p.surface};
            color: {p.text_secondary};
            border: 1px solid {p.border_light};
            selection-background-color: {p.surface_alt};
            selection-color: {p.text};
        }}
    """


def action_button_css(p: ThemePalette, variant: str = "scrub") -> str:
    """Action button with semantic variants.

    Variants:
        'scrub'     — info-tinted background, info text
        'delete'    — danger-tinted background, danger text
        'benchmark' — neutral background, accent text
        'dialog'    — neutral background for dialog buttons

    Args:
        p: Active theme palette.
        variant: One of 'scrub', 'delete', 'benchmark', 'dialog'.

    Returns:
        QSS string for the button.
    """
    if variant == "scrub":
        return f"""
            QPushButton {{
                background-color: {p.surface};
                color: {p.info};
                border: 1px solid {p.border_light};
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {p.surface_hover};
                border-color: {p.info};
            }}
            QPushButton:pressed {{
                background-color: {p.surface};
            }}
            QPushButton:disabled {{
                background-color: {p.surface_alt};
                color: {p.text_disabled};
                border-color: {p.border};
            }}
        """
    elif variant == "delete":
        return f"""
            QPushButton {{
                background-color: {p.surface};
                color: {p.danger};
                border: 1px solid {p.border_light};
                border-radius: 4px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {p.surface_hover};
                border-color: {p.danger};
            }}
            QPushButton:pressed {{
                background-color: {p.surface};
            }}
        """
    elif variant == "benchmark":
        return f"""
            QPushButton {{
                background-color: {p.surface_alt};
                color: {p.accent};
                border: 1px solid {p.border_light};
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {p.surface_hover};
                border-color: {p.accent};
            }}
            QPushButton:pressed {{
                background-color: {p.surface};
            }}
            QPushButton:disabled {{
                color: {p.text_disabled};
                border-color: {p.border};
            }}
        """
    else:  # 'dialog'
        return f"""
            QPushButton {{
                background-color: {p.surface_alt};
                color: {p.text_secondary};
                border: 1px solid {p.border_light};
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
                min-width: 70px;
            }}
            QPushButton:hover {{
                background-color: {p.surface_hover};
                border-color: {p.accent};
            }}
            QPushButton:pressed {{
                background-color: {p.surface};
            }}
        """


def list_widget_css(p: ThemePalette) -> str:
    """QListWidget styling.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for list widgets.
    """
    return f"""
        QListWidget {{
            background-color: {p.surface};
            color: {p.text_secondary};
            border: none;
            border-radius: 5px;
            font-size: 12px;
            padding: 4px;
            outline: none;
        }}
        QListWidget::item {{
            padding: 6px 8px;
            border-bottom: 1px solid {p.surface_alt};
        }}
        QListWidget::item:selected {{
            background-color: {p.surface_alt};
            color: {p.text};
        }}
        QListWidget::item:hover {{
            background-color: {p.surface_hover};
        }}
    """


def progress_bar_css(p: ThemePalette, chunk_color: str | None = None) -> str:
    """QProgressBar template with customisable chunk colour.

    Args:
        p: Active theme palette.
        chunk_color: Colour for the progress chunk (defaults to accent).

    Returns:
        QSS string for progress bars.
    """
    color = chunk_color or p.accent
    return f"""
        QProgressBar {{
            border: 1px solid {p.border_light};
            border-radius: 4px;
            background-color: {p.surface};
            text-align: center;
            color: {p.text_secondary};
            font-size: 11px;
            height: 16px;
        }}
        QProgressBar::chunk {{
            background-color: {color};
            border-radius: 3px;
        }}
    """


def context_menu_css(p: ThemePalette, accent_color: str | None = None) -> str:
    """QMenu / context menu styling.

    Args:
        p: Active theme palette.
        accent_color: Override for selected-item background (defaults to accent).

    Returns:
        QSS string for menus.
    """
    accent = accent_color or p.accent
    return f"""
        QMenu {{
            background-color: {p.surface};
            color: {p.text_secondary};
            border: 1px solid {p.border_light};
            border-radius: 5px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 20px;
            border-radius: 3px;
        }}
        QMenu::item:selected {{
            background-color: {accent};
            color: {p.accent_text};
        }}
    """


def dialog_css(p: ThemePalette) -> str:
    """QDialog base styling.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for dialogs.
    """
    return f"""
        QDialog {{
            background-color: {p.dialog_bg};
        }}
        QLabel {{
            color: {p.text_secondary};
            font-size: 12px;
        }}
    """


def badge_css(p: ThemePalette) -> str:
    """New-content badge (auto-scroll pause indicator).

    Args:
        p: Active theme palette.

    Returns:
        QSS string for the badge QPushButton.
    """
    return f"""
        QPushButton {{
            background-color: {p.badge_bg};
            color: {p.text};
            border: 1px solid {p.border_strong};
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: {p.surface_hover};
            border: 1px solid {p.border_strong};
        }}
        QPushButton:pressed {{
            background-color: {p.surface_alt};
        }}
    """


def resize_grip_css(p: ThemePalette) -> str:
    """QSizeGrip styling.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for the resize grip.
    """
    return f"""
        QSizeGrip {{
            background-color: {p.grip_bg};
            border-radius: 3px;
        }}
        QSizeGrip:hover {{
            background-color: {p.grip_hover};
        }}
    """


def legend_overlay_css(p: ThemePalette) -> Dict[str, str]:
    """Legend overlay styles — returns a dict of named QSS strings.

    The legend overlay is a QFrame with child QLabels and a separator
    QFrame.  Returns individual QSS blocks so the caller can apply them
    to the correct child widgets.

    Args:
        p: Active theme palette.

    Returns:
        Dict with keys: 'overlay', 'title', 'separator', 'range_label',
        'desc_label'.  Each value is a QSS string.
    """
    return {
        "overlay": f"""
            QFrame {{
                background-color: {p.surface};
                border: 1px solid {p.border_light};
                border-radius: 8px;
                padding: 8px;
            }}
        """,
        "title": f"color: {p.text}; font-weight: bold; font-size: 12px; border: none;",
        "separator": f"background-color: {p.border_light}; border: none;",
        "range_label": f"color: {p.text}; font-size: 11px; border: none;",
        "desc_label": f"color: {p.text_tertiary}; font-size: 11px; border: none;",
    }


def detail_header_css(p: ThemePalette) -> str:
    """Detail header frame (above history viewer).

    Args:
        p: Active theme palette.

    Returns:
        QSS string for the detail header QFrame.
    """
    return f"""
        QFrame {{
            background-color: {p.surface};
            border-bottom: 1px solid {p.border};
            border-radius: 0px;
        }}
    """


def separator_css(p: ThemePalette) -> str:
    """QFrame horizontal separator.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for a horizontal separator line.
    """
    return f"QFrame {{ background-color: {p.separator}; max-height: 1px; border: none; }}"


def info_label_css(p: ThemePalette) -> str:
    """Small metric / info labels.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for info QLabels.
    """
    return f"QLabel {{ color: {p.text_tertiary}; font-size: 11px; }}"


def status_label_css(p: ThemePalette) -> str:
    """Status text label.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for the status QLabel.
    """
    return f"""
        QLabel {{
            color: {p.text_tertiary};
            font-size: 11px;
            padding: 3px;
        }}
    """


def splitter_css(p: ThemePalette) -> str:
    """QSplitter handle styling.

    Args:
        p: Active theme palette.

    Returns:
        QSS string for splitter handles.
    """
    return f"""
        QSplitter::handle {{
            background-color: {p.border};
            height: 3px;
        }}
    """
