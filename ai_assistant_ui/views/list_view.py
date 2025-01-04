"""List view for displaying batches of emails."""
import logging
from textual.widgets import DataTable
from textual.widget import Widget
from textual.reactive import reactive
from textual.geometry import Offset
from textual.containers import Container

from ai_assistant_ui.models.action import InboxAction, ActionStatus
from npc.prompts.ai_assistant.email_action_template import EmailDestination
from ai_assistant_ui.models.batch import ActionBatch
from ai_assistant_ui.controllers.email_controller import EmailController
from ai_assistant_ui.views.card_view import EmailCardView
from ai_assistant_ui.views.shortcut_bar import ShortcutBar, EditMode

logger = logging.getLogger(__name__)

class EmailListView(Widget):
    """Widget for displaying and managing a list of email actions."""

    BINDINGS = [
        ("space", "toggle_accept", "Accept/Reject"),
        ("enter", "view_details", "View Details"),
        ("e", "toggle_edit_mode", "Edit Destination"),
        ("r", "toggle_read", "Toggle Read"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
        # Destination shortcuts - only active in edit mode
        ("n", "move_to_newsletter", "Move to Newsletter"),
        ("b", "move_to_business", "Move to Business"),
        ("a", "move_to_archive", "Move to Archive"),
        ("d", "move_to_delete", "Move to Delete"),
        ("i", "move_to_inbox", "Move to Inbox"),
    ]

    DEFAULT_CSS = """
    EmailListView {
        height: 1fr;
        border: solid $primary;
        layout: grid;
        grid-rows: 1fr auto;
    }

    EmailListView DataTable {
        height: 1fr;
        margin: 0 1;
    }

    EmailListView ShortcutBar {
        width: 100%;
        content-align: center bottom;
        padding: 0 1;
        border-top: solid $primary;
    }
    """

    current_batch = reactive[ActionBatch | None](None)
    edit_mode = reactive[EditMode](EditMode.NORMAL)

    def __init__(
        self,
        email_batch: ActionBatch | None,
        controller: EmailController,
    ):
        """Initialize the list view.
        
        Args:
            email_batch: Batch of email actions to display
            controller: Email controller for managing actions
        """
        super().__init__()
        self._controller = controller
        self._table = DataTable()
        self._table.cursor_type = "row"
        self.current_batch = email_batch
        
        # Register for batch updates
        if controller:
            controller.add_batch_updated_callback(self._on_batch_updated)

    def _on_batch_updated(self, batch: ActionBatch) -> None:
        """Handle batch updates from the controller."""
        self.current_batch = batch

    def on_mount(self) -> None:
        """Set up the table when the widget is mounted."""
        self._table.focus()
        self._table.add_columns(
            "Status",
            "Subject",
            "From",
            "Time",
            "Read"
        )
        self._refresh_table()
        # Just select first row, don't try to manage focus
        if self.current_batch and self.current_batch.actions:
            self._table.move_cursor(row=0)
            logger.debug(f"ListView initial cursor set to row 0, cursor_row={self._table.cursor_row}")
            logger.debug(f"App focused widget after cursor set: {self.app.focused.__class__.__name__ if self.app.focused else None}")

    def compose(self):
        """Create child widgets."""
        yield self._table
        yield ShortcutBar()

    def watch_current_batch(self, batch: ActionBatch | None) -> None:
        """React to batch changes."""
        logger.debug(f"App focused widget before batch change: {self.app.focused.__class__.__name__ if self.app.focused else None}")
        self._refresh_table()
        # Always ensure a row is selected
        if batch and batch.actions:
            if self._table.cursor_row is None or self._table.cursor_row >= len(batch.actions):
                self._table.move_cursor(row=0)
        logger.debug(f"App focused widget after batch change: {self.app.focused.__class__.__name__ if self.app.focused else None}")

    def _refresh_table(self) -> None:
        """Refresh the table contents."""
        # Store current cursor position
        current_row = self._table.cursor_row

        self._table.clear()
        if not self.current_batch:
            return

        for action in self.current_batch.actions:
            status_indicators = {
                ActionStatus.PENDING: "•",    # Bullet
                ActionStatus.ACCEPTED: "✓",   # Check mark
                ActionStatus.REJECTED: "✗",   # Cross mark
                ActionStatus.EXECUTING: "⋯",  # Ellipsis
                ActionStatus.EXECUTED: "✓",   # Check mark
                ActionStatus.FAILED: "⚠",     # Warning
            }
            
            self._table.add_row(
                f"{status_indicators[action.status]} {action.status.name}",
                action.email.subject,
                action.email.sender,
                action.email.timestamp.strftime("%Y-%m-%d %H:%M") if hasattr(action.email, 'timestamp') else "N/A",
                "Yes" if action.mark_as_read else "No",
            )
            
        # Restore cursor position if it was set and within valid range
        if current_row is not None and current_row < len(self.current_batch.actions):
            self._table.move_cursor(row=current_row)

    def _get_selected_action(self) -> InboxAction | None:
        """Get the currently selected action."""
        if not self.current_batch or self._table.cursor_row is None:
            return None
        return self.current_batch.actions[self._table.cursor_row]

    def _modify_action(self, action: InboxAction, **kwargs) -> None:
        """Modify an action and refresh the view."""
        if not action or not action.can_modify:
            return

        self._controller.modify_action(action, **kwargs)
        self._refresh_table()

    def action_toggle_accept(self) -> None:
        """Toggle between accepting and rejecting the selected action."""
        action = self._get_selected_action()
        if not action:
            return

        new_status = ActionStatus.ACCEPTED if action.status != ActionStatus.ACCEPTED else ActionStatus.REJECTED
        self._modify_action(action, status=new_status)

    def action_view_details(self) -> None:
        """Open the card view for the selected action."""
        action = self._get_selected_action()
        if not action:
            return

        self.app.push_screen(EmailCardView(action, self._controller))

    def action_toggle_read(self) -> None:
        """Toggle read status of the selected action."""
        action = self._get_selected_action()
        if not action:
            return
            
        self._modify_action(action, mark_as_read=not action.mark_as_read)

    def action_cursor_down(self) -> None:
        """Move cursor down one row."""
        if not self.current_batch:
            return
        if self._table.cursor_row is None:
            self._table.move_cursor(row=0)
        else:
            next_row = min(self._table.cursor_row + 1, len(self.current_batch.actions) - 1)
            self._table.move_cursor(row=next_row)

    def action_cursor_up(self) -> None:
        """Move cursor up one row."""
        if not self.current_batch:
            return
        if self._table.cursor_row is None:
            self._table.move_cursor(row=0)
        else:
            prev_row = max(self._table.cursor_row - 1, 0)
            self._table.move_cursor(row=prev_row)

    def action_toggle_edit_mode(self) -> None:
        """Toggle destination edit mode."""
        if self.edit_mode == EditMode.NORMAL:
            self.edit_mode = EditMode.DESTINATION
        else:
            self.edit_mode = EditMode.NORMAL
        
        # Update shortcut bar
        shortcut_bar = self.query_one(ShortcutBar)
        shortcut_bar.edit_mode = self.edit_mode

    def _move_to_destination(self, destination: EmailDestination) -> None:
        """Move selected email to specified destination."""
        action = self._get_selected_action()
        if not action:
            return

        self._modify_action(action, destination=destination)
        self.edit_mode = EditMode.NORMAL
        
        # Update shortcut bar
        shortcut_bar = self.query_one(ShortcutBar)
        shortcut_bar.edit_mode = self.edit_mode

    def action_move_to_newsletter(self) -> None:
        """Move email to newsletter destination."""
        if self.edit_mode == EditMode.DESTINATION:
            self._move_to_destination(EmailDestination.NEWSLETTER)

    def action_move_to_business(self) -> None:
        """Move email to business destination."""
        if self.edit_mode == EditMode.DESTINATION:
            self._move_to_destination(EmailDestination.BUSINESS_TRANSACTION)

    def action_move_to_archive(self) -> None:
        """Move email to archive destination."""
        if self.edit_mode == EditMode.DESTINATION:
            self._move_to_destination(EmailDestination.ARCHIVE)

    def action_move_to_delete(self) -> None:
        """Move email to delete destination."""
        if self.edit_mode == EditMode.DESTINATION:
            self._move_to_destination(EmailDestination.DELETE)

    def action_move_to_inbox(self) -> None:
        """Move email to inbox destination."""
        if self.edit_mode == EditMode.DESTINATION:
            self._move_to_destination(EmailDestination.INBOX)
