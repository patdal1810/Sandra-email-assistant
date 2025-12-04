from email.utils import parseaddr

from config import AUTO_SEND_EMAILS, AUTO_SEND_DOMAINS


def is_noreply_address(addr: str) -> bool:
    """
    True if address looks like a no-reply / system email.
    """
    addr_lower = (addr or "").lower()
    patterns = [
        "no-reply",
        "noreply",
        "do-not-reply",
        "donotreply",
        "no_reply",
        "noresponse",
        "no-response",
        "mailer-daemon",
        "postmaster",
    ]
    return any(p in addr_lower for p in patterns)


def normalize_email_from_header(from_header: str) -> str:
    """
    Turn 'Name <email@x.com>' into 'email@x.com'.
    """
    _, addr = parseaddr(from_header or "")
    return addr.lower()


def should_auto_send(sender_header: str) -> bool:
    """
    Return True if this sender should get an automatic send instead of a draft.
    Controlled via AUTO_SEND_EMAILS and AUTO_SEND_DOMAINS.
    """
    addr = normalize_email_from_header(sender_header)
    if not addr:
        return False

    if addr in AUTO_SEND_EMAILS:
        return True

    if "@" in addr:
        domain = addr.split("@")[-1]
        if domain in AUTO_SEND_DOMAINS:
            return True

    return False
