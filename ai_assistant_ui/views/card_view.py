"""Email detail view showing full content."""
from textual.screen import ModalScreen
from textual.widgets import Static, Label
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

from ai_assistant_ui.models.action import InboxAction, ActionStatus
from ai_assistant_ui.controllers.email_controller import EmailController
from ai_assistant_ui.views.shortcut_bar import ShortcutBar


class EmailCardView(ModalScreen):
    """Modal screen showing detailed email information."""

    DEFAULT_CSS = """
    EmailCardView {
        align: center middle;
    }

    EmailCardView > Vertical {
        background: $surface;
        border: thick $primary;
        min-width: 80;
        max-width: 120;
        height: 40;
        padding: 1 2;
        layout: grid;
        grid-rows: auto 1fr auto;
    }

    EmailCardView Label {
        width: 15;
        padding: 1 2;
    }

    EmailCardView Static {
        padding: 0 1;
    }

    #header {
        border-bottom: solid $primary;
        padding-bottom: 1;
    }

    #body {
        height: 1fr;
        border: solid $primary;
        margin: 1 0;
        padding: 1;
        overflow-y: auto;
    }

    #footer {
        border-top: solid $primary;
        padding-top: 1;
        height: auto;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("space", "toggle_accept", "Accept/Reject"),
        ("r", "toggle_read", "Toggle Read"),
        ("j", "next_email", "Next Email"),
        ("k", "prev_email", "Previous Email"),
    ]

    STATUS_INDICATORS = {
        ActionStatus.PENDING: "•",    # Bullet
        ActionStatus.ACCEPTED: "✓",   # Check mark
        ActionStatus.REJECTED: "✗",   # Cross mark
        ActionStatus.EXECUTING: "⋯",  # Ellipsis
        ActionStatus.EXECUTED: "✓",   # Check mark
        ActionStatus.FAILED: "⚠",     # Warning
    }

    def __init__(self, action: InboxAction, controller: EmailController):
        super().__init__()
        self.action = action
        self._controller = controller

    def compose(self):
        """Create child widgets."""
        with Vertical(id="dialog"):
            # Header section with metadata
            with Vertical(id="header"):
                with Horizontal():
                    yield Label("Subject:")
                    yield Static(self.action.email.subject, id="subject")
                
                with Horizontal():
                    yield Label("From:")
                    yield Static(self.action.email.sender, id="sender")
                
                with Horizontal():
                    yield Label("Time:")
                    yield Static(
                        self.action.email.timestamp.strftime("%Y-%m-%d %H:%M") 
                        if hasattr(self.action.email, 'timestamp') else "N/A", 
                        id="time"
                    )
                
                with Horizontal():
                    yield Label("Status:")
                    yield Static(
                        f"{self.STATUS_INDICATORS[self.action.status]} {self.action.status.name}",
                        id="status"
                    )
                
                with Horizontal():
                    yield Label("Destination:")
                    yield Static(self.action.destination.name, id="destination")
                
                with Horizontal():
                    yield Label("Read:")
                    yield Static("Yes" if self.action.mark_as_read else "No", id="mark_read")
            
            # Body section with email content
            yield Static(
                "(Placeholder) Email content will be displayed here",
                id="body"
            )
            
            # Footer with shortcuts
            with Vertical(id="footer"):
                yield ShortcutBar()

    def _modify_action(self, **kwargs) -> None:
        """Modify the action and update the view."""
        if not self.action.can_modify:
            return

        self._controller.modify_action(self.action, **kwargs)
        self._update_status()

    def _update_status(self) -> None:
        """Update status displays."""
        self.query_one("#status").update(
            f"{self.STATUS_INDICATORS[self.action.status]} {self.action.status.name}"
        )
        self.query_one("#mark_read").update(
            "Yes" if self.action.mark_as_read else "No"
        )

    def action_toggle_accept(self) -> None:
        """Toggle between accepting and rejecting the action."""
        new_status = ActionStatus.ACCEPTED if self.action.status != ActionStatus.ACCEPTED else ActionStatus.REJECTED
        self._modify_action(status=new_status)

    def action_toggle_read(self) -> None:
        """Toggle read status of the action."""
        self._modify_action(mark_as_read=not self.action.mark_as_read)

    def action_next_email(self) -> None:
        """Navigate to next email."""
        # TODO: Implement navigation between emails
        pass

    def action_prev_email(self) -> None:
        """Navigate to previous email."""
        # TODO: Implement navigation between emails
        pass
