# Widget Double-Click Issue Diagnosis

## Problem Summary
Widget interactions (record button and source lobes) require double-click instead of single-click.

## Root Cause

### Issue 1: Event Consumption in Parent Widget
**Location:** `src/metamemory/widgets/main_widget.py:147-161`

The `MeetAndReadWidget.mousePressEvent` method intercepts and **accepts** all left-button clicks that occur on the record button or toggle lobes:

```python
def mousePressEvent(self, event):
    """Start dragging."""
    if event.button() == Qt.MouseButton.LeftButton:
        scene_pos = self.mapToScene(event.pos())
        items = self._scene.items(scene_pos)
        
        if any(isinstance(item, (RecordButtonItem, ToggleLobeItem, SettingsLobeItem)) 
               for item in items):
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint()
            self.widget_start_pos = self.pos()
            event.accept()  # <-- PROBLEM: Event is consumed here
```

**Impact:** When `event.accept()` is called, the event propagation stops. The event never reaches the individual items' `mousePressEvent` handlers that are supposed to handle the actual click actions.

### Issue 2: Items Have Correct Handlers That Never Get Called
**Locations:**
- `RecordButtonItem.mousePressEvent` (lines 426-430)
- `ToggleLobeItem.mousePressEvent` (lines 481-487)
- `SettingsLobeItem.mousePressEvent` (lines 514-518)

These items have proper click handlers:
```python
def mousePressEvent(self, event):
    """Handle click."""
    if event.button() == Qt.MouseButton.LeftButton:
        self.parent_widget.toggle_recording()
        event.accept()
```

But they never execute because the parent widget consumes the event first.

### Why Double-Click Works
1. **First click:** Parent widget's `mousePressEvent` catches it, sets `is_dragging = True`, and accepts the event. Items never see it.
2. **Second click:** Since `is_dragging` is already True, the drag logic still runs, but somehow the item's `mousePressEvent` also fires (possibly due to Qt's double-click handling or event timing).

## Investigation Details

### Event Flow (Current - Broken)
```
User clicks item
  ↓
MeetAndReadWidget.mousePressEvent
  ↓
Detects item is RecordButtonItem/ToggleLobeItem
  ↓
Sets is_dragging = True
  ↓
event.accept() ← STOPS HERE
  ↓
Item.mousePressEvent NEVER CALLED
```

### Event Flow (Expected)
```
User clicks item
  ↓
MeetAndReadWidget.mousePressEvent
  ↓
Detects item is RecordButtonItem/ToggleLobeItem
  ↓
Do NOT accept - let it propagate
  ↓
Item.mousePressEvent receives event
  ↓
Item handles action (toggle recording, toggle source, etc.)
```

## Additional Findings

### QGraphicsScene Event Propagation
In QGraphicsView/QGraphicsScene architecture:
- Mouse events are first delivered to the QGraphicsView
- The view maps them to scene coordinates
- Events should propagate to the scene items

The current implementation breaks this by calling `event.accept()` at the view level before items can receive the event.

## Artifacts

### Affected Code Locations

1. **`main_widget.py:147-161`** - Parent widget's `mousePressEvent` that consumes events
2. **`main_widget.py:426-430`** - RecordButtonItem's click handler (never reached)
3. **`main_widget.py:481-487`** - ToggleLobeItem's click handler (never reached)
4. **`main_widget.py:514-518`** - SettingsLobeItem's click handler (never reached)

## Suggested Fix

### Option 1: Distinguish Click from Drag
Check if the mouse actually moved before considering it a drag. Only start dragging if there's movement beyond a threshold.

```python
def mousePressEvent(self, event):
    """Start dragging on empty areas, let items handle their own clicks."""
    if event.button() == Qt.MouseButton.LeftButton:
        scene_pos = self.mapToScene(event.pos())
        items = self._scene.items(scene_pos)
        
        # Only start dragging if NOT clicking on interactive items
        if not any(isinstance(item, (RecordButtonItem, ToggleLobeItem, SettingsLobeItem)) 
                   for item in items):
            self.is_dragging = True
            self.drag_start_pos = event.globalPosition().toPoint()
            self.widget_start_pos = self.pos()
            event.accept()
        else:
            # Let the item handle the click
            super().mousePressEvent(event)
```

### Option 2: Use mouseReleaseEvent to Distinguish
Store click position in `mousePressEvent`, then check in `mouseReleaseEvent` if mouse moved:
- If no movement → it's a click, don't drag
- If moved → it's a drag, handle snap-to-edge

### Option 3: Don't Call event.accept()
Remove `event.accept()` so events propagate to items:

```python
def mousePressEvent(self, event):
    """Start dragging."""
    if event.button() == Qt.MouseButton.LeftButton:
        self.is_dragging = True
        self.drag_start_pos = event.globalPosition().toPoint()
        self.widget_start_pos = self.pos()
        # Don't call event.accept() - let items also receive the event
```

## Missing Elements
- Click vs drag detection logic (position threshold or time threshold)
- Proper event propagation to child items
- Coordination between drag functionality and click functionality
