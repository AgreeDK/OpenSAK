"""
src/opensak/gui/map_popout.py — Floating pop-out window for the map.

Hosts the MapWidget in its own top-level window so the user can resize it
freely or move it to a second monitor.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QWidget

from opensak.gui.settings import get_settings
from opensak.lang import tr


class MapPopoutWindow(QMainWindow):
    """Independent window that hosts the MapWidget when popped out."""

    closed = Signal()  # emitted when the user closes the pop-out window

    def __init__(self, parent=None):
        # Use Qt.Window flag so it behaves as an independent window while
        # still grouping with the parent in the taskbar on Windows.
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(tr("map_popout_title"))
        self.setMinimumSize(500, 400)
        self._central = QWidget()
        self._layout = QVBoxLayout(self._central)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self._central)
        self._restore_geometry()

    def take_widget(self, widget: QWidget) -> None:
        """Reparent a widget into this pop-out window."""
        self._layout.addWidget(widget)
        widget.show()

    def save_geometry_to_settings(self) -> None:
        """Persist current geometry to settings (base64 string)."""
        s = get_settings()
        s.map_popout_geometry = self.saveGeometry().toBase64().data().decode("ascii")

    def _restore_geometry(self) -> None:
        from PySide6.QtCore import QByteArray
        s = get_settings()
        geo = s.map_popout_geometry
        if geo:
            if isinstance(geo, (bytes, bytearray, QByteArray)):
                self.restoreGeometry(geo)
            else:
                self.restoreGeometry(QByteArray.fromBase64(geo.encode("ascii")))
        else:
            self.resize(900, 700)

    def closeEvent(self, event) -> None:
        self.closed.emit()
        event.accept()
