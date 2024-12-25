"""Models for managing groups of related actions."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Optional

from ai_assistant_ui.models.action import InboxAction, ActionStatus
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


def batch_by_destination(actions: list[InboxAction]) -> dict[EmailDestination, ActionBatch]:
    """Organize a list of InboxActions into batches based on suggested destination."""
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
