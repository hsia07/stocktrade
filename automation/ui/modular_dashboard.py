"""
R026: Modular Trading Interface - Dashboard Component

Provides modular dashboard UI for trading interface.
R026 scope ONLY: UI component, NO runtime trading logic.
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class DashboardWidget:
    """Represents a dashboard widget."""
    id: str
    widget_type: str
    position: Dict[str, int]
    config: Dict[str, Any]


class ModularDashboard:
    """Modular dashboard for trading interface."""

    def __init__(self, layout: str = "default"):
        self.layout = layout
        self.widgets: List[DashboardWidget] = []
        self.blueprint_linked: bool = False

    def add_widget(self, widget_id: str, widget_type: str, position: Dict[str, int], config: Dict[str, Any]) -> DashboardWidget:
        """Add a widget to the dashboard."""
        widget = DashboardWidget(
            id=widget_id,
            widget_type=widget_type,
            position=position,
            config=config
        )
        self.widgets.append(widget)
        return widget

    def remove_widget(self, widget_id: str) -> bool:
        """Remove a widget by id."""
        initial_count = len(self.widgets)
        self.widgets = [w for w in self.widgets if w.id != widget_id]
        return len(self.widgets) < initial_count

    def link_to_blueprint(self, blueprint_path: str) -> bool:
        """Link dashboard to blueprint layout."""
        self.blueprint_linked = True
        return True

    def get_widgets(self) -> List[DashboardWidget]:
        """Get all widgets."""
        return self.widgets

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for UI rendering."""
        return {
            "layout": self.layout,
            "widgets": [
                {
                    "id": w.id,
                    "type": w.widget_type,
                    "position": w.position,
                    "config": w.config
                }
                for w in self.widgets
            ],
            "blueprint_linked": self.blueprint_linked
        }
