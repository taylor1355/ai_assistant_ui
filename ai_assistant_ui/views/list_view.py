"""List view for displaying batches of emails."""
import logging
from textual.widgets import DataTable, Select
from textual.widget import Widget
from textual.reactive import reactive
from textual.geometry import Offset

from ai_assistant_ui.models.action import InboxAction, ActionStatus
from npc.prompts.ai_assistant.email_action_template import EmailDestination
from ai_assistant_ui.models.batch import ActionBatch
from ai_assistant_ui.controllers.email_controller import EmailController
from ai_assistant_ui.views.card_view import EmailCardView

logger = logging.getLogger(__name__)

class EmailListView(Widget):
    """Widget for displaying and managing a list of email actions."""

    BINDINGS = [
        ("space", "toggle_accept", "Accept/Reject"),
        ("enter", "view_details", "View Details"),
        ("e", "edit_destination", "Edit Destination"),
        ("r", "toggle_read", "Toggle Read"),
        ("j", "cursor_down", "Down"),
        ("k", "cursor_up", "Up"),
    ]

    DEFAULT_CSS = """
    EmailListView {
        height: 1fr;
        border: solid $primary;
    }

    EmailListView > DataTable {
        height: 1fr;
        margin: 0 1;
    }

    EmailListView Select {
        width: 30;
        height: auto;
        border: solid $primary;
        background: $surface;
        margin: 1;
    }
    """

    current_batch = reactive[ActionBatch | None](None)

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

    def compose(self):
        """Create child widgets."""
        yield self._table

    def watch_current_batch(self, batch: ActionBatch | None) -> None:
        """React to batch changes."""
        self._refresh_table()

    def _refresh_table(self) -> None:
        """Refresh the table contents."""
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

    def _get_selected_action(self) -> InboxAction | None:
        """Get the currently selected action."""
        if not self.current_batch or self._table.cursor_row is None:
            return None
        return self.current_batch.actions[self._table.cursor_row]

    def action_toggle_accept(self) -> None:
        """Toggle between accepting and rejecting the selected action."""
        action = self._get_selected_action()
        if not action or not action.can_modify:
            return

        new_status = ActionStatus.ACCEPTED if action.status != ActionStatus.ACCEPTED else ActionStatus.REJECTED
        self._controller.modify_action(action, status=new_status)

    def action_view_details(self) -> None:
        """Open the card view for the selected action."""
        action = self._get_selected_action()
        if not action:
            return

        self.app.push_screen(EmailCardView(action, self._controller))

    def action_toggle_read(self) -> None:
        """Toggle read status of the selected action."""
        action = self._get_selected_action()
        if not action or not action.can_modify:
            return
            
        self._controller.modify_action(action, mark_as_read=not action.mark_as_read)

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

    def action_edit_destination(self) -> None:
        """Show destination selection menu."""
        action = self._get_selected_action()
        if not action or not action.can_modify:
            return

        # Create and show destination select popup
        select = Select(
            [(dest.name, dest) for dest in EmailDestination],
            value=action.destination,
            id="destination-select"
        )
        self.mount(select)
        select.focus()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection changes in the destination select."""
        action = self._get_selected_action()
        if action and event.value and event.value != action.destination:
            self._controller.modify_action(action, destination=event.value)
        
            event.select.remove()
            self._table.focus()
