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
        ("h", "previous_tab", "Previous Tab"),
        ("l", "next_tab", "Next Tab"),
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

    def on_mount(self) -> None:
        """Handle widget mount."""
        logger.debug("EmailTabs mounted")

    def compose(self):
        logger.debug("EmailTabs composing")
        with TabbedContent() as tabbed:
            def on_focus() -> None:
                logger.debug("TabbedContent gained focus")
                
            def on_blur() -> None:
                logger.debug("TabbedContent lost focus")
                
            tabbed.on_focus = on_focus
            tabbed.on_blur = on_blur
            for dest in EmailDestination:
                dest_batch = self._destination_batches.get(dest)
                # Use lowercase destination name as ID
                tab_id = dest.name.lower()
                tab = TabPane(f"[b]{dest.name}[/b]", id=tab_id)
                tab.destination = dest # Associate tab with destination
                with tab:
                    list_view = EmailListView(
                        email_batch=dest_batch,
                        controller=self._controller
                    )
                    logger.debug(f"Created list view for {dest.name}")
                    yield list_view

    def action_previous_tab(self) -> None:
        """Switch to the previous tab."""
        tabbed = self.query_one(TabbedContent)
        current_id = tabbed.active
        # Get all tab IDs
        tab_ids = [tab.id for tab in self.query("TabPane")]
        if not tab_ids:
            return
            
        # Get current list view focus state
        current_tab = next((tab for tab in tabbed.query(TabPane) if tab.id == current_id), None)
        if current_tab:
            list_view = current_tab.query_one(EmailListView)
            if list_view:
                logger.debug(f"Before keyboard prev tab, table has_focus={list_view._table.has_focus}, cursor_row={list_view._table.cursor_row}")
            
        # Find current index and calculate previous
        current_idx = tab_ids.index(current_id)
        prev_idx = (current_idx - 1) % len(tab_ids)
        # Switch to previous tab
        tabbed.active = tab_ids[prev_idx]

    def action_next_tab(self) -> None:
        """Switch to the next tab."""
        tabbed = self.query_one(TabbedContent)
        current_id = tabbed.active
        # Get all tab IDs
        tab_ids = [tab.id for tab in self.query("TabPane")]
        if not tab_ids:
            return
            
        # Get current list view focus state
        current_tab = next((tab for tab in tabbed.query(TabPane) if tab.id == current_id), None)
        if current_tab:
            list_view = current_tab.query_one(EmailListView)
            if list_view:
                logger.debug(f"Before keyboard next tab, table has_focus={list_view._table.has_focus}, cursor_row={list_view._table.cursor_row}")
            
        # Find current index and calculate next
        current_idx = tab_ids.index(current_id)
        next_idx = (current_idx + 1) % len(tab_ids)
        # Switch to next tab
        tabbed.active = tab_ids[next_idx]

    def on_tabbed_content_tab_activated(self, event) -> None:
        """Handle tab switch events."""
        dest = event.pane.destination  # Use pane instead of tab to get the TabPane
        batch = self._destination_batches.get(dest)
        logger.debug(f"Tab switched to {dest.name}, updating current batch")
        logger.debug(f"App focused widget before tab switch: {self.app.focused.__class__.__name__ if self.app.focused else None}")
        
        # Get the list view for this tab
        list_view = event.pane.query_one(EmailListView)
        if list_view:
            logger.debug(f"Found list view for tab, table has_focus={list_view._table.has_focus}, cursor_row={list_view._table.cursor_row}")
        else:
            logger.warning("No list view found for tab")
            return
            
        if batch:
            logger.debug("Selecting batch")
            self._controller.select_batch(batch)
        else:
            logger.debug(f"No batch for {dest.name}")
            # Clear current batch when switching to a tab with no actions
            self._controller.select_batch(None)
            
        logger.debug(f"After batch update, table has_focus={list_view._table.has_focus}, cursor_row={list_view._table.cursor_row}")
        logger.debug(f"App focused widget after tab switch: {self.app.focused.__class__.__name__ if self.app.focused else None}")

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
            first_batch = self._destination_batches[first_dest]
            self._controller.select_batch(first_batch)

    def action_execute_batch(self) -> None:
        """Execute the current batch."""
        # Get current tab's list view and batch
        tabbed = self.query_one(TabbedContent)
        current_id = tabbed.active
        current_tab = next((tab for tab in tabbed.query(TabPane) if tab.id == current_id), None)
        if not current_tab:
            return
            
        list_view = current_tab.query_one(EmailListView)
        if not list_view or not list_view.current_batch:
            return
            
        logger.debug(f"Executing batch, table has_focus={list_view._table.has_focus}, cursor_row={list_view._table.cursor_row}")

        # Don't execute if batch is in a failed state
        if list_view.current_batch.status == ActionBatchStatus.FAILED:
            error_message = self.app.query_one("#error_message", expect_type=None)
            if error_message:
                error_message.show_error("Cannot execute batch in failed state")
            return
            
        # Post execute batch message
        self.post_message(self.ExecuteBatch())

    class ExecuteBatch(Message):
        """Message sent when batch execution is requested."""
