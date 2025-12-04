import re

# Simple one-line acknowledgements that do not need a reply
CLOSING_PATTERNS = [
    r"^thanks[\s!.,]*$",
    r"^thank you[\s!.,]*$",
    r"^thanks a lot[\s!.,]*$",
    r"^ok(ay)?[\s!.,]*$",
    r"^got it[\s!.,]*$",
    r"^noted[\s!.,]*$",
    r"^sounds good[\s!.,]*$",
    r"^appreciate it[\s!.,]*$",
    r"^thank you so much[\s!.,]*$",
    r"^alright[\s!.,]*$",
]

# Messages where the sender indicates THEY will continue later
DEFER_PATTERNS = [
    r"\bi('ll| will)\s+get back to you\b",
    r"\bi('ll| will)\s+reach out\b",
    r"\bi('ll| will)\s+contact\b",
    r"\blet me\s+check\s+and\s+get back\b",
]

# Emails that look like automatic systems
SYSTEM_PATTERNS = [
    r"this is an automated message",
    r"do not reply to this email",
    r"please do not reply to this message",
    r"no[-\s]?reply@",
    r"you are receiving this email because",
    r"unsubscribe",
]

# Phrases that usually mean "the ball is now in your court",
# and an auto-reply from you would sound unnatural.
CLOSURE_PHRASES = [
    "feel free to reach out",
    "whenever you are ready",
    "when you are ready",
    "at your convenience",
    "let me know when you are ready",
    "let me know if and when",
    "thank you for your quick response",
    "thank you for your response",
    "thank you for your message",
    "thank you for your follow up",
]


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _contains_question(text: str) -> bool:
    return "?" in text


def is_closing_ack(body: str) -> bool:
    """
    Returns True for very short closure messages like:
    'thanks', 'ok', 'noted', etc.
    """
    norm = _normalize(body)

    # Only treat as closure if the message is short
    if len(norm) <= 80:
        for pattern in CLOSING_PATTERNS:
            if re.match(pattern, norm):
                return True

    # Detect short gratitude messages like:
    # "thanks for the update" -> still closure
    if ("thanks" in norm or "thank you" in norm) and len(norm.split()) <= 6:
        return True

    return False


def is_defer_then_close(body: str) -> bool:
    """
    Returns True if the sender is saying they will act later and continue.
    Example: 'I will reach out and get back to you.'
    """
    norm = _normalize(body)
    for pattern in DEFER_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def is_system_like(body: str) -> bool:
    """
    Returns True if message appears to come from a system or automated process.
    """
    norm = _normalize(body)
    for pattern in SYSTEM_PATTERNS:
        if re.search(pattern, norm):
            return True
    return False


def is_polite_closure_without_question(body: str) -> bool:
    """
    Returns True for emails that:
    - have no question mark, and
    - contain closure-like phrases where the ball is in your court.
    Example: 'Thank you for your quick response. Please feel free to reach out
    whenever you are ready to discuss further.'
    """
    norm = _normalize(body)

    if _contains_question(norm):
        return False

    for phrase in CLOSURE_PHRASES:
        if phrase in norm:
            return True

    return False


def should_generate_reply(subject: str, body: str) -> bool:
    """
    Determines if the AI should generate a reply at all.
    Returns False when:
    - Message is empty
    - Out-of-office / automatic reply
    - System / notification email
    - Simple closure ('thanks', 'got it', etc.)
    - Sender indicates they will get back to you
    - Sender sends a polite closure with no question and phrases like
      'feel free to reach out whenever you are ready'
    """
    norm_subject = _normalize(subject)
    norm_body = _normalize(body)

    # Empty or blank messages do not need replies
    if not norm_body:
        return False

    # Out-of-office or auto-responses
    if "out of office" in norm_subject or "automatic reply" in norm_subject:
        return False
    if "out of office" in norm_body or "auto-reply" in norm_body or "automatic reply" in norm_body:
        return False

    # System emails or notification emails
    if is_system_like(norm_body):
        return False

    # One-line closure like "thanks", "got it", etc.
    if is_closing_ack(norm_body):
        return False

    # Sender indicates THEY will continue the conversation later
    if is_defer_then_close(norm_body):
        return False

    # Polite closure like your screenshot example
    if is_polite_closure_without_question(norm_body):
        return False

    # Otherwise it is safe to generate a reply
    return True
