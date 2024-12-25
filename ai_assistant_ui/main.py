"""Main application entry point."""
from textual.app import App
from textual.containers import Container
from textual.widgets import LoadingIndicator
from textual.reactive import reactive
import asyncio
import logging

from ai_assistant_ui.models.state import AppState
# from ai_assistant_ui.models.gmail import GmailWrapper
from ai_assistant_ui.models.mock_gmail import MockGmailWrapper as GmailWrapper
from ai_assistant_ui.controllers.email_controller import EmailController
from ai_assistant_ui.views.tab_view import EmailTabs
from ai_assistant_ui.views.status_bar import StatusBar
from ai_assistant_ui.utils.logging import setup_logging
from npc.apis.gmail_client import GmailSearchOptions, GmailClientError

# Set up logging
log_file = setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"Application starting, logging to {log_file}")

class InboxApp(App):
    """Main application class."""

    # App state
    is_loading = reactive(False)

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        logger.info("Initializing application components")
        
        # Initialize models
        self.gmail = GmailWrapper()
        self.state = AppState()
        
        # Initialize controller
        self.email_controller = EmailController(self.gmail, self.state)
        
        # Initialize data
        self.initial_batch = None
        self.initial_error = None

    async def _load_initial_data(self):
        """Load initial email data."""
        try:
            logger.info("Fetching unread emails...")
            # Get unread threads
            email_threads = await self.gmail.get_emails(
                GmailSearchOptions(unread=True),
                max_results=10
            )
            logger.info(f"Fetched {len(email_threads)} unread threads")
            logger.debug(f"Email threads: {[e.subject for e, _ in email_threads]}")
            
            if not email_threads:
                logger.warning("No unread threads found")
                return None, "No unread emails found"
            
            logger.info("Creating batch from threads...")
            # Create batch from threads
            batch = await self.email_controller.load_batch(email_threads)
            if batch:
                logger.info(f"Successfully created batch {batch.id} with {len(batch.actions)} actions")
                logger.debug(f"Batch actions: {[(a.email.subject, a.destination.name) for a in batch.actions]}")
                return batch, None
            else:
                error_msg = f"Failed to create batch: {self.email_controller.error_message}"
                logger.error(error_msg)
                return None, error_msg
                
        except GmailClientError as e:
            error_msg = f"Error loading emails: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(error_msg)
            return None, error_msg

    def compose(self):
        """Create main layout."""
        yield Container(
            LoadingIndicator(),
            EmailTabs(
                actions=[],  # Start with empty actions, will update after loading
                controller=self.email_controller
            ),
            StatusBar(),
        )

    async def on_mount(self) -> None:
        """Set up the application when mounted."""
        # Get widgets
        tabs = self.query_one(EmailTabs)
        loading = self.query_one(LoadingIndicator)
        status_bar = self.query_one(StatusBar)
        
        # Hide loading initially
        loading.display = False
        
        # Set up batch update callback
        def on_batch_updated(batch):
            status_bar.current_batch = batch
        self.email_controller.add_batch_updated_callback(on_batch_updated)
        
        # Show loading indicator
        self.is_loading = True
        loading.display = True
        
        # Load initial data
        self.initial_batch, self.initial_error = await self._load_initial_data()
        
        # Update UI based on result
        if self.initial_error:
            status_bar.error_message = self.initial_error
        elif self.initial_batch:
            # Update tabs with loaded actions
            logger.info(f"Updating tabs with {len(self.initial_batch.actions)} actions")
            tabs.update_actions(self.initial_batch.actions)
        
        # Hide loading indicator
        self.is_loading = False
        loading.display = False

    async def handle_batch_execution(self) -> None:
        """Handle batch execution with loading state."""
        loading = self.query_one(LoadingIndicator)
        status_bar = self.query_one(StatusBar)
        
        # Show loading during execution
        self.is_loading = True
        loading.display = True
        
        try:
            success = await self.email_controller.execute_current_batch()
            if not success:
                status_bar.error_message = self.email_controller.error_message
        finally:
            self.is_loading = False
            loading.display = False

    def on_email_tabs_execute_batch(self) -> None:
        """Handle execute batch request from tabs."""
        asyncio.create_task(self.handle_batch_execution())


if __name__ == "__main__":
    app = InboxApp()
    app.run()
