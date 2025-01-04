# Card View Redesign Proposal

## Overview
This document outlines proposed changes to the card view component and destination editing functionality in the email management TUI.

## Changes

### 1. Card View to Detail View
The card view will be repurposed as a detail view focused on displaying complete email content:

- **Purpose**: Show full email content and metadata when an email is selected
- **Content Display**:
  - Complete email body
  - Full headers (From, To, CC, Subject, Date)
  - Attachments list if present
- **Initial Implementation**:
  - Placeholder view showing basic email metadata
  - Structured layout for future content integration
  - Maintain existing keyboard navigation (j/k for next/previous)

### 2. Vim-style Destination Editing
Replace the current destination selection dropdown with vim-inspired keyboard shortcuts:

#### Workflow
1. User selects an email in the list view
2. Pressing 'e' enters "destination edit mode"
3. Single-key shortcuts immediately move email to corresponding destination
4. Visual indicator shows available shortcuts while in edit mode

#### Destination Shortcuts
```
n - Newsletter
b - Business Transaction
a - Archive
d - Delete
i - Inbox
```

#### Implementation Details
- Add new EditMode enum to track UI state
- Show shortcuts in footer area when in edit mode
- Single keypress handling for immediate action
- No need for confirmation - actions are immediately undoable

### 3. UI Changes

#### Footer Shortcuts Display
```
Normal Mode:
j/k: Navigate  Space: Accept/Reject  e: Edit Destination  r: Read/Unread  Enter: View Details

Edit Mode (after pressing 'e'):
[n]ewsletter  [b]usiness  [a]rchive  [d]elete  [i]nbox  e: Cancel
- other shortcuts (like j/k) also will work and cancel edit mode
```

#### Status Indicators
- Visual indicator when in edit mode
- Highlight available shortcuts
- Clear feedback when destination changes

### 4. Initial Implementation Plan

#### Phase 1: Destination Shortcuts
1. Implement edit mode
   - Add EditMode enum
   - Update key handling
   - Add footer shortcut display
2. Allowing cancel

#### Phase 1: Basic Structure
1. Create placeholder detail view
   - Basic email metadata display
   - Placeholder for content area
   - Maintain existing navigation

## Technical Considerations

### State Management
```python
from enum import Enum

class EditMode(Enum):
    NORMAL = "normal"
    DESTINATION = "destination"

class AppState:
    def __init__(self):
        self.edit_mode: EditMode = EditMode.NORMAL
```

### Key Handling
# TODO: look at how Textual handles keybindings
```python
def on_key(self, event: events.Key) -> None:
    if self.edit_mode == EditMode.DESTINATION:
        # Map keys to destinations
        destinations = {
            "n": EmailDestination.NEWSLETTER,
            "b": EmailDestination.BUSINESS_TRANSACTION,
            "a": EmailDestination.ARCHIVE,
            "d": EmailDestination.DELETE,
            "i": EmailDestination.INBOX,
        }
        if dest := destinations.get(event.key):
            self._controller.modify_action(self._get_selected_action(), destination=dest)
            self.edit_mode = EditMode.NORMAL
    else:
        # Handle normal mode keys
        super().on_key(event)
```

### Footer Component
```python
class Footer(Widget):
    def render(self) -> RenderableType:
        if self.app.edit_mode == EditMode.DESTINATION:
            return "[n]ewsletter  [b]usiness  [a]rchive  [d]elete  [i]nbox  Esc: Cancel"
        return "j/k: Navigate  Space: Accept/Reject  e: Edit  r: Read/Unread  Enter: View"
```

## Migration Strategy

1. Create new detail view component
2. Gradually phase out old card view functionality
3. Implement edit mode and shortcuts
4. Update documentation and tests

## Future Enhancements

1. Rich email content display
   - HTML rendering
   - Attachment previews
   - Syntax highlighting for code

2. Advanced shortcuts
   - Custom key mappings
   - Macro support
   - Multiple action sequences

3. Visual improvements
   - Smooth transitions
   - Better shortcut visibility
   - Theme integration
