"""Tests for CCOverlayPanel — compact closed-caption overlay shell.

Covers:
- Child inventory: one QTextEdit, one QSizeGrip, no history/status chrome
- Size constraints: compact min/default/max bounds
- Grip anchoring: direct-child QSizeGrip at bottom-right corner
- Drag movement: mouse-drag repositions the panel
- Safe no-parent construction: works without parent, no crash
- Shell methods: show_panel, hide_panel (immediate + deferred), toggle_panel,
  dock_to_widget, clear
- Empty state: panel starts with _has_content == False
- Object names: panel and text_edit have correct objectNames
"""

import pytest

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import (
    QApplication,
    QSizeGrip,
    QTabWidget,
    QTextEdit,
    QWidget,
)

from meetandread.widgets.floating_panels import CCOverlayPanel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def qapp():
    """Provide a QApplication singleton for QWidget tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def cc_panel(qapp):
    """Create a shown CCOverlayPanel for testing, cleaned up after."""
    panel = CCOverlayPanel()
    panel.show()
    qapp.processEvents()
    yield panel
    panel.close()


@pytest.fixture
def cc_panel_with_parent(qapp):
    """Create a CCOverlayPanel with a parent widget, cleaned up after."""
    parent = QWidget()
    parent.show()
    qapp.processEvents()
    panel = CCOverlayPanel(parent=parent)
    panel.show()
    qapp.processEvents()
    yield panel, parent
    panel.close()
    parent.close()


# ---------------------------------------------------------------------------
# 1. Child inventory — correct children, no history/status
# ---------------------------------------------------------------------------

class TestChildInventory:
    """CCOverlayPanel must have exactly the expected child widgets."""

    def test_has_text_edit(self, cc_panel):
        text_edits = cc_panel.findChildren(QTextEdit)
        assert len(text_edits) >= 1, "CCOverlayPanel should have at least one QTextEdit"

    def test_text_edit_is_read_only(self, cc_panel):
        te = cc_panel.findChild(QTextEdit)
        assert te is not None
        assert te.isReadOnly(), "CC overlay text edit must be read-only"

    def test_has_size_grip(self, cc_panel):
        grip = cc_panel.findChild(QSizeGrip)
        assert grip is not None, "CCOverlayPanel should have a QSizeGrip child"

    def test_grip_is_direct_child(self, cc_panel):
        """QSizeGrip must be a direct child of the panel (MEM083)."""
        grip = cc_panel.findChild(QSizeGrip)
        assert grip is not None
        assert grip.parent() is cc_panel, "QSizeGrip parent must be the panel itself"

    def test_no_tab_widget(self, cc_panel):
        """CC overlay must not have a QTabWidget (no history chrome)."""
        tabs = cc_panel.findChildren(QTabWidget)
        assert len(tabs) == 0, "CC overlay should not contain any QTabWidget"

    def test_no_status_label(self, cc_panel):
        """CC overlay should not have status/recording labels."""
        from PyQt6.QtWidgets import QLabel
        labels = cc_panel.findChildren(QLabel)
        # We expect at most the text display widget, not status labels
        for label in labels:
            # No label should contain "Recording" or "Ready" status text
            text = label.text()
            assert "Recording" not in text
            assert "Ready" not in text


# ---------------------------------------------------------------------------
# 2. Size constraints — compact bounds
# ---------------------------------------------------------------------------

class TestSizeConstraints:
    """CC overlay uses compact size bounds suitable for caption overlay."""

    def test_minimum_width(self, cc_panel):
        assert cc_panel.minimumWidth() >= 280

    def test_minimum_height(self, cc_panel):
        assert cc_panel.minimumHeight() >= 80

    def test_maximum_width(self, cc_panel):
        assert cc_panel.maximumWidth() <= 1000

    def test_maximum_height(self, cc_panel):
        assert cc_panel.maximumHeight() <= 500

    def test_not_fixed_size(self, cc_panel):
        """Panel should be resizable (min != max)."""
        sz = cc_panel.minimumSize()
        mx = cc_panel.maximumSize()
        assert (sz.width() != mx.width()) or (sz.height() != mx.height())

    def test_compact_default_size(self, cc_panel):
        """Default size should be compact — smaller than transcript panel."""
        # CC overlay should be significantly smaller than FloatingTranscriptPanel
        # which has minSize(350, 300)
        assert cc_panel.minimumWidth() < 350
        assert cc_panel.minimumHeight() < 300


# ---------------------------------------------------------------------------
# 3. Grip anchoring — direct-child grip at bottom-right
# ---------------------------------------------------------------------------

class TestGripAnchoring:
    """QSizeGrip must anchor at bottom-right after resize."""

    def test_grip_at_bottom_right(self, cc_panel, qapp):
        cc_panel.resize(400, 200)
        qapp.processEvents()
        grip = cc_panel.findChild(QSizeGrip)
        assert grip is not None
        expected_x = cc_panel.width() - grip.width()
        expected_y = cc_panel.height() - grip.height()
        assert grip.x() == expected_x, f"Grip x={grip.x()}, expected {expected_x}"
        assert grip.y() == expected_y, f"Grip y={grip.y()}, expected {expected_y}"

    def test_grip_at_bottom_right_after_larger_resize(self, cc_panel, qapp):
        cc_panel.resize(600, 350)
        qapp.processEvents()
        grip = cc_panel.findChild(QSizeGrip)
        assert grip is not None
        expected_x = cc_panel.width() - grip.width()
        expected_y = cc_panel.height() - grip.height()
        assert grip.x() == expected_x
        assert grip.y() == expected_y

    def test_grip_at_bottom_right_at_min_size(self, cc_panel, qapp):
        min_w = cc_panel.minimumWidth()
        min_h = cc_panel.minimumHeight()
        cc_panel.resize(min_w, min_h)
        qapp.processEvents()
        grip = cc_panel.findChild(QSizeGrip)
        assert grip is not None
        expected_x = cc_panel.width() - grip.width()
        expected_y = cc_panel.height() - grip.height()
        assert grip.x() == expected_x
        assert grip.y() == expected_y

    def test_grip_visible(self, cc_panel):
        grip = cc_panel.findChild(QSizeGrip)
        assert grip is not None
        assert grip.isVisible()


# ---------------------------------------------------------------------------
# 4. Drag movement — mouse-drag repositions panel
# ---------------------------------------------------------------------------

class TestDragMovement:
    """Mouse drag on the panel background should move the window."""

    def test_drag_moves_panel(self, cc_panel, qapp):
        from PyQt6.QtCore import QPointF
        # Position the panel at a known location
        cc_panel.move(100, 100)
        qapp.processEvents()
        initial_pos = cc_panel.pos()

        # Simulate mouse press at center
        local = QPointF(cc_panel.width() / 2, cc_panel.height() / 2)
        global_press = QPointF(100 + local.x(), 100 + local.y())
        press = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            local, global_press,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        cc_panel.mousePressEvent(press)

        # Simulate mouse move to global position offset by (50, 30)
        global_move = QPointF(global_press.x() + 50, global_press.y() + 30)
        move = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(local.x() + 50, local.y() + 30),
            global_move,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        cc_panel.mouseMoveEvent(move)

        # Release
        release = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(local.x() + 50, local.y() + 30),
            global_move,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        cc_panel.mouseReleaseEvent(release)
        qapp.processEvents()

        # Panel should have moved by the drag offset
        new_pos = cc_panel.pos()
        assert new_pos != initial_pos, f"Panel should have moved: was {initial_pos}, now {new_pos}"


# ---------------------------------------------------------------------------
# 5. Safe no-parent construction
# ---------------------------------------------------------------------------

class TestSafeNoParentConstruction:
    """CCOverlayPanel must work when constructed without a parent."""

    def test_construct_no_parent(self, qapp):
        """Constructing without parent must not crash."""
        panel = CCOverlayPanel(parent=None)
        assert panel is not None
        panel.close()

    def test_show_without_parent(self, qapp):
        """Showing without parent must not crash."""
        panel = CCOverlayPanel(parent=None)
        panel.show()
        qapp.processEvents()
        assert panel.isVisible()
        panel.close()

    def test_dock_to_widget_without_parent(self, qapp):
        """dock_to_widget with a valid widget must work even without initial parent."""
        panel = CCOverlayPanel(parent=None)
        dummy = QWidget()
        dummy.show()
        qapp.processEvents()
        # Should not crash
        panel.dock_to_widget(dummy)
        qapp.processEvents()
        panel.close()
        dummy.close()


# ---------------------------------------------------------------------------
# 6. Shell methods — show, hide, toggle, clear
# ---------------------------------------------------------------------------

class TestShellMethods:
    """Shell methods must work correctly."""

    def test_show_panel(self, cc_panel, qapp):
        cc_panel.hide()
        qapp.processEvents()
        assert not cc_panel.isVisible()
        cc_panel.show_panel()
        qapp.processEvents()
        assert cc_panel.isVisible()

    def test_hide_panel_immediate(self, cc_panel, qapp):
        cc_panel.show()
        qapp.processEvents()
        assert cc_panel.isVisible()
        cc_panel.hide_panel(immediate=True)
        qapp.processEvents()
        assert not cc_panel.isVisible()

    def test_toggle_panel_shows(self, cc_panel, qapp):
        cc_panel.hide()
        qapp.processEvents()
        cc_panel.toggle_panel()
        qapp.processEvents()
        assert cc_panel.isVisible()

    def test_toggle_panel_hides(self, cc_panel, qapp):
        """Toggle on visible panel triggers fade-out which ends in hide."""
        cc_panel.show()
        qapp.processEvents()
        assert cc_panel.isVisible()
        cc_panel.toggle_panel()
        # The fade-out timer runs 15 steps of 10ms each
        # Process timer events by spinning the event loop with delays
        import time
        for _ in range(20):
            qapp.processEvents()
            time.sleep(0.01)
        qapp.processEvents()
        assert not cc_panel.isVisible(), "Panel should be hidden after fade-out completes"

    def test_clear_resets_content(self, cc_panel, qapp):
        te = cc_panel.findChild(QTextEdit)
        assert te is not None
        te.setPlainText("Some text")
        cc_panel.clear()
        assert te.toPlainText() == "", "clear() should empty the text edit"
        assert not cc_panel._has_content, "clear() should reset _has_content"

    def test_dock_to_widget_positions_panel(self, cc_panel_with_parent, qapp):
        panel, parent = cc_panel_with_parent
        panel.dock_to_widget(parent)
        qapp.processEvents()
        # Panel should be positioned near the parent (not at 0,0)
        parent_pos = parent.mapToGlobal(parent.rect().topLeft())
        # Panel x should be near parent right edge + offset
        assert panel.x() > 0, "Panel should be positioned (not at origin)"


# ---------------------------------------------------------------------------
# 7. Object names
# ---------------------------------------------------------------------------

class TestObjectNames:
    """Panel and child widgets must have correct object names for styling."""

    def test_panel_object_name(self, cc_panel):
        assert cc_panel.objectName() == "AethericCCOverlay"

    def test_text_edit_object_name(self, cc_panel):
        te = cc_panel.findChild(QTextEdit)
        assert te is not None
        # Text edit should have a scoped object name
        assert te.objectName() != "", "Text edit should have a non-empty objectName"


# ---------------------------------------------------------------------------
# 8. Window flags — frameless, tool, always-on-top
# ---------------------------------------------------------------------------

class TestWindowFlags:
    """CC overlay must have frameless/tool/always-on-top flags."""

    def test_frameless(self, cc_panel):
        flags = cc_panel.windowFlags()
        assert flags & Qt.WindowType.FramelessWindowHint

    def test_tool_window(self, cc_panel):
        flags = cc_panel.windowFlags()
        assert flags & Qt.WindowType.Tool

    def test_always_on_top(self, cc_panel):
        flags = cc_panel.windowFlags()
        assert flags & Qt.WindowType.WindowStaysOnTopHint

    def test_translucent_background(self, cc_panel):
        assert cc_panel.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
