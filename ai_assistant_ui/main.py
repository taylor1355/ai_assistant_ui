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

    #
    # Class setup
    #

    class ErrorMessages:
        """Application error messages."""
        # Email loading errors
        NO_UNREAD_EMAILS = "No unread emails found"
        GMAIL_ERROR = "Error loading emails: {}"
        
        # Batch operation errors
        BATCH_CREATE_ERROR = "Failed to create batch: {}"
        BATCH_EXECUTION_ERROR = "Failed to execute batch: {}"
        
        # General errors
        UNEXPECTED_ERROR = "Unexpected error: {}"

    is_loading = reactive(False)  # Loading state for async operations
    
    # Widget references
    _tabs: EmailTabs
    _loading_indicator: LoadingIndicator
    _status_bar: StatusBar

    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        logger.info("Initializing application components")
        
        # Initialize models
        self.gmail = GmailWrapper()
        self.state = AppState()
        
        # Initialize controller
        self.email_controller = EmailController(self.gmail, self.state)

    #
    # UI Setup and Layout
    #
    
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

    def watch_is_loading(self, loading: bool) -> None:
        """React to loading state changes by updating loading indicator."""
        if hasattr(self, '_loading_indicator'):
            self._loading_indicator.display = loading

    def _setup_callbacks(self) -> None:
        """Set up widget callbacks."""
        def on_batch_updated(batch):
            """Update status bar when batch changes."""
            self._status_bar.current_batch = batch
        self.email_controller.add_batch_updated_callback(on_batch_updated)

    #
    # Data Loading and Processing
    #
    
    async def _load_initial_data(self):
        """Load initial email data and return (batch, error_message)."""
        try:
            # Fetch unread threads
            email_threads = await self.gmail.get_emails(
                GmailSearchOptions(unread=True),
                max_results=10
            )
            logger.info(f"Fetched {len(email_threads)} unread email threads")
            
            # Handle no emails case
            if not email_threads:
                return None, InboxApp.ErrorMessages.NO_UNREAD_EMAILS
            
            # Create batch from threads
            batch = await self.email_controller.create_batch(email_threads)
            if not batch:
                return None, InboxApp.ErrorMessages.BATCH_CREATE_ERROR.format(
                    self.email_controller.error_message
                )
            
            # Log success details at debug level
            logger.debug(
                f"Created batch {batch.id} with actions: "
                f"{[(a.email.subject, a.destination.name) for a in batch.actions]}"
            )
            return batch, None
                
        except GmailClientError as e:
            return None, InboxApp.ErrorMessages.GMAIL_ERROR.format(str(e))
        except Exception as e:
            logger.exception("Unexpected error loading initial data")
            return None, InboxApp.ErrorMessages.UNEXPECTED_ERROR.format(str(e))

    async def _handle_async_operation(self, operation_name: str, operation):
        """Handle an async operation with loading state and error handling."""
        try:
            self.is_loading = True
            result = await operation
            return result
        except Exception as e:
            error_msg = InboxApp.ErrorMessages.UNEXPECTED_ERROR.format(str(e))
            logger.exception(f"Unexpected error during {operation_name}")
            self._status_bar.error_message = error_msg
            return None
        finally:
            self.is_loading = False

    #
    # Application Lifecycle
    #

    async def on_mount(self) -> None:
        """Set up the application when mounted."""
        # Initialize widget references
        self._tabs = self.query_one(EmailTabs)
        self._loading_indicator = self.query_one(LoadingIndicator)
        self._status_bar = self.query_one(StatusBar)
        
        # Set up callbacks
        self._setup_callbacks()
        
        # Load initial data
        result = await self._handle_async_operation(
            "initial data load",
            self._load_initial_data()
        )
        
        if result:
            batch, error = result
            if error:
                self._status_bar.error_message = error
            elif batch:
                logger.info(f"Populating tabs with {len(batch.actions)} actions")
                self._tabs.update_actions(batch.actions)

    #
    # Batch Operations
    #

    async def handle_batch_execution(self) -> None:
        """Execute current batch and handle any errors."""
        result = await self._handle_async_operation(
            "batch execution",
            self.email_controller.execute_current_batch()
        )
        
        if result is not None:
            if result:
                logger.info("Successfully executed batch")
            else:
                error_msg = InboxApp.ErrorMessages.BATCH_EXECUTION_ERROR.format(
                    self.email_controller.error_message
                )
                logger.error(error_msg)
                self._status_bar.error_message = error_msg

    def on_email_tabs_execute_batch(self) -> None:
        """Handle execute batch request from tabs."""
        asyncio.create_task(self.handle_batch_execution())


if __name__ == "__main__":
    app = InboxApp()
    app.run()
