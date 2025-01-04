"""Shortcut bar component for displaying available keyboard shortcuts."""
from textual.widgets import Static
from textual.reactive import reactive
from enum import Enum

class EditMode(Enum):
    """Edit mode states."""
    NORMAL = "normal"
    DESTINATION = "destination"

class ShortcutBar(Static):
    """Status bar showing available keyboard shortcuts."""

    edit_mode = reactive[EditMode](EditMode.NORMAL)

    def render(self) -> str:
        """Render the shortcut bar content."""
        if self.edit_mode == EditMode.DESTINATION:
            return "(n)ewsletter  (b)usiness  (a)rchive  (d)elete  (i)nbox  e: Cancel"
        
        return "j/k: Navigate  Space: Accept/Reject  e: Edit  r: Read/Unread  Enter: View"
