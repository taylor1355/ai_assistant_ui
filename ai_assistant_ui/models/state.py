"""Global application state management."""
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ai_assistant_ui.models.action import InboxAction, ActionStatus
from ai_assistant_ui.models.batch import ActionBatch, ActionBatchStatus


@dataclass
class ActionHistoryEntry:
    """Represents a change in an action's state."""
    action_before: InboxAction
    action_after: InboxAction
    batch_id: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AppState:
    """Global application state."""
    current_batch: Optional[ActionBatch] = None
    history: deque[ActionHistoryEntry] = field(default_factory=lambda: deque(maxlen=10))
    redo_stack: deque[ActionHistoryEntry] = field(default_factory=deque)
    batches: dict[str, ActionBatch] = field(default_factory=dict)
    
    def set_current_batch(self, batch: ActionBatch) -> None:
        """Set the current batch being processed."""
        self.current_batch = batch
        self.batches[batch.id] = batch
        # Clear redo stack when starting new batch
        self.redo_stack.clear()

    def record_action_change(self, 
                           before: InboxAction, 
                           after: InboxAction, 
                           batch_id: str) -> None:
        """Record a change in action state for undo/redo."""
        entry = ActionHistoryEntry(
            action_before=before,
            action_after=after,
            batch_id=batch_id
        )
        self.history.append(entry)
        # Clear redo stack when new action is recorded
        self.redo_stack.clear()

    def can_undo(self) -> bool:
        """Check if there are actions that can be undone."""
        return len(self.history) > 0

    def can_redo(self) -> bool:
        """Check if there are actions that can be redone."""
        return len(self.redo_stack) > 0

    def undo(self) -> Optional[ActionHistoryEntry]:
        """Undo the last action change."""
        if not self.can_undo():
            return None
        
        entry = self.history.pop()
        self.redo_stack.append(entry)
        return entry

    def redo(self) -> Optional[ActionHistoryEntry]:
        """Redo the last undone action change."""
        if not self.can_redo():
            return None
        
        entry = self.redo_stack.pop()
        self.history.append(entry)
        return entry

    def get_batch_by_id(self, batch_id: str) -> Optional[ActionBatch]:
        """Get a batch by its ID."""
        return self.batches.get(batch_id)

    def get_batches_by_status(self, status: ActionBatchStatus) -> list[ActionBatch]:
        """Get all batches with the given status."""
        return [batch for batch in self.batches.values() 
                if batch.status == status]

    def get_actions_by_status(self, status: ActionStatus) -> list[InboxAction]:
        """Get all actions with the given status across all batches."""
        actions = []
        for batch in self.batches.values():
            actions.extend([action for action in batch.actions 
                          if action.status == status])
        return actions
