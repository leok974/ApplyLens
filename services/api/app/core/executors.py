"""
Action Executors for Phase 4 Agentic Actions

Implements thin adapters for executing each ActionType:
- Gmail operations (archive, label, move, unsubscribe)
- Calendar events
- Task creation
- Sender blocking
- Attachment quarantine

All executors return (success: bool, error: str | None)
"""

from typing import Tuple, Optional, Dict, Any

# Gmail API imports (will be injected/imported from services)
# from ..services.gmail_service import gmail_service


def execute_action(proposed_action, user=None) -> Tuple[bool, Optional[str]]:
    """
    Execute a proposed action and return outcome.

    Args:
        proposed_action: ProposedAction model instance
        user: Optional user context

    Returns:
        (success: bool, error_msg: str | None)
    """
    try:
        action_type = proposed_action.action.value
        email_id = proposed_action.email_id
        params = proposed_action.params or {}

        if action_type == "archive_email":
            return gmail_archive(email_id), None

        if action_type == "label_email":
            label = params.get("label")
            if not label:
                return False, "Missing 'label' param"
            return gmail_label(email_id, label), None

        if action_type == "move_to_folder":
            folder = params.get("folder")
            if not folder:
                return False, "Missing 'folder' param"
            return gmail_move(email_id, folder), None

        if action_type == "unsubscribe_via_header":
            return try_list_unsubscribe(email_id), None

        if action_type == "create_calendar_event":
            return create_calendar_event(params), None

        if action_type == "create_task":
            return create_task_item(params), None

        if action_type == "block_sender":
            sender = params.get("sender")
            if not sender:
                return False, "Missing 'sender' param"
            return block_sender(sender), None

        if action_type == "quarantine_attachment":
            return quarantine_email(email_id), None

        return False, f"Unknown action type: {action_type}"

    except Exception as e:
        return False, str(e)


# ===== Gmail Operations =====


def gmail_archive(email_id: int) -> bool:
    """
    Archive an email (remove INBOX label, add ARCHIVED).

    Implementation:
    1. Load Email from DB
    2. Call Gmail API modify() to remove INBOX, add ARCHIVED
    3. Update local labels in DB
    """
    try:
        # TODO: Implement with gmail_service
        # email = db.get(Email, email_id)
        # gmail_service.archive_message(email.gmail_id)
        print(f"[EXECUTOR] Archiving email {email_id}")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Archive failed: {e}")
        return False


def gmail_label(email_id: int, label: str) -> bool:
    """
    Add a label to an email.

    Implementation:
    1. Load Email from DB
    2. Call Gmail API modify() to add label
    3. Update local labels in DB
    """
    try:
        # TODO: Implement with gmail_service
        # email = db.get(Email, email_id)
        # gmail_service.modify_labels(email.gmail_id, add_labels=[label])
        print(f"[EXECUTOR] Labeling email {email_id} with '{label}'")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Label failed: {e}")
        return False


def gmail_move(email_id: int, folder: str) -> bool:
    """
    Move an email to a folder (label in Gmail).

    Implementation:
    1. Load Email from DB
    2. Call Gmail API modify() to add folder label, remove INBOX
    3. Update local labels in DB
    """
    try:
        # TODO: Implement with gmail_service
        # email = db.get(Email, email_id)
        # gmail_service.modify_labels(email.gmail_id, add_labels=[folder], remove_labels=["INBOX"])
        print(f"[EXECUTOR] Moving email {email_id} to folder '{folder}'")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Move failed: {e}")
        return False


def try_list_unsubscribe(email_id: int) -> bool:
    """
    Attempt to unsubscribe using List-Unsubscribe header.

    Implementation:
    1. Load Email from DB with raw headers
    2. Parse List-Unsubscribe header
    3. Prefer mailto: with auto-composed draft
    4. Fall back to https: GET if safe

    Returns:
        True if unsubscribe action was attempted
    """
    try:
        # TODO: Implement with email parsing
        # email = db.get(Email, email_id)
        # headers = email.raw.get("payload", {}).get("headers", [])
        # unsub_header = next((h["value"] for h in headers if h["name"].lower() == "list-unsubscribe"), None)

        # if not unsub_header:
        #     return False

        # # Parse mailto: or https: links
        # mailto_match = re.search(r'<mailto:([^>]+)>', unsub_header)
        # if mailto_match:
        #     # Create draft email to unsubscribe
        #     return send_unsubscribe_email(mailto_match.group(1))

        # https_match = re.search(r'<(https://[^>]+)>', unsub_header)
        # if https_match:
        #     # GET request to unsubscribe (if safe domain)
        #     return safe_unsubscribe_get(https_match.group(1))

        print(f"[EXECUTOR] Unsubscribing email {email_id} via List-Unsubscribe")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Unsubscribe failed: {e}")
        return False


# ===== Calendar Operations =====


def create_calendar_event(params: Dict[str, Any]) -> bool:
    """
    Create a calendar event from email data.

    Expected params:
    - title: str
    - start_time: ISO datetime
    - end_time: ISO datetime (optional, default +1hr)
    - location: str (optional)
    - description: str (optional)

    Implementation:
    1. Parse datetime strings
    2. Call Google Calendar API to create event
    3. Return success/fail
    """
    try:
        # TODO: Implement with calendar service
        # title = params.get("title", "Email Event")
        # start = datetime.fromisoformat(params["start_time"])
        # end = datetime.fromisoformat(params.get("end_time", (start + timedelta(hours=1)).isoformat()))
        # location = params.get("location")
        # description = params.get("description")

        # calendar_service.create_event(title, start, end, location, description)
        print(f"[EXECUTOR] Creating calendar event: {params.get('title', 'Event')}")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Calendar event creation failed: {e}")
        return False


# ===== Task Operations =====


def create_task_item(params: Dict[str, Any]) -> bool:
    """
    Create a task from email data.

    Expected params:
    - title: str
    - due_date: ISO datetime (optional)
    - notes: str (optional)

    Implementation:
    1. Call Google Tasks API to create task
    2. Return success/fail
    """
    try:
        # TODO: Implement with tasks service
        # title = params.get("title", "Email Task")
        # due_date = params.get("due_date")
        # notes = params.get("notes")

        # tasks_service.create_task(title, due_date, notes)
        print(f"[EXECUTOR] Creating task: {params.get('title', 'Task')}")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Task creation failed: {e}")
        return False


# ===== Security Operations =====


def block_sender(sender: str) -> bool:
    """
    Block a sender (add to block list filter).

    Implementation:
    1. Extract email/domain from sender
    2. Create Gmail filter to auto-archive or trash
    3. Store in local block list
    """
    try:
        # TODO: Implement with gmail_service
        # gmail_service.create_filter(from_address=sender, action="trash")
        print(f"[EXECUTOR] Blocking sender: {sender}")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Block sender failed: {e}")
        return False


def quarantine_email(email_id: int) -> bool:
    """
    Quarantine an email and its attachments.

    Implementation:
    1. Load Email from DB
    2. Set quarantined=True in DB
    3. Move attachments to safe storage (/data/quarantine/)
    4. Add QUARANTINED label in Gmail
    """
    try:
        # TODO: Implement with db and storage
        # email = db.get(Email, email_id)
        # email.quarantined = True
        # db.commit()

        # # Move attachments
        # for attachment in email.raw.get("payload", {}).get("parts", []):
        #     if attachment.get("filename"):
        #         move_attachment_to_quarantine(email_id, attachment)

        # gmail_service.modify_labels(email.gmail_id, add_labels=["QUARANTINED"])
        print(f"[EXECUTOR] Quarantining email {email_id}")
        return True
    except Exception as e:
        print(f"[EXECUTOR] Quarantine failed: {e}")
        return False


# ===== Helper Functions =====


def send_unsubscribe_email(mailto_address: str) -> bool:
    """Send unsubscribe email via Gmail API."""
    # TODO: Implement
    print(f"[EXECUTOR] Sending unsubscribe email to {mailto_address}")
    return True


def safe_unsubscribe_get(url: str) -> bool:
    """
    Safely perform GET request to unsubscribe URL.

    Only allows known-safe domains to prevent CSRF.
    """
    # TODO: Implement with domain whitelist
    print(f"[EXECUTOR] Performing unsubscribe GET: {url}")
    return True


def move_attachment_to_quarantine(email_id: int, attachment: Dict[str, Any]) -> bool:
    """Move attachment to quarantine storage."""
    # TODO: Implement
    print(f"[EXECUTOR] Moving attachment to quarantine: {attachment.get('filename')}")
    return True
