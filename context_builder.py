"""
context_builder.py — Assembles the full prompt context for the email reply
drafting agent.

Loads the user's tone profile and past reply examples, formats an email
thread into a readable conversation string, and builds a system + user
prompt pair ready to send to the LLM.
"""

import json
import os
from typing import Any

# All file paths are resolved relative to this module's directory
_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 1. Load tone profile
# ---------------------------------------------------------------------------

def load_tone_profile(path: str = "tone_profile.json") -> dict:
    """Read and return the tone profile dict from a JSON file.

    Args:
        path: Relative or absolute path to the tone profile JSON.
              Defaults to ``tone_profile.json`` in the project root.

    Returns:
        dict with keys like name, role, tone, formality, quirks, etc.
    """
    if not os.path.isabs(path):
        path = os.path.join(_DIR, path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. Load past replies
# ---------------------------------------------------------------------------

def load_past_replies(path: str = "past_replies.json") -> list[dict]:
    """Read and return the list of past reply examples from a JSON file.

    Args:
        path: Relative or absolute path to the past-replies JSON.
              Defaults to ``past_replies.json`` in the project root.

    Returns:
        List of dicts, each with subject, to, and body.
    """
    if not os.path.isabs(path):
        path = os.path.join(_DIR, path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 3. Format thread history
# ---------------------------------------------------------------------------

def format_thread_history(thread: dict) -> str:
    """Convert a thread dict into a human-readable conversation string.

    Args:
        thread: dict with keys:
            - "subject" (str): The email subject line
            - "messages" (list[dict]): Each message has "from", "date", "body"

    Returns:
        A formatted multi-line string showing who said what, in order.

    Example output::

        Subject: Q3 roadmap finalization
        ──────────────────────────────────────────
        [1] From: Alice <alice@co.com>
            Date: Mon, 15 Jun 2026 09:00
            ─
            Hey team, here's the draft…

        [2] From: Bob <bob@co.com>
            Date: Mon, 15 Jun 2026 10:30
            ─
            Looks good — one question…
    """
    lines: list[str] = []

    subject = thread.get("subject", "(no subject)")
    lines.append(f"Subject: {subject}")
    lines.append("-" * 50)

    messages = thread.get("messages", [])
    for idx, msg in enumerate(messages, 1):
        sender = msg.get("from", "Unknown")
        date = msg.get("date", "")
        body = msg.get("body", "").strip()

        lines.append(f"\n[{idx}] From: {sender}")
        if date:
            lines.append(f"    Date: {date}")
        lines.append("    --")
        # Indent each line of the body for readability
        for body_line in body.splitlines():
            lines.append(f"    {body_line}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. Build system prompt
# ---------------------------------------------------------------------------

def build_system_prompt(tone_profile: dict, past_replies: list[dict]) -> str:
    """Build the system prompt that defines the agent's persona and writing rules.

    The prompt includes:
    - The persona: name, role, tone, formality
    - Writing rules derived from the quirks list
    - 2-3 past reply examples so the model can mirror the user's voice

    Args:
        tone_profile: dict returned by :func:`load_tone_profile`.
        past_replies: list returned by :func:`load_past_replies`.

    Returns:
        A fully-formed system prompt string.
    """
    name = tone_profile.get("name", "the user")
    role = tone_profile.get("role", "professional")
    tone = tone_profile.get("tone", "neutral")
    formality = tone_profile.get("formality", "formal")
    sign_off = tone_profile.get("sign_off", "Best")
    quirks = tone_profile.get("quirks", [])
    vocab = tone_profile.get("vocabulary_preferences", {})

    # --- Persona section ---
    persona_block = (
        f"You are a ghostwriter drafting email replies on behalf of "
        f"**{name}**, a {role}.\n"
        f"- Tone: {tone}\n"
        f"- Formality level: {formality}\n"
        f"- Default sign-off: \"{sign_off}\"\n"
    )

    # --- Writing rules section ---
    rules_lines = ["## Writing Rules"]
    for i, quirk in enumerate(quirks, 1):
        rules_lines.append(f"{i}. {quirk}")

    if vocab.get("use"):
        rules_lines.append(
            f"\n**Preferred vocabulary:** {', '.join(vocab['use'])}"
        )
    if vocab.get("avoid"):
        rules_lines.append(
            f"**Avoid these phrases:** {', '.join(vocab['avoid'])}"
        )

    rules_block = "\n".join(rules_lines)

    # --- Past examples section (use up to 3) ---
    examples_lines = [f"\n## Here's how {name} writes:"]
    for reply in past_replies[:3]:
        subj = reply.get("subject", "")
        to = reply.get("to", "")
        body = reply.get("body", "")
        examples_lines.append(f"\n**{subj}** (to {to}):")
        examples_lines.append(f"```\n{body}\n```")

    examples_block = "\n".join(examples_lines)

    # --- Assemble ---
    system_prompt = (
        f"{persona_block}\n"
        f"{rules_block}\n"
        f"{examples_block}\n\n"
        f"---\n"
        f"When drafting a reply, match {name}'s voice exactly. "
        f"Keep it concise, genuine, and action-oriented. "
        f"Always end with a clear next step or ask."
    )

    return system_prompt


# ---------------------------------------------------------------------------
# 5. Build user prompt
# ---------------------------------------------------------------------------

def build_user_prompt(thread_formatted: str) -> str:
    """Build the user message asking the agent to draft a reply.

    Args:
        thread_formatted: The output of :func:`format_thread_history`.

    Returns:
        A user-prompt string containing the thread and a clear instruction.
    """
    return (
        f"Here is the email thread I need to reply to:\n\n"
        f"{thread_formatted}\n\n"
        f"---\n"
        f"Draft a reply to the most recent message in this thread. "
        f"Match my writing style exactly -- keep the tone, length, and "
        f"structure consistent with how I usually write. "
        f"Do NOT include a subject line; just write the body of the reply."
    )


# ---------------------------------------------------------------------------
# 6. Assemble context (main orchestrator)
# ---------------------------------------------------------------------------

def assemble_context(
    thread: dict,
    tone_path: str = "tone_profile.json",
    replies_path: str = "past_replies.json",
) -> dict[str, str]:
    """Load everything and return the final prompt context.

    This is the main entry-point. Given a thread dict, it:
    1. Loads the tone profile
    2. Loads past reply examples
    3. Formats the thread history
    4. Builds the system and user prompts

    Args:
        thread: dict with "subject" and "messages" (list of {from, date, body}).
        tone_path: Path to tone_profile.json.
        replies_path: Path to past_replies.json.

    Returns:
        dict with two keys:
            - "system": The full system prompt (persona + rules + examples)
            - "user":   The user prompt (thread + drafting instruction)
    """
    tone_profile = load_tone_profile(tone_path)
    past_replies = load_past_replies(replies_path)

    thread_formatted = format_thread_history(thread)

    system_prompt = build_system_prompt(tone_profile, past_replies)
    user_prompt = build_user_prompt(thread_formatted)

    return {
        "system": system_prompt,
        "user": user_prompt,
    }


# ---------------------------------------------------------------------------
# Demo — print the assembled prompt
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Sample thread to demonstrate the context builder
    sample_thread = {
        "subject": "Re: Beta launch timeline update",
        "messages": [
            {
                "from": "Priya Sharma <priya@company.com>",
                "date": "Mon, 16 Jun 2026 09:15",
                "body": (
                    "Hi Rahul,\n\n"
                    "Quick update — the eng team flagged a blocker on the "
                    "payment integration. They need an extra 3 days to sort "
                    "out the Stripe webhook handling.\n\n"
                    "This pushes our beta from Jun 20 to Jun 23. I wanted to "
                    "flag this before the stakeholder sync tomorrow.\n\n"
                    "Should I update the project tracker, or do you want to "
                    "discuss first?\n\n"
                    "Thanks,\nPriya"
                ),
            },
            {
                "from": "Anil Kapoor <anil@company.com>",
                "date": "Mon, 16 Jun 2026 10:02",
                "body": (
                    "Adding context — the webhook issue is with retry logic "
                    "on failed charges. We've got a fix in review but QA "
                    "needs time to validate edge cases.\n\n"
                    "Happy to jump on a call if that helps.\n\n"
                    "– Anil"
                ),
            },
        ],
    }

    context = assemble_context(sample_thread)

    print("=" * 80)
    print("SYSTEM PROMPT")
    print("=" * 80)
    print(context["system"])
    print()
    print("=" * 80)
    print("USER PROMPT")
    print("=" * 80)
    print(context["user"])
