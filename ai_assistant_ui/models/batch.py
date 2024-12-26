"""Models for managing groups of related actions."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Awaitable, Callable, Optional

from ai_assistant_ui.models.action import InboxAction, ActionStatus
from npc.apis.gmail_client import Email, GmailThread
from npc.prompts.ai_assistant.email_action_template import EmailDestination


class ActionBatchStatus(Enum):
    READY = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELED = auto()


@dataclass
class ActionBatch:
    """A group of related email actions."""
    id: str
    actions: list[InboxAction]
    created_at: datetime = field(default_factory=datetime.now)
    status: ActionBatchStatus = ActionBatchStatus.READY
    error_message: Optional[str] = None

    def count_actions(self, status: ActionStatus) -> int:
        """Count the number of actions with a given status."""
        return sum(1 for action in self.actions if action.status == status)

    def set_status(self, status: ActionBatchStatus) -> None:
        """Set the batch status."""
        self.status = status

    @property
    def size(self) -> int:
        """Get the number of actions in the batch."""
        return len(self.actions)

    @property
    def is_complete(self) -> bool:
        """Check if all actions have been reviewed."""
        return self.count_actions(ActionStatus.PENDING) == 0

    @property
    def can_execute(self) -> bool:
        """Check if the batch can be executed."""
        return (
            self.status == ActionBatchStatus.READY and
            any(action.can_execute for action in self.actions)
        )


    @classmethod
    async def from_email_threads(cls, 
                               threads: list[tuple[Email, GmailThread]], 
                               action_suggestion_fn: Callable[[Email, GmailThread], Awaitable[InboxAction]],
                               batch_id: str) -> 'ActionBatch':
        """Create a new batch from email threads using a suggestion function."""
        actions = []
        for email, thread in threads:
            suggestion = await action_suggestion_fn(email, thread)
            action = InboxAction(
                email=email,
                destination=suggestion.destination,
                mark_as_read=suggestion.mark_as_read
            )
            action.status = suggestion.status
            actions.append(action)
            
        return cls(
            id=batch_id,
            actions=actions,
            status=ActionBatchStatus.READY
        )

def group_by_destination(actions: list[InboxAction]) -> dict[EmailDestination, ActionBatch]:
    """Group actions into batches based on their destination."""
    batches = {dest: [] for dest in EmailDestination}
    for action in actions:
        batches[action.destination].append(action)
    
    return {
        dest: ActionBatch(
            id=dest.name.lower(),
            actions=dest_actions,
            status=ActionBatchStatus.READY
        )
        for dest, dest_actions in batches.items()
    }
