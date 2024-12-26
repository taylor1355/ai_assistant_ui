"""Unified controller for all email operations."""
from typing import Optional, Callable, List, Tuple
from copy import deepcopy
import logging

from ai_assistant_ui.models.batch import ActionBatch, ActionBatchStatus
from ai_assistant_ui.models.action import InboxAction, ActionStatus
from ai_assistant_ui.models.state import AppState
from ai_assistant_ui.models.gmail import GmailWrapper
from npc.apis.gmail_client import Email, GmailThread
from npc.simulators.ai_assistant.tools.inbox_manager import Status as NpcStatus
from npc.prompts.ai_assistant.email_action_template import EmailDestination

logger = logging.getLogger(__name__)

def _convert_npc_status_to_action_status(status: NpcStatus) -> ActionStatus:
    """Convert NPC Status to ActionStatus."""
    status_mapping = {
        NpcStatus.NOT_STARTED: ActionStatus.PENDING,
        NpcStatus.IN_PROGRESS: ActionStatus.EXECUTING,
        NpcStatus.SUCCEEDED: ActionStatus.EXECUTED,
        NpcStatus.FAILED: ActionStatus.FAILED,
        NpcStatus.CANCELED: ActionStatus.REJECTED
    }
    return status_mapping.get(status, ActionStatus.PENDING)

class EmailController:
    """Unified controller for email operations."""

    # Callback type definitions
    BatchUpdateCallback = Callable[[ActionBatch], None]

    def __init__(self, gmail: GmailWrapper, state: AppState):
        """Initialize the controller."""
        self.gmail = gmail
        self.state = state
        self._error_message: Optional[str] = None
        self._batch_callbacks: list[EmailController.BatchUpdateCallback] = []
        logger.info("EmailController initialized")

    @property
    def error_message(self) -> Optional[str]:
        """Get the current error message."""
        return self._error_message

    def add_batch_updated_callback(self, callback: BatchUpdateCallback) -> None:
        """Register a callback for batch updates.
        
        The callback will be invoked whenever a batch's state changes,
        with the updated batch as the argument.
        """
        if callback not in self._batch_callbacks:
            self._batch_callbacks.append(callback)
            logger.debug(f"Registered batch update callback (total: {len(self._batch_callbacks)})")

    def remove_batch_updated_callback(self, callback: BatchUpdateCallback) -> None:
        """Unregister a batch update callback."""
        if callback in self._batch_callbacks:
            self._batch_callbacks.remove(callback)
            logger.debug(f"Unregistered batch update callback (remaining: {len(self._batch_callbacks)})")
        else:
            logger.warning("Attempted to remove non-existent callback")

    def _notify_batch_updated(self) -> None:
        """Notify registered callbacks of batch updates."""
        if not self.state.current_batch:
            return
            
        batch = self.state.current_batch
        logger.debug(f"Notifying {len(self._batch_callbacks)} callbacks of update to batch {batch.id}")
        
        for callback in self._batch_callbacks:
            try:
                callback(batch)
            except Exception as e:
                logger.error(f"Error in batch update callback: {e}", exc_info=True)

    # Action Operations

    def _update_batch_reference(self, batch: ActionBatch) -> ActionBatch:
        """Create new batch reference to trigger reactive update."""
        updated_batch = ActionBatch(
            id=batch.id,
            actions=batch.actions.copy(),
            status=batch.status
        )
        self.state.batches[batch.id] = updated_batch
        if self.state.current_batch and self.state.current_batch.id == batch.id:
            self.state.current_batch = updated_batch
        return updated_batch

    def _change_action_destination(self, 
                                 action: InboxAction, 
                                 destination: EmailDestination) -> None:
        """Move action to a new destination batch."""
        if not self.state.current_batch:
            logger.error("No current batch while changing action destination")
            return
            
        # Remove from current batch
        current_batch = self.state.current_batch
        current_batch.actions.remove(action)
        self._update_batch_reference(current_batch)
        
        # Add to destination batch
        dest_batch = self.state.batches[destination.name.lower()]
        action.set_destination(destination)
        dest_batch.actions.append(action)
        
        # Notify of updates
        self._notify_batch_updated()

    def _update_action_state(self, action: InboxAction, 
                           destination: Optional[EmailDestination] = None,
                           mark_as_read: Optional[bool] = None,
                           status: Optional[ActionStatus] = None) -> None:
        """Update an action's state."""
        if destination is not None and destination != action.destination:
            self._change_action_destination(action, destination)
        if mark_as_read is not None:
            action.set_read_status(mark_as_read)
        if status is not None:
            status_updates = {
                ActionStatus.ACCEPTED: action.accept,
                ActionStatus.REJECTED: action.reject,
            }
            if update_func := status_updates.get(status):
                update_func()

    def modify_action(self, action: InboxAction, 
                     destination: Optional[EmailDestination] = None,
                     mark_as_read: Optional[bool] = None,
                     status: Optional[ActionStatus] = None) -> None:
        """Modify an action's properties."""
        # Validate modification
        if not action.can_modify or not self.state.current_batch:
            logger.warning(
                f"Cannot modify action {action.email.id}: "
                f"can_modify={action.can_modify}, "
                f"has_current_batch={bool(self.state.current_batch)}"
            )
            self._error_message = "Cannot modify action in current state"
            return

        try:
            # Record state for history
            action_before = deepcopy(action)
            
            # Apply changes
            self._update_action_state(action, destination, mark_as_read, status)
            
            # Record in history
            self.state.record_action_change(
                action_before,
                deepcopy(action),
                self.state.current_batch.id
            )
            
        except Exception as e:
            logger.exception(f"Failed to modify action {action.email.id}")
            self._error_message = f"Failed to modify action: {str(e)}"

    async def execute_action(self, action: InboxAction) -> bool:
        """Execute a single action."""
        if not action.can_execute:
            self._error_message = "Action cannot be executed in current state"
            return False

        action.set_executing()

        try:
            # Execute through Gmail wrapper
            await self.gmail.execute_action(
                action.email.thread_id,
                action.destination,
                action.mark_as_read
            )
            action.set_executed()
            return True

        except Exception as e:
            action.set_failed(str(e))
            self._error_message = f"Failed to execute action: {str(e)}"
            return False

    # Batch Operations

    async def create_batch(self, email_threads: List[Tuple[Email, GmailThread]]) -> Optional[ActionBatch]:
        """Create a new batch from email threads."""
        if not email_threads:
            logger.warning("No email threads provided")
            return None

        try:
            batch = await ActionBatch.from_email_threads(
                threads=email_threads,
                action_suggestion_fn=self.gmail.suggest_action,
                batch_id=f"batch_{len(self.state.batches) + 1}"
            )
            
            self.state.set_current_batch(batch)
            self._notify_batch_updated()
            logger.info(f"Created batch {batch.id} with {len(batch.actions)} actions")
            
            return batch

        except Exception as e:
            logger.exception("Failed to create batch")
            self._error_message = f"Failed to create batch: {str(e)}"
            return None

    def _update_batch_status(self, batch: ActionBatch, status: ActionBatchStatus, message: str) -> None:
        """Update batch status and notify listeners."""
        batch.set_status(status)
        if status == ActionBatchStatus.FAILED:
            logger.error(f"Batch {batch.id}: {message}")
            self._error_message = message
        else:
            logger.info(f"Batch {batch.id}: {message}")
        self._notify_batch_updated()

    async def execute_batch(self, batch: ActionBatch) -> bool:
        """Execute all executable actions in a batch."""
        if not batch.can_execute:
            self._update_batch_status(
                batch, 
                ActionBatchStatus.FAILED,
                "Batch cannot be executed in current state"
            )
            return False

        # Start execution
        self._update_batch_status(
            batch,
            ActionBatchStatus.EXECUTING,
            "Starting batch execution"
        )

        try:
            # Execute each action
            failed = 0
            for action in batch.actions:
                if action.can_execute:
                    logger.debug(f"Executing action for email: {action.email.subject}")
                    if not await self.execute_action(action):
                        failed += 1

            # Update final status
            success = failed == 0
            self._update_batch_status(
                batch,
                ActionBatchStatus.COMPLETED if success else ActionBatchStatus.FAILED,
                f"Execution complete: {failed} actions failed" if failed else "Execution successful"
            )
            return success

        except Exception as e:
            self._update_batch_status(
                batch,
                ActionBatchStatus.FAILED,
                f"Batch execution failed: {str(e)}"
            )
            return False

    async def execute_current_batch(self) -> bool:
        """Execute the current batch."""
        if not self.state.current_batch:
            logger.warning("No current batch to execute")
            self._error_message = "No current batch to execute"
            return False
            
        return await self.execute_batch(self.state.current_batch)

    # History Operations
    def undo(self) -> bool:
        """Undo the last action modification."""
        if not self.state.can_undo():
            logger.debug("No actions to undo")
            return False

        success = self.state.undo()
        if success:
            logger.info("Undid last action")
            self._notify_batch_updated()
        return success

    def redo(self) -> bool:
        """Redo the last undone action modification."""
        if not self.state.can_redo():
            logger.debug("No actions to redo")
            return False

        success = self.state.redo()
        if success:
            logger.info("Redid last action")
            self._notify_batch_updated()
        return success

    # Batch State Operations

    # Batch state operations
    def select_batch(self, batch: ActionBatch) -> None:
        """Select a batch as the current batch and notify listeners."""
        logger.info(f"Selecting batch {batch.id} with {len(batch.actions)} actions")
        self.state.set_current_batch(batch)
        self._notify_batch_updated()

    def get_current_batch_summary(self) -> dict[str, Optional[int | ActionBatchStatus]]:
        """Get a summary of the current batch state."""
        if not self.state.current_batch:
            return {
                'status': None,
                'total': 0,
                'pending': 0,
                'accepted': 0,
                'rejected': 0,
                'executed': 0,
                'failed': 0,
                'modified': 0
            }

        batch = self.state.current_batch
        summary = {
            'status': batch.status,
            'total': batch.size,
            'pending': batch.count_actions(ActionStatus.PENDING),
            'accepted': batch.count_actions(ActionStatus.ACCEPTED),
            'rejected': batch.count_actions(ActionStatus.REJECTED),
            'executed': batch.count_actions(ActionStatus.EXECUTED),
            'failed': batch.count_actions(ActionStatus.FAILED),
            'modified': sum(1 for action in batch.actions if action.is_modified)
        }
        logger.debug(f"Batch {batch.id} summary: {summary}")
        return summary
