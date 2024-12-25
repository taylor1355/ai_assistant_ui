"""Gmail client wrapper for error handling."""
from typing import Optional
import asyncio
from functools import partial

from npc.apis.gmail_client import (
    GmailClient, GmailSearchOptions, Email, GmailThread, GmailClientError,
    AuthenticationError, OperationError
)
from npc.prompts.ai_assistant.email_action_template import EmailDestination
from npc.simulators.ai_assistant.tools.email_summarizer import EmailSummarizer
from npc.simulators.ai_assistant.tools.inbox_manager import InboxAction, InboxManager
from npc.apis.llm_client import Model


class GmailWrapper:
    """Wrapper around GmailClient with error handling."""

    def __init__(self, client: Optional[GmailClient] = None):
        """Initialize with optional client instance."""
        self.client = client or GmailClient()
        self.llm = Model.HAIKU
        self.email_summarizer = EmailSummarizer(self.llm)
        self.inbox_manager = InboxManager(
            llm=self.llm,
            email_summarizer=self.email_summarizer,
            gmail_client=self.client,
            label_mapping={
                EmailDestination.NEWSLETTER: "Saved Emails/Newsletters",
                EmailDestination.BUSINESS_TRANSACTION: "Saved Emails/Receipts",
                EmailDestination.ARCHIVE: None,
                EmailDestination.DELETE: "To Delete",
                EmailDestination.INBOX: "INBOX",
            }
        )

    async def get_emails(
        self,
        options: GmailSearchOptions, 
        max_results: int = 10,
    ) -> list[tuple[Email, GmailThread]]:
        """Get threads and their latest emails."""
        try:
            # Run synchronous methods in thread pool
            loop = asyncio.get_event_loop()
            threads = await loop.run_in_executor(
                None,
                partial(self.client.retrieve_threads, options, max_results=max_results)
            )
            
            results = []
            for thread in threads:
                email = await loop.run_in_executor(
                    None,
                    partial(self.client.get_latest_email, thread)
                )
                results.append((email, thread))
            return results
        except (AuthenticationError, OperationError, GmailClientError):
            # Let caller handle all errors
            raise

    async def suggest_action(self, email: Email, thread: GmailThread) -> InboxAction:
        """Create an action with suggested destination for an email."""
        try:
            loop = asyncio.get_event_loop()
            # Use InboxManager to suggest action for the thread
            actions = await loop.run_in_executor(
                None,
                partial(self.inbox_manager.suggest_actions, [thread])
            )
            if not actions:
                raise ValueError(f"No actions suggested for email: {email.subject}")
            return actions[0]  # Return first suggested action
        except GmailClientError:
            # Let caller handle the error
            raise

    async def execute_action(
        self,
        thread: GmailThread,
        destination: EmailDestination,
        mark_as_read: bool = True
    ) -> None:
        """Execute an action on a thread."""
        try:
            if mark_as_read:
                await self.client.mark_as_read(thread)

            if destination == EmailDestination.ARCHIVE:
                await self.client.archive_thread(thread)
            elif destination == EmailDestination.DELETE:
                await self.client.delete_thread(thread)
            else:
                # Apply appropriate label based on destination
                label = self._get_label_for_destination(destination)
                if label:
                    await self.client.apply_label(thread, label)
                    
        except GmailClientError:
            # Let caller handle the error
            raise

    def _get_label_for_destination(self, destination: EmailDestination) -> Optional[str]:
        """Get the Gmail label for a destination."""
        label_ids = {
            "CATEGORY_PERSONAL": "CATEGORY_PERSONAL",
            "CATEGORY_PROMOTIONS": "CATEGORY_PROMOTIONS",
            "CATEGORY_SOCIAL": "CATEGORY_SOCIAL",
            "CATEGORY_UPDATES": "CATEGORY_UPDATES",
            "IMPORTANT": "IMPORTANT",
            "INBOX": "INBOX",
            "Saved Emails/Receipts": "Label_11",
            "Saved Emails/Newsletters": "Label_390122604015354833",
            "To Delete": "Label_6230125154949725760",
            "UNREAD": "UNREAD",
        }
        label_mapping = {
            EmailDestination.NEWSLETTER: "Saved Emails/Newsletters",
            EmailDestination.BUSINESS_TRANSACTION: "Saved Emails/Receipts",
            EmailDestination.ARCHIVE: None,
            EmailDestination.DELETE: "To Delete",
            EmailDestination.INBOX: "INBOX",
        }
        label_mapping = {k: label_ids.get(v) for k, v in label_mapping.items()}
        return label_mapping.get(destination)
