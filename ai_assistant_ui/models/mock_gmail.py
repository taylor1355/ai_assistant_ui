"""Mock Gmail client for testing."""
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
import asyncio

# Mock classes to avoid dependency on actual Gmail implementation
@dataclass
class MockEmail:
    """Mock implementation of Email class."""
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    timestamp: datetime
    body: str
    snippet: str

@dataclass
class MockThread:
    """Mock implementation of GmailThread class."""
    id: str
    snippet: str
    messages: List[str] = field(default_factory=list)

@dataclass
class MockSearchOptions:
    """Mock implementation of GmailSearchOptions."""
    labels: Optional[List[str]] = None
    unread: Optional[bool] = None

class MockGmailError(Exception):
    """Mock implementation of GmailClientError."""
    pass

from npc.prompts.ai_assistant.email_action_template import EmailDestination
from ai_assistant_ui.models.action import InboxAction

# Set fixed seed for reproducible test data
random.seed(42)

# Sample data for generating realistic-looking test emails
SAMPLE_SUBJECTS = [
    "Your Weekly Newsletter",
    "Order Confirmation #123456",
    "Meeting Notes: Project Review",
    "Invoice for Recent Purchase",
    "Updates to Your Account",
    "Special Offer Inside!",
    "Important Security Alert",
    "Your Subscription Renewal",
    "Team Sync Summary",
    "Payment Receipt"
]

SAMPLE_SENDERS = [
    "newsletter@company.com",
    "orders@shop.com",
    "team@workspace.com",
    "billing@service.com",
    "updates@platform.com",
    "marketing@brand.com",
    "security@system.com",
    "support@product.com",
    "notifications@app.com",
    "info@business.com"
]

SAMPLE_BODIES = [
    "Here's your weekly roundup of the latest updates and news...",
    "Thank you for your recent purchase. Your order details are...",
    "During today's project review meeting, we discussed...",
    "Please find attached your invoice for the recent transaction...",
    "We've made some important updates to your account settings...",
    "Don't miss out on these exclusive deals just for you...",
    "We noticed some unusual activity on your account...",
    "Your subscription will renew automatically in 7 days...",
    "Key points from today's team sync meeting...",
    "This receipt confirms your payment of..."
]

class MockGmailWrapper:
    """Mock implementation of GmailWrapper for testing."""

    def __init__(self):
        """Initialize with test data."""
        self._email_counter = 30
        self._thread_counter = 30
        self._emails = {}  # id -> MockEmail
        self._threads = {}  # id -> MockThread

    def _generate_email_id(self) -> str:
        """Generate a unique email ID."""
        self._email_counter += 1
        return f"email_{self._email_counter}"

    def _generate_thread_id(self) -> str:
        """Generate a unique thread ID."""
        self._thread_counter += 1
        return f"thread_{self._thread_counter}"

    def _create_mock_email(self) -> Tuple[MockEmail, str]:
        """Create a mock email with realistic-looking data."""
        email_id = self._generate_email_id()
        thread_id = self._generate_thread_id()
        
        # Generate random but realistic-looking data
        idx = random.randint(0, len(SAMPLE_SUBJECTS) - 1)
        
        # Create timestamp within last 7 days
        days_ago = random.randint(0, 7)
        hours_ago = random.randint(0, 23)
        timestamp = datetime.now() - timedelta(days=days_ago, hours=hours_ago)
        
        email = MockEmail(
            id=email_id,
            thread_id=thread_id,
            subject=SAMPLE_SUBJECTS[idx],
            sender=SAMPLE_SENDERS[idx],
            recipient="me@example.com",
            timestamp=timestamp,
            body=SAMPLE_BODIES[idx],
            snippet=SAMPLE_BODIES[idx][:100] + "..."
        )
        
        return email, thread_id

    def _create_mock_thread(self, thread_id: str, email_id: str) -> MockThread:
        """Create a mock thread containing the email."""
        return MockThread(
            id=thread_id,
            snippet=self._emails[email_id].snippet,
            messages=[email_id]
        )

    async def get_emails(
        self,
        options: Optional[MockSearchOptions] = None, 
        max_results: int = 10
    ) -> List[Tuple[MockEmail, MockThread]]:
        """Get mock threads and their latest emails."""
        results = []
        for _ in range(max_results):
            email, thread_id = self._create_mock_email()
            self._emails[email.id] = email
            thread = self._create_mock_thread(thread_id, email.id)
            self._threads[thread_id] = thread
            results.append((email, thread))
        return results

    async def suggest_action(self, email: MockEmail, thread: MockThread) -> InboxAction:
        """Create a mock action with random suggested destination."""
        # Weight the random choices to make some destinations more likely
        weights = [
            0.3,  # NEWSLETTER
            0.2,  # BUSINESS_TRANSACTION
            0.2,  # ARCHIVE
            0.2,  # DELETE
            0.1   # INBOX
        ]
        destination = random.choices(
            list(EmailDestination),
            weights=weights,
            k=1
        )[0]
        
        # 80% chance to mark as read
        mark_as_read = random.random() < 0.8
        
        return InboxAction(
            email=email,
            destination=destination,
            mark_as_read=mark_as_read
        )

    async def execute_action(
        self,
        thread: MockThread,
        destination: EmailDestination,
        mark_as_read: bool = True
    ) -> None:
        """Simulate executing an action (no-op in mock)."""
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Randomly fail some operations to test error handling
        # if random.random() < 0.05:  # 5% chance of failure
        #     raise MockGmailError("Simulated random failure")
