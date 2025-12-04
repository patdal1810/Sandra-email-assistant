import os.path
from typing import List, Dict, Any
import base64
from email.mime.text import MIMEText
from email.utils import parseaddr
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
from email.utils import formataddr

# Read + modify + create drafts/send
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
]


def send_new_email(service, to_email: str, subject: str, body: str, from_name: str | None = None):
    """
    Send a brand new email (not a reply) to the given address.
    """
    if from_name:
        from_header = formataddr((from_name, "me"))
    else:
        from_header = None  # Gmail will fill in the account email

    msg = MIMEText(body)
    msg["To"] = to_email
    msg["Subject"] = subject
    if from_header:
        msg["From"] = from_header

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    message = {"raw": raw}

    sent = service.users().messages().send(
        userId="me",
        body=message,
    ).execute()

    return sent


def get_gmail_service():
    """Authenticate and return a Gmail service client."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def list_unread_messages(service, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    List unread emails that arrived today (local date).
    Uses Gmail search query 'after:YYYY/MM/DD'.
    """
    today = datetime.now().strftime("%Y/%m/%d")

    result = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        q=f"after:{today}",
        maxResults=max_results,
    ).execute()

    return result.get("messages", [])


def get_message_detail(service, msg_id: str) -> Dict[str, Any]:
    """Get full message with headers and body."""
    msg = service.users().messages().get(
        userId="me",
        id=msg_id,
        format="full",
    ).execute()
    return msg


def _find_header(headers, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def extract_email_data(msg: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract subject, from, plain-text body (simple version).
    """
    headers = msg.get("payload", {}).get("headers", [])

    subject = _find_header(headers, "Subject")
    from_ = _find_header(headers, "From")

    body = ""
    payload = msg.get("payload", {})

    if payload.get("mimeType") == "text/plain":
        body_data = payload.get("body", {}).get("data")
        if body_data:
            body = base64.urlsafe_b64decode(body_data).decode(
                "utf-8", errors="ignore"
            )
    else:
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data")
                if body_data:
                    body = base64.urlsafe_b64decode(body_data).decode(
                        "utf-8", errors="ignore"
                    )
                    break

    return {
        "subject": subject,
        "from": from_,
        "body": body,
    }


def mark_as_read(service, msg_id: str):
    """Remove UNREAD label from a message."""
    service.users().messages().modify(
        userId="me",
        id=msg_id,
        body={"removeLabelIds": ["UNREAD"], "addLabelIds": []},
    ).execute()


def create_reply_draft(service, original_msg: Dict[str, Any], reply_text: str):
    """Create a Gmail draft reply in the same thread."""
    payload = original_msg.get("payload", {})
    headers = payload.get("headers", [])

    from_addr = _find_header(headers, "From")
    subject = _find_header(headers, "Subject")
    message_id = _find_header(headers, "Message-ID")

    _, to_email = parseaddr(from_addr)

    if subject.lower().startswith("re:"):
        reply_subject = subject
    else:
        reply_subject = f"Re: {subject}"

    msg = MIMEText(reply_text)
    msg["To"] = to_email
    msg["Subject"] = reply_subject

    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    draft_body = {
        "message": {
            "raw": raw,
            "threadId": original_msg.get("threadId"),
        }
    }

    draft = service.users().drafts().create(
        userId="me", body=draft_body
    ).execute()

    return draft


def send_reply(service, original_msg: Dict[str, Any], reply_text: str):
    """Send an actual reply email in the same thread."""
    payload = original_msg.get("payload", {})
    headers = payload.get("headers", [])

    from_addr = _find_header(headers, "From")
    subject = _find_header(headers, "Subject")
    message_id = _find_header(headers, "Message-ID")

    _, to_email = parseaddr(from_addr)

    if subject.lower().startswith("re:"):
        reply_subject = subject
    else:
        reply_subject = f"Re: {subject}"

    msg = MIMEText(reply_text)
    msg["To"] = to_email
    msg["Subject"] = reply_subject

    if message_id:
        msg["In-Reply-To"] = message_id
        msg["References"] = message_id

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    body = {
        "raw": raw,
        "threadId": original_msg.get("threadId"),
    }

    sent = service.users().messages().send(
        userId="me", body=body
    ).execute()

    return sent
