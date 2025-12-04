import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EmailClass = Literal["URGENT", "IMPORTANT", "INFO ONLY", "SPAM / MARKETING"]

# ===== Results for incoming-email butler =====

@dataclass
class ButlerResult:
    klass: EmailClass
    summary: str
    draft_reply: str


# ===== Results for user-initiated email composer =====

@dataclass
class EmailComposerResult:
    klass: EmailClass
    summary: str
    subject: str
    body: str


# ====== 1. Incoming email butler ======

MASTER_INSTRUCTION = """
You are an AI Email Butler.

Given an email (subject, sender, and body), you must:
1. Classify the email into EXACTLY ONE of:
   - URGENT
   - IMPORTANT
   - INFO ONLY
   - SPAM / MARKETING

2. Write a 2–3 sentence human-friendly summary.

3. Draft a short, polite reply in plain English. Keep the tone neutral-professional
   unless the email clearly has a specific tone.

Return your response in the following exact text format:

CLASS:
<one of URGENT / IMPORTANT / INFO ONLY / SPAM / MARKETING>

SUMMARY:
<summary text here>

DRAFT REPLY:
<reply text here>
""".strip()


def build_user_prompt(subject: str, sender: str, body: str) -> str:
    return f"""Here is the email:

SUBJECT: {subject}
FROM: {sender}

BODY:
{body}
"""


def call_email_butler(subject: str, sender: str, body: str) -> ButlerResult:
    user_prompt = build_user_prompt(subject, sender, body)

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": MASTER_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )

    content = resp.choices[0].message.content or ""
    klass = ""
    summary = ""
    draft = ""

    lines = [l.strip() for l in content.splitlines() if l.strip()]
    current_section = None

    for line in lines:
        if line.startswith("CLASS:"):
            current_section = "class"
            continue
        elif line.startswith("SUMMARY:"):
            current_section = "summary"
            continue
        elif line.startswith("DRAFT REPLY:"):
            current_section = "draft"
            continue

        if current_section == "class":
            klass = line.upper()
        elif current_section == "summary":
            summary += line + " "
        elif current_section == "draft":
            draft += line + "\n"

    return ButlerResult(
        klass=klass or "INFO ONLY",
        summary=summary.strip(),
        draft_reply=draft.strip(),
    )


# ====== 2. User-initiated email composer (mood-aware) ======

EMAIL_COMPOSER_INSTRUCTION = """
You are an AI Email Composer.

The user will provide:
- The context of the email (what they want to say or achieve),
- The relationship to the recipient (e.g., recruiter, friend, partner, client),
- The desired tone/mood: for example "professional", "casual", "happy", "sad",
  "loving", "love", "romantic", etc.
- The sender's name (SENDER_NAME), which must be used in the signature.

Your job:

1. Decide the appropriate IMPORTANCE class for this email:
   - URGENT
   - IMPORTANT
   - INFO ONLY
   - SPAM / MARKETING  (rarely used here; only if it is obviously junk)

2. Write a 1–2 sentence summary of what this outgoing email is about.

3. Generate:
   - A strong, concise SUBJECT line.
   - A well-structured BODY that matches the requested mood/tone.

    BODY FORMAT RULES:
    The email MUST follow this exact structure:
    1. A greeting on its own line. Example:
    Dear Recruiter,
    (then one blank line)

    2. First paragraph (2–4 short sentences) on its own block.
    (then one blank line)

    3. Second paragraph (optional, 2–4 short sentences).
    (then one blank line)

    4. A closing sentence that fits the mode selected.

    5. Closing line that suits the mode selected.

    6. Sender name on its own line.

    Hard rules:
    - A blank line MUST appear between every block.
    - No paragraph should be directly under another without a blank line.
    - Do NOT combine paragraphs.
    - Do NOT indent paragraphs. Gmail ignores indentation; spacing must be done using blank lines.
    - The final result MUST look exactly like this spacing style:


Tone rules:
- "professional": clear, polite, concise, no slang.
- "casual": friendly, relaxed, light slang is acceptable.
- "happy": warm, positive, upbeat.
- "sad": gentle, empathetic, respectful.
- "love"/"loving"/"romantic": affectionate, warm, emotionally expressive,
  but still respectful.
- If the tone is unknown, default to professional.

Return your response in the following exact text format:

CLASS:
<one of URGENT / IMPORTANT / INFO ONLY / SPAM / MARKETING>

SUMMARY:
<summary text here>

SUBJECT:
<subject line here>

BODY:
<body text here, following the BODY FORMAT RULES above>
""".strip()



def build_composer_prompt(
    context: str,
    relationship: str,
    mood: str,
    recipient_email: str | None = None,
    sender_name: str | None = None,
) -> str:
    return f"""Here is the request for an outgoing email.

RECIPIENT_RELATIONSHIP: {relationship}
RECIPIENT_EMAIL: {recipient_email or "unknown"}
DESIRED_TONE_OR_MOOD: {mood}
SENDER_NAME: {sender_name or "Unknown Sender"}

CONTEXT:
{context}
"""




def format_email_body(body: str) -> str:
    """
    Reformat model output into a clean email layout:

    Dear Recruiter,

    First paragraph...

    Second paragraph...

    Thank you...

    Best regards,
    Patrick
    """
    # Normalize newlines
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = [l.rstrip() for l in body.split("\n")]

    # Remove leading/trailing empty lines
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    if not lines:
        return ""

    # First non-empty line = greeting
    greeting = lines[0]
    rest = lines[1:]

    if not rest:
        return greeting

    # Find "thank you" style line in the rest
    thanks_idx = None
    for i, line in enumerate(rest):
        low = line.lower()
        if "thank you" in low or low.startswith("thanks"):
            thanks_idx = i
            break

    if thanks_idx is not None:
        main_para_lines = rest[:thanks_idx]
        closing_thanks_line = rest[thanks_idx]
        closing_salutation_lines = rest[thanks_idx + 1 :]
    else:
        # Fallback: assume last 2 lines are closing and name
        if len(rest) >= 3:
            main_para_lines = rest[:-2]
            closing_thanks_line = ""
            closing_salutation_lines = rest[-2:]
        else:
            main_para_lines = rest
            closing_thanks_line = ""
            closing_salutation_lines = []

    # Collapse main paragraph lines into one block
    main_para = " ".join(l.strip() for l in main_para_lines if l.strip())

    new_lines: list[str] = []

    # Greeting
    new_lines.append(greeting)
    new_lines.append("")

    # Main paragraph block
    if main_para:
        new_lines.append(main_para)
        new_lines.append("")

    # "Thank you..." block
    if closing_thanks_line:
        new_lines.append(closing_thanks_line.strip())
        new_lines.append("")

    # Closing + name
    for l in closing_salutation_lines:
        if l.strip():
            new_lines.append(l.strip())

    # Remove accidental extra blank lines
    out = "\n".join(new_lines)
    while "\n\n\n" in out:
        out = out.replace("\n\n\n", "\n\n")
    return out.strip()



def compose_email_from_context(
    context: str,
    relationship: str,
    mood: str,
    recipient_email: str | None = None,
    sender_name: str | None = None,
) -> EmailComposerResult:
    user_prompt = build_composer_prompt(
        context=context,
        relationship=relationship,
        mood=mood,
        recipient_email=recipient_email,
        sender_name=sender_name,
    )

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": EMAIL_COMPOSER_INSTRUCTION},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
    )

    content = resp.choices[0].message.content or ""
    klass = ""
    summary = ""
    subject = ""
    body = ""

    lines = [l.strip() for l in content.splitlines() if l.strip()]
    current_section = None

    for line in lines:
        if line.startswith("CLASS:"):
            current_section = "class"
            continue
        elif line.startswith("SUMMARY:"):
            current_section = "summary"
            continue
        elif line.startswith("SUBJECT:"):
            current_section = "subject"
            continue
        elif line.startswith("BODY:"):
            current_section = "body"
            continue

        if current_section == "class":
            klass = line.upper()
        elif current_section == "summary":
            summary += line + " "
        elif current_section == "subject":
            subject += line + " "
        elif current_section == "body":
            body += line + "\n"

    # Ensure real name is used if the model left placeholders
    if sender_name:
        body = body.replace("[Your Name]", sender_name).replace("Your Name", sender_name)

    # Enforce the exact spacing format you want
    body = format_email_body(body)

    return EmailComposerResult(
        klass=klass or "INFO ONLY",
        summary=summary.strip(),
        subject=subject.strip(),
        body=body.strip(),
    )

