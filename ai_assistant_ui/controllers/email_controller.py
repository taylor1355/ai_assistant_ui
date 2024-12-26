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

    def __init__(self, gmail: GmailWrapper, state: AppState):
        """Initialize the controller."""
        self.gmail = gmail
        self.state = state
        self._error_message: Optional[str] = None
        self._batch_updated_callbacks: list[Callable[[ActionBatch], None]] = []
        logger.info("EmailController initialized")

    @property
    def error_message(self) -> Optional[str]:
        """Get the current error message."""
        return self._error_message

    def add_batch_updated_callback(self, callback: Callable[[ActionBatch], None]) -> None:
        """Add a callback for batch updates."""
        if callback not in self._batch_updated_callbacks:
            self._batch_updated_callbacks.append(callback)
            logger.debug("Added batch update callback")

    def remove_batch_updated_callback(self, callback: Callable[[ActionBatch], None]) -> None:
        """Remove a callback for batch updates."""
        if callback in self._batch_updated_callbacks:
            self._batch_updated_callbacks.remove(callback)
            logger.debug("Removed batch update callback")

    def _notify_batch_updated(self) -> None:
        """Notify listeners of batch updates."""
        if self.state.current_batch:
            logger.debug(f"Notifying {len(self._batch_updated_callbacks)} listeners of batch update for {self.state.current_batch.id}")
            for callback in self._batch_updated_callbacks:
                callback(self.state.current_batch)

    # Action Operations

    def modify_action(self, action: InboxAction, 
                     destination: Optional[EmailDestination] = None,
                     mark_as_read: Optional[bool] = None,
                     status: Optional[ActionStatus] = None) -> None:
        """Modify an action's properties."""
        if not action.can_modify or not self.state.current_batch:
            self._error_message = "Cannot modify action in current state"
            return

        # Create copies for history
        action_before = deepcopy(action)
        
        # Handle destination change
        if destination is not None and destination != action.destination:
            # Remove action from current batch
            current_batch = self.state.current_batch
            current_batch.actions.remove(action)
            
            # Create new batch reference to trigger reactive update
            updated_batch = ActionBatch(
                id=current_batch.id,
                actions=current_batch.actions.copy(),
                status=current_batch.status
            )
            self.state.batches[current_batch.id] = updated_batch
            if self.state.current_batch.id == current_batch.id:
                self.state.current_batch = updated_batch
            
            # Get batch for new destination and add action
            dest_batch = self.state.batches[destination.name.lower()]
            action.set_destination(destination)
            dest_batch.actions.append(action)
            
            # Notify tabs to update
            self._notify_batch_updated()
            
        # Apply other modifications
        if mark_as_read is not None:
            action.set_read_status(mark_as_read)
        if status is not None:
            if status == ActionStatus.ACCEPTED:
                action.accept()
            elif status == ActionStatus.REJECTED:
                action.reject()

        # Record change in history
        self.state.record_action_change(
            action_before,
            deepcopy(action),
            self.state.current_batch.id
        )

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

    async def load_batch(self, email_threads: List[Tuple[Email, GmailThread]]) -> Optional[ActionBatch]:
        """Create a new batch from the provided email threads."""
        try:
            if not email_threads:
                logger.warning("No email threads provided to load_batch")
                return None

            logger.info(f"Creating batch from {len(email_threads)} email threads")
            
            # Create actions for each email
            actions = []
            for i, (email, thread) in enumerate(email_threads, 1):
                try:
                    logger.debug(f"Processing email {i}/{len(email_threads)}: {email.subject}")
                    # Create action with suggested destination
                    npc_action = await self.gmail.suggest_action(email, thread)
                    action = InboxAction(
                        email=email,
                        destination=npc_action.destination,
                        mark_as_read=npc_action.mark_as_read
                    )
                    action.status = _convert_npc_status_to_action_status(npc_action.status)
                    actions.append(action)
                    logger.debug(f"Created action with destination: {action.destination}")
                except Exception as e:
                    logger.error(f"Error creating action for email {email.subject}: {str(e)}", exc_info=True)
                    raise

            logger.info(f"Successfully created {len(actions)} actions")

            # Create new batch
            batch = ActionBatch(
                id=f"batch_{len(self.state.batches) + 1}",
                actions=actions,
                status=ActionBatchStatus.READY
            )
            logger.info(f"Created new batch {batch.id}")

            # Update state
            self.state.set_current_batch(batch)
            self._notify_batch_updated()
            
            return batch

        except Exception as e:
            error_msg = f"Failed to load batch: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._error_message = error_msg
            return None

    async def execute_batch(self, batch: ActionBatch) -> bool:
        """Execute all accepted actions in a batch."""
        if not batch.can_execute:
            error_msg = "Batch cannot be executed in current state"
            logger.warning(f"{error_msg} (batch {batch.id})")
            self._error_message = error_msg
            return False

        logger.info(f"Starting execution of batch {batch.id}")
        batch.set_status(ActionBatchStatus.EXECUTING)
        success = True

        try:
            # Execute each accepted action
            for action in batch.actions:
                if action.can_execute:
                    logger.debug(f"Executing action for email: {action.email.subject}")
                    if not await self.execute_action(action):
                        logger.error(f"Failed to execute action for email: {action.email.subject}")
                        success = False

            # Update batch status based on results
            if not success:
                logger.warning(f"Batch {batch.id} execution failed")
                batch.set_status(ActionBatchStatus.FAILED)
            else:
                logger.info(f"Batch {batch.id} execution completed successfully")
                batch.set_status(ActionBatchStatus.COMPLETED)

            self._notify_batch_updated()
            return success

        except Exception as e:
            error_msg = f"Batch execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            batch.set_status(ActionBatchStatus.FAILED)
            self._error_message = error_msg
            self._notify_batch_updated()
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
            return False

        entry = self.state.undo()
        if not entry:
            return False

        # Find the action in the current state
        batch = self.state.get_batch_by_id(entry.batch_id)
        if not batch:
            return False

        action = next(
            (a for a in batch.actions 
             if a.email.id == entry.action_before.email.id),
            None
        )
        if not action:
            return False

        # Restore the previous state
        action.destination = entry.action_before.destination
        action.mark_as_read = entry.action_before.mark_as_read
        action.status = entry.action_before.status
        return True

    def redo(self) -> bool:
        """Redo the last undone action modification."""
        if not self.state.can_redo():
            return False

        entry = self.state.redo()
        if not entry:
            return False

        # Find the action in the current state
        batch = self.state.get_batch_by_id(entry.batch_id)
        if not batch:
            return False

        action = next(
            (a for a in batch.actions 
             if a.email.id == entry.action_after.email.id),
            None
        )
        if not action:
            return False

        # Restore the redone state
        action.destination = entry.action_after.destination
        action.mark_as_read = entry.action_after.mark_as_read
        action.status = entry.action_after.status
        return True

    # Batch State Operations

    def get_batch_summary(self) -> dict:
        """Get a summary of the current batch state."""
        batch = self.state.current_batch
        if not batch:
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
        logger.debug(f"Batch summary for {batch.id}: {summary}")
        return summary

    def get_batches_by_status(self, status: ActionBatchStatus) -> list[ActionBatch]:
        """Get all batches with the given status."""
        return self.state.get_batches_by_status(status)

    def get_batch_by_id(self, batch_id: str) -> Optional[ActionBatch]:
        """Get a batch by its ID."""
        return self.state.get_batch_by_id(batch_id)

    def select_batch(self, batch: ActionBatch) -> None:
        """Select a batch as the current batch."""
        logger.info(f"Selecting batch {batch.id}")
        self.state.set_current_batch(batch)
        self._notify_batch_updated()
