"""Models for email actions and their states."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from npc.apis.gmail_client import Email
from npc.prompts.ai_assistant.email_action_template import EmailDestination

class ActionStatus(Enum):
    """Status of an email action."""
    PENDING = auto()    # Not yet reviewed
    ACCEPTED = auto()   # User accepted the suggestion
    REJECTED = auto()   # User rejected the suggestion
    EXECUTING = auto()  # Action is being executed
    EXECUTED = auto()   # Action has been executed
    FAILED = auto()     # Action execution failed

@dataclass
class InboxAction:
    """Represents an action to be taken on an email."""
    email: Email
    destination: EmailDestination
    mark_as_read: bool = True

    def __post_init__(self) -> None:
        self.status = ActionStatus.PENDING
        self.original_destination = self.destination
        self.original_mark_as_read = self.mark_as_read
        self.modified_at = None
        self.error_message = None

    def accept(self) -> None:
        """Accept the suggested action."""
        if self.can_modify:
            self.status = ActionStatus.ACCEPTED

    def reject(self) -> None:
        """Reject the suggested action."""
        if self.can_modify:
            self.status = ActionStatus.REJECTED

    def toggle_accept(self) -> None:
        """Toggle between accepting and rejecting the action."""
        if self.can_modify:
            if self.status == ActionStatus.ACCEPTED:
                self.status = ActionStatus.REJECTED
            else:
                self.status = ActionStatus.ACCEPTED

    def set_destination(self, new_destination: EmailDestination) -> None:
        """Modify the suggested destination."""
        if self.can_modify and new_destination != self.destination:
            self.destination = new_destination
            self.modified_at = datetime.now()

    def set_read_status(self, mark_as_read: bool) -> None:
        """Set whether the email should be marked as read."""
        if self.can_modify and mark_as_read != self.mark_as_read:
            self.mark_as_read = mark_as_read
            self.modified_at = datetime.now()

    def toggle_read_status(self) -> None:
        """Toggle whether the email should be marked as read."""
        self.set_read_status(not self.mark_as_read)

    def set_executing(self) -> None:
        """Mark the action as being executed."""
        self.status = ActionStatus.EXECUTING

    def set_executed(self) -> None:
        """Mark the action as executed."""
        self.status = ActionStatus.EXECUTED

    def set_failed(self, error: str) -> None:
        """Mark the action as failed with an error message."""
        self.status = ActionStatus.FAILED
        self.error_message = error

    @property
    def is_modified(self) -> bool:
        """Check whether the action has been modified since being created."""
        return (
            self.destination != self.original_destination or
            self.mark_as_read != self.original_mark_as_read
        )

    @property
    def can_modify(self) -> bool:
        """Check if the action can be modified."""
        return self.status in (ActionStatus.PENDING, ActionStatus.ACCEPTED, ActionStatus.REJECTED)

    @property
    def can_execute(self) -> bool:
        """Check if the action can be executed."""
        return self.status == ActionStatus.ACCEPTED

    @property
    def needs_review(self) -> bool:
        """Check if the action needs user review."""
        return self.status == ActionStatus.PENDING
