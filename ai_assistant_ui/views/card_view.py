"""Detailed single email card view."""
from textual.screen import ModalScreen
from textual.widgets import Static, Label, Select
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

from ai_assistant_ui.models.action import InboxAction, ActionStatus
from ai_assistant_ui.controllers.email_controller import EmailController
from npc.prompts.ai_assistant.email_action_template import EmailDestination


class EmailCardView(ModalScreen):
    """Modal screen showing detailed email information."""

    DEFAULT_CSS = """
    EmailCardView {
        align: center middle;
    }

    EmailCardView > Vertical {
        background: $surface;
        border: thick $primary;
        min-width: 60;
        max-width: 100;
        max-height: 40;
        padding: 1 2;
    }

    EmailCardView Label {
        width: 15;
        padding: 1 2;
    }

    EmailCardView Static {
        padding: 0 1;
    }

    EmailCardView Select {
        width: 30;
    }

    #body {
        height: 1fr;
        min-height: 10;
        border: solid $primary;
        padding: 1;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("space", "toggle_accept", "Accept/Reject"),
        ("e", "edit_destination", "Edit"),
        ("r", "toggle_read", "Toggle Read"),
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
                yield Select(
                    [(dest.name, dest) for dest in EmailDestination],
                    value=self.action.destination.name,
                    id="destination"
                )
            
            with Horizontal():
                yield Label("Mark as Read:")
                yield Select(
                    [("Yes", True), ("No", False)],
                    value=str(self.action.mark_as_read),
                    id="mark_read"
                )
            
            yield Static(
                self.action.email.body,
                id="body"
            )

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle changes to select widgets."""
        if not self.action.can_modify:
            return

        if event.select.id == "destination":
            self._controller.modify_action(
                self.action,
                destination=EmailDestination[event.value]
            )
            self.query_one("#status").update(
                f"{self.STATUS_INDICATORS[self.action.status]} {self.action.status.name}"
            )
        elif event.select.id == "mark_read":
            self._controller.modify_action(
                self.action,
                mark_as_read=(event.value == "True")
            )
            self.query_one("#status").update(
                f"{self.STATUS_INDICATORS[self.action.status]} {self.action.status.name}"
            )

    def action_toggle_accept(self) -> None:
        """Toggle between accepting and rejecting the action."""
        if not self.action.can_modify:
            return

        new_status = ActionStatus.ACCEPTED if self.action.status != ActionStatus.ACCEPTED else ActionStatus.REJECTED
        self._controller.modify_action(self.action, status=new_status)
        self.query_one("#status").update(
            f"{self.STATUS_INDICATORS[self.action.status]} {self.action.status.name}"
        )

    def action_toggle_read(self) -> None:
        """Toggle read status of the action."""
        if not self.action.can_modify:
            return

        self._controller.modify_action(self.action, mark_as_read=not self.action.mark_as_read)
        self.query_one("#mark_read").value = str(self.action.mark_as_read)
        self.query_one("#status").update(
            f"{self.STATUS_INDICATORS[self.action.status]} {self.action.status.name}"
        )
