"""Status bar component for displaying application state."""
from textual.widgets import Static
from textual.reactive import reactive

from ai_assistant_ui.models.action import ActionStatus
from ai_assistant_ui.models.batch import ActionBatch, ActionBatchStatus


class StatusBar(Static):
    """Status bar showing batch information and error messages."""

    current_batch = reactive[ActionBatch](None)
    error_message = reactive[str]("")

    STATUS_INDICATORS = {
        ActionBatchStatus.READY: "•",      # Bullet
        ActionBatchStatus.EXECUTING: "⋯",  # Ellipsis
        ActionBatchStatus.COMPLETED: "✓",  # Check mark
        ActionBatchStatus.FAILED: "⚠",     # Warning
        ActionBatchStatus.CANCELED: "✗",   # Cross mark
    }

    def render(self) -> str:
        """Render the status bar content."""
        if self.error_message:
            return f"Error: {self.error_message}"
        
        if not self.current_batch:
            return "No batch selected"

        status_indicator = self.STATUS_INDICATORS[self.current_batch.status]
        
        # Count actions in different states
        total = self.current_batch.size
        pending = self.current_batch.count_actions(ActionStatus.PENDING)
        modified = sum(1 for action in self.current_batch.actions if action.is_modified)
        accepted = self.current_batch.count_actions(ActionStatus.ACCEPTED)
        rejected = self.current_batch.count_actions(ActionStatus.REJECTED)

        return (
            f"Batch: {self.current_batch.id} | "
            f"Status: {status_indicator} {self.current_batch.status.name} | "
            f"Total: {total} | "
            f"Pending: {pending} | "
            f"Modified: {modified} | "
            f"Accepted: {accepted} | "
            f"Rejected: {rejected}"
        )
