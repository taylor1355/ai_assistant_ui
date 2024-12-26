"""Tab-based navigation interface."""
import logging
from textual.widgets import TabbedContent, TabPane
from textual.message import Message
from textual.widget import Widget
from textual.reactive import reactive

logger = logging.getLogger(__name__)

from ai_assistant_ui.controllers.email_controller import EmailController
from ai_assistant_ui.models.action import InboxAction
from ai_assistant_ui.models.batch import ActionBatchStatus, group_by_destination
from ai_assistant_ui.views.list_view import EmailListView
from npc.prompts.ai_assistant.email_action_template import EmailDestination


class EmailTabs(Widget):
    """Tab container for different email views."""

    BINDINGS = [
        ("x", "execute_batch", "Execute Batch"),
    ]

    DEFAULT_CSS = """
    EmailTabs {
        height: 1fr;
        border: solid $primary;
    }
    """

    def __init__(
        self, 
        actions: list[InboxAction],
        controller: EmailController
    ):
        super().__init__()
        self._destination_batches = group_by_destination(actions)
        self._controller = controller
        
        # Initialize state batches
        for dest, batch in self._destination_batches.items():
            self._controller.state.batches[dest.name.lower()] = batch

    def compose(self):
        with TabbedContent():
            for dest in EmailDestination:
                dest_batch = self._destination_batches.get(dest)
                tab = TabPane(f"[b]{dest.name}[/b]")
                tab.destination = dest # Associate tab with destination
                with tab:
                    yield EmailListView(
                        email_batch=dest_batch,
                        controller=self._controller
                    )

    def on_tabbed_content_tab_activated(self, event) -> None:
        """Handle tab switch events."""
        dest = event.pane.destination  # Use pane instead of tab to get the TabPane
        batch = self._destination_batches.get(dest)
        logger.info(f"Tab switched to {dest.name}, updating current batch")
        if batch:
            self._controller.select_batch(batch)
        else:
            logger.debug(f"No batch for {dest.name}")
            # Clear current batch when switching to a tab with no actions
            self._controller.select_batch(None)

    def update_actions(self, actions: list[InboxAction]) -> None:
        """Update tabs with new actions."""
        # For each action, use controller to set its destination
        for action in actions:
            # Get current batch for action
            current_batch = next(
                (batch for batch in self._destination_batches.values() 
                 if action in batch.actions),
                None
            )
            
            # If action's destination doesn't match its current batch, update it
            if current_batch and action.destination != current_batch.actions[0].destination:
                self._controller.modify_action(action, destination=action.destination)
        
        # Update view with new batches
        self._destination_batches = group_by_destination(actions)
        for dest, batch in self._destination_batches.items():
            self._controller.state.batches[dest.name.lower()] = batch
            
        # Update each tab's content
        for dest in EmailDestination:
            tab = next(t for t in self.query("TabPane") if t.destination == dest)
            list_view = tab.query_one(EmailListView)
            if list_view:
                batch = self._destination_batches.get(dest)
                list_view.current_batch = batch
        
        # Set initial batch if needed
        if not self._controller.state.current_batch and self._destination_batches:
            first_dest = next(iter(self._destination_batches))
            self._controller.select_batch(self._destination_batches[first_dest])

    def action_execute_batch(self) -> None:
        """Execute the current batch."""
        # Get current tab's list view and batch
        current_tab = self.query_one("TabbedContent TabPane.-active")
        if not current_tab:
            return
            
        list_view = current_tab.query_one("EmailListView")
        if not list_view or not list_view.current_batch:
            return

        # Don't execute if batch is in a failed state
        if list_view.current_batch.status == ActionBatchStatus.FAILED:
            error_message = self.app.query_one("#error_message", expect_type=None)
            if error_message:
                error_message.show_error("Cannot execute batch in failed state")
    class ExecuteBatch(Message):
        """Message sent when batch execution is requested."""
