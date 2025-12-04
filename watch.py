import time

from state import load_state, save_state
from gmail_client import (
    get_gmail_service,
    list_unread_messages,
    get_message_detail,
    extract_email_data,
    mark_as_read,
    create_reply_draft,
    send_reply,
    send_new_email,         
)
from agent_sandra import (
    call_email_butler,
    compose_email_from_context,   
)
from rules import is_noreply_address, should_auto_send
from reply_guard import should_generate_reply


def watch_inbox(interval: int = 10):
    print(f"Watching inbox every {interval} seconds...")

    state = load_state()
    processed = set(state.get("processed_ids", []))

    service = get_gmail_service()

    while True:
        try:
            messages = list_unread_messages(service, max_results=10)

            if messages:
                for m in messages:
                    msg_id = m["id"]

                    # Skip already processed emails
                    if msg_id in processed:
                        continue

                    full_msg = get_message_detail(service, msg_id)
                    email_data = extract_email_data(full_msg)

                    sender = email_data["from"]
                    subject = email_data["subject"]
                    body = email_data["body"]

                    print("\n==============================")
                    print(f"NEW EMAIL: {subject} FROM {sender}")
                    print("BODY (truncated preview):")
                    print((body or "")[:300])
                    print()

                    # Guard 1: no-reply / system sender
                    if is_noreply_address(sender):
                        print("[GUARD] No-reply or system sender. Skipping reply.")
                        mark_as_read(service, msg_id)
                        print("Marked as read.")
                        processed.add(msg_id)
                        state["processed_ids"] = list(processed)
                        save_state(state)
                        continue

                    # Guard 2: closure / acknowledgement / system-like content
                    if not should_generate_reply(subject, body):
                        print("[GUARD] No reply needed based on content.")
                        mark_as_read(service, msg_id)
                        print("Marked as read.")
                        processed.add(msg_id)
                        state["processed_ids"] = list(processed)
                        save_state(state)
                        continue

                    # Safe to reply
                    result = call_email_butler(subject, sender, body)

                    print("Summary:")
                    print(result.summary)
                    print("Draft reply:")
                    print(result.draft_reply)
                    print()

                    if should_auto_send(sender):
                        sent = send_reply(service, full_msg, result.draft_reply)
                        print(f"Auto-sent reply. Gmail ID: {sent.get('id')}")
                    else:
                        draft = create_reply_draft(service, full_msg, result.draft_reply)
                        print(f"Draft created. ID: {draft.get('id')}")

                    mark_as_read(service, msg_id)
                    print("Marked as read.")

                    processed.add(msg_id)
                    state["processed_ids"] = list(processed)
                    save_state(state)

        except Exception as e:
            print("Error in watcher:", e)

        time.sleep(interval)


def send_email_interactive():
    to_email = input("Enter recipient email address: ").strip()
    if not to_email:
        print("No email entered. Aborting.")
        return

    relationship = input("Relationship (recruiter, friend, client, partner, etc): ").strip() or "unknown"
    mood = input("Tone / mood (professional, casual, happy, sad, love, etc): ").strip() or "professional"
    sender_name = input("Your name as it should appear in the email signature: ").strip() or None

    print("\nEnter email context (what you want to say).")
    print("Example: thank them for interview, restate interest, mention availability next week.")
    mail_context = input("Context: ").strip()

    if not mail_context:
        print("No context entered. Aborting.")
        return

    result = compose_email_from_context(
        context=mail_context,
        relationship=relationship,
        mood=mood,
        recipient_email=to_email,
        sender_name=sender_name,
    )

    # Safety: replace placeholders if the model still used them
    body_text = result.body
    if sender_name:
        body_text = body_text.replace("[Your Name]", sender_name).replace("Your Name", sender_name)

    print("\n=== Suggested Email ===")
    print("Class:", result.klass)
    print("Summary:", result.summary)
    print("\nSubject:")
    print(result.subject)
    print("\nBody:")
    print(body_text)
    print("=======================")

    confirm = input("\nSend this email? (y/n): ").strip().lower()
    if confirm != "y":
        print("Canceled. Email not sent.")
        return

    service = get_gmail_service()
    sent = send_new_email(service, to_email=to_email, subject=result.subject, body=body_text)
    print(f"Email sent. Gmail ID: {sent.get('id')}")


if __name__ == "__main__":
    print("What would you like to do?")
    print("1. Send Email")
    print("2. Watch Inbox and Auto-Reply")
    print()

    choice = input("Enter number of action here (1 or 2): ").strip()

    if choice == "1":
        send_email_interactive()
    elif choice == "2":
        watch_inbox(interval=2)
    else:
        print("Invalid choice. Exiting.")
