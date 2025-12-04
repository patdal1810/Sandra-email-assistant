from gmail_client import (
    get_gmail_service,
    list_unread_messages,
    get_message_detail,
    extract_email_data,
    mark_as_read,
    create_reply_draft,
    send_reply,
)
from ai_butler import call_email_butler
from rules import is_noreply_address, should_auto_send
from reply_guard import should_generate_reply


def main():
    service = get_gmail_service()
    messages = list_unread_messages(service, max_results=10)

    if not messages:
        print("No unread messages found for today.")
        return

    for idx, m in enumerate(messages, start=1):
        msg_id = m["id"]
        full_msg = get_message_detail(service, msg_id)
        email_data = extract_email_data(full_msg)

        sender = email_data["from"]
        subject = email_data["subject"]
        body = email_data["body"]

        print("=" * 80)
        print(f"[{idx}] SUBJECT: {subject}")
        print(f"FROM: {sender}")
        print("-" * 80)
        print("BODY (truncated preview):")
        print((body or "")[:500])
        print()

        # Guard 1: no-reply sender
        if is_noreply_address(sender):
            print("[GUARD] No-reply or system sender detected. Skipping reply.")
            mark_as_read(service, msg_id)
            print("[INFO] Marked original message as read.")
            print("=" * 80)
            print()
            continue

        # Guard 2: closure / acknowledgement / system-like content
        if not should_generate_reply(subject, body):
            print("[GUARD] Email does not require a reply based on content analysis.")
            mark_as_read(service, msg_id)
            print("[INFO] Marked original message as read.")
            print("=" * 80)
            print()
            continue

        # Safe to generate a reply
        print("Running AI Email Butler...")

        result = call_email_butler(
            subject=subject,
            sender=sender,
            body=body,
        )

        print(f"CLASS: {result.klass}")
        print("SUMMARY:")
        print(result.summary)
        print("DRAFT REPLY:")
        print(result.draft_reply)
        print()

        if should_auto_send(sender):
            sent = send_reply(service, full_msg, result.draft_reply)
            print(f"[INFO] Auto-sent reply. Gmail message ID: {sent.get('id')}")
        else:
            draft = create_reply_draft(service, full_msg, result.draft_reply)
            draft_id = draft.get("id")
            print(f"[INFO] Draft created. ID: {draft_id}")

        mark_as_read(service, msg_id)
        print("[INFO] Marked original message as read.")
        print("=" * 80)
        print()


if __name__ == "__main__":
    main()
