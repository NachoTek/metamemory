"""Tests for widget edge-snap detection, peek position, slide animation,
and live magnet snap during drag.

Covers:
- Left/right-only snap detection (top returns None)
- Peek position math (1/5th visible when snapped)
- Slide animation convergence over ~9 ticks
- Live magnet snap during drag
"""

import time as _time
from unittest.mock import MagicMock, patch

import pytest

from PyQt6.QtCore import QPoint
from PyQt6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Qt application fixture (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication for the test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# Widget fixture — creates a minimal MeetAndReadWidget with mocked screen
# ---------------------------------------------------------------------------

class _FakeScreenGeometry:
    """Minimal stand-in for QScreen.geometry() — fixed 1920×1080 screen."""

    def __init__(self, width=1920, height=1080):
        self._w = width
        self._h = height

    def width(self):
        return self._w

    def height(self):
        return self._h

    def contains(self, point):
        return 0 <= point.x() < self._w and 0 <= point.y() < self._h


@pytest.fixture
def widget(qapp):
    """Create a MeetAndReadWidget with mocked screen geometry."""
    from meetandread.widgets.main_widget import MeetAndReadWidget

    fake_screen = MagicMock()
    fake_screen.geometry.return_value = _FakeScreenGeometry(1920, 1080)
    fake_screen.availableGeometry.return_value = _FakeScreenGeometry(1920, 1080)

    with patch.object(QApplication, "primaryScreen", return_value=fake_screen), \
         patch.object(QApplication, "screens", return_value=[fake_screen]), \
         patch("meetandread.widgets.main_widget.get_config") as mock_get, \
         patch("meetandread.widgets.main_widget.save_config"):
        from meetandread.config.models import UISettings, AppSettings
        mock_get.return_value = AppSettings(ui=UISettings())

        w = MeetAndReadWidget()
        w.show()
        yield w
        w.hide()
        w.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCREEN_W = 1920
SCREEN_H = 1080
WIDGET_W = 200
WIDGET_H = 120
SNAP_THRESHOLD = 20


def _move_to(widget, x, y):
    """Move widget and reset animation state."""
    widget.move(x, y)
    widget.is_dragging = False
    widget._slide_state.active = False


def _advance_animations(widget, ticks=15, interval_ms=33):
    """Advance _update_animations for *ticks* frames, simulating real time.

    Patches ``_time.monotonic`` so the animation engine sees elapsed time
    increasing by *interval_ms* per tick (matching the 33ms animation timer).
    """
    base_monotonic = _time.monotonic
    call_count = 0

    def fake_monotonic():
        nonlocal call_count
        call_count += 1
        return base_monotonic() + (call_count * interval_ms / 1000.0)

    with patch("meetandread.widgets.main_widget._time.monotonic", fake_monotonic):
        for _ in range(ticks):
            widget._update_animations()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSnapDetectionLeftRightOnly:
    """_check_snap_to_edge should only detect left and right edges."""

    def test_snap_left_triggers_slide(self, widget):
        """Widget near left edge should trigger a slide to peek position."""
        _move_to(widget, 10, 500)
        widget._check_snap_to_edge()
        # Animation should have started (slide to left peek position)
        assert widget._slide_state.active

    def test_snap_right_triggers_slide(self, widget):
        """Widget near right edge should trigger a slide to peek position."""
        _move_to(widget, SCREEN_W - WIDGET_W - 10, 500)
        widget._check_snap_to_edge()
        assert widget._slide_state.active

    def test_top_no_snap(self, widget):
        """Widget near top edge should NOT trigger snap."""
        _move_to(widget, 500, 5)
        widget._check_snap_to_edge()
        assert not widget._slide_state.active

    def test_bottom_no_snap(self, widget):
        """Widget near bottom edge should NOT trigger snap."""
        _move_to(widget, 500, SCREEN_H - WIDGET_H - 5)
        widget._check_snap_to_edge()
        assert not widget._slide_state.active

    def test_center_no_snap(self, widget):
        """Widget in center should not trigger snap."""
        _move_to(widget, 500, 500)
        widget._check_snap_to_edge()
        assert not widget._slide_state.active


class TestPeekPositionCalculation:
    """When snapped to edge, only 1/5th of widget width should be visible."""

    def test_peek_width_value(self, widget):
        """_peek_width should be 1/5th of widget width (40px for 200px widget)."""
        assert widget.width() == WIDGET_W
        assert widget._peek_width == 40  # int(200 * 0.2)

    def test_snap_left_peek_position(self, widget):
        """Snapping left should slide to x = -(width - peek_width) = -160."""
        _move_to(widget, 10, 500)
        widget._check_snap_to_edge()

        _advance_animations(widget, ticks=12)
        assert widget.pos().x() == -(WIDGET_W - 40)  # -160

    def test_snap_right_peek_position(self, widget):
        """Snapping right should slide to x = screen_width - peek_width = 1880."""
        _move_to(widget, SCREEN_W - WIDGET_W - 10, 500)
        widget._check_snap_to_edge()

        _advance_animations(widget, ticks=12)
        assert widget.pos().x() == SCREEN_W - 40  # 1880


class TestSlideAnimationInterpolation:
    """Slide animation should converge to target with ease-out deceleration."""

    def test_converges_to_target(self, widget):
        """After ~9 ticks (~300ms), widget position should reach target."""
        _move_to(widget, 500, 500)
        target = QPoint(100, 500)
        widget._start_slide_to(target)

        _advance_animations(widget, ticks=10)

        assert not widget._slide_state.active, "Animation should be finished"
        assert widget.pos().x() == target.x()
        assert widget.pos().y() == target.y()

    def test_ease_out_deceleration(self, widget):
        """Position should move more in early steps than later steps (ease-out)."""
        _move_to(widget, 500, 500)
        target = QPoint(100, 500)

        base_monotonic = _time.monotonic
        call_count = 0

        def fake_monotonic():
            nonlocal call_count
            call_count += 1
            return base_monotonic() + (call_count * 33 / 1000.0)

        widget._start_slide_to(target)
        positions = []
        with patch("meetandread.widgets.main_widget._time.monotonic", fake_monotonic):
            for _ in range(9):
                widget._update_animations()
                positions.append(widget.pos().x())

        deltas = [abs(positions[i + 1] - positions[i]) for i in range(len(positions) - 1)]

        mid = len(deltas) // 2
        early_avg = sum(deltas[:mid]) / max(mid, 1)
        late_avg = sum(deltas[mid:]) / max(len(deltas) - mid, 1)

        assert early_avg > late_avg, (
            f"Ease-out expected: early avg {early_avg:.1f} should be > late avg {late_avg:.1f}"
        )


class TestLiveMagnetSnapDuringDrag:
    """Live magnet snap should slide to peek position while dragging."""

    def test_magnet_snap_to_left_edge(self, widget):
        """Dragging near left edge should trigger magnet snap slide."""
        _move_to(widget, 500, 500)

        widget.is_dragging = True
        widget.drag_start_pos = QPoint(500, 500)
        widget.widget_start_pos = QPoint(500, 500)

        new_pos = QPoint(10, 500)
        widget._apply_drag_position(new_pos)

        # Should have started a slide animation to peek position
        assert widget._slide_state.active

        _advance_animations(widget, ticks=12)
        assert widget.pos().x() == -(WIDGET_W - 40)  # -160

    def test_magnet_snap_to_right_edge(self, widget):
        """Dragging near right edge should trigger magnet snap slide."""
        _move_to(widget, 500, 500)

        widget.is_dragging = True
        widget.drag_start_pos = QPoint(500, 500)
        widget.widget_start_pos = QPoint(500, 500)

        new_pos = QPoint(SCREEN_W - WIDGET_W - 10, 500)
        widget._apply_drag_position(new_pos)

        assert widget._slide_state.active

        _advance_animations(widget, ticks=12)
        assert widget.pos().x() == SCREEN_W - 40  # 1880

    def test_magnet_unsnap_away_from_edge(self, widget):
        """Moving away from edge during drag should follow mouse directly."""
        _move_to(widget, 500, 500)

        widget.is_dragging = True
        widget.drag_start_pos = QPoint(500, 500)
        widget.widget_start_pos = QPoint(500, 500)

        # First snap to left
        widget._apply_drag_position(QPoint(10, 500))

        # Now move to center — should follow mouse directly (no slide)
        center_pos = QPoint(500, 500)
        widget._apply_drag_position(center_pos)

        # Not near edge, so move() should have been called directly
        assert widget.pos().x() == 500

    def test_drag_edge_snap_check_method(self, widget):
        """_check_drag_edge_snap returns correct (should_snap, edge) tuples."""
        # Near left edge
        snap, edge = widget._check_drag_edge_snap(QPoint(5, 500))
        assert snap is True
        assert edge == "left"

        # Near right edge
        snap, edge = widget._check_drag_edge_snap(QPoint(SCREEN_W - WIDGET_W - 5, 500))
        assert snap is True
        assert edge == "right"

        # Center — no snap
        snap, edge = widget._check_drag_edge_snap(QPoint(500, 500))
        assert snap is False
        assert edge is None

        # Near top — no snap (top removed)
        snap, edge = widget._check_drag_edge_snap(QPoint(500, 5))
        assert snap is False
        assert edge is None


class TestFreeFloatingPanelPositioning:
    """Panels should open at a simple offset from widget — no docking."""

    def test_settings_panel_opens_at_offset(self, widget, qapp):
        """Settings panel should appear to the right of the widget."""
        widget.move(300, 200)
        panel = widget._floating_settings_panel
        assert panel is not None

        # Toggle settings open
        widget._toggle_settings_panel()
        for _ in range(20):
            qapp.processEvents()

        # Panel should be visible
        assert panel.isVisible()

        # Panel should be positioned to the right of the widget
        expected_x = widget.x() + widget.width() + 10
        expected_y = widget.y()
        assert panel.x() == expected_x
        assert panel.y() == expected_y

        # Clean up
        panel.hide_panel()

    def test_settings_panel_not_synced_on_widget_move(self, widget, qapp):
        """After opening, moving the widget should NOT move the settings panel."""
        widget.move(300, 200)
        panel = widget._floating_settings_panel

        widget._toggle_settings_panel()
        for _ in range(20):
            qapp.processEvents()

        panel_pos = panel.pos()

        # Move widget
        widget.move(600, 400)
        for _ in range(5):
            qapp.processEvents()

        # Panel should NOT have moved (free-floating)
        assert panel.pos() == panel_pos

        # Clean up
        panel.hide_panel()

    def test_cc_overlay_free_floating(self, widget, qapp):
        """CC overlay should not follow widget moves."""
        overlay = widget._cc_overlay
        if overlay is None:
            pytest.skip("CC overlay not available")

        widget.move(300, 200)
        overlay.show_panel()
        for _ in range(20):
            qapp.processEvents()

        original_pos = overlay.pos()

        # Move widget
        widget.move(600, 400)
        for _ in range(5):
            qapp.processEvents()

        # Overlay should NOT have moved
        assert overlay.pos() == original_pos

        # Clean up
        overlay.hide_panel()
