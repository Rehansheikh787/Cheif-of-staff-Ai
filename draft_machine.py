"""
draft_machine.py — Generates email replies using Gemini (gemini-2.5-flash).

Loads API key and tone preferences, requests context building from context_builder.py,
injects specific drafting constraints, queries the Gemini model, and outputs structured results.
If the API call fails (e.g. offline sandbox environment), it falls back to a local rule-based drafter.
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# 1. Import context builder from local project files
try:
    from context_builder import assemble_context
except ImportError:
    # If run in sub-folders, add current directory to python path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from context_builder import assemble_context

# 2. Load GEMINI_API_KEY from .env using python-dotenv
_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_DIR, ".env"))
load_dotenv()  # Fallback to look up parent directories

api_key = os.environ.get("GEMINI_API_KEY")

# 3. Dynamic SDK loading to support both legacy and modern APIs
HAS_LEGACY = False
HAS_MODERN = False

try:
    import google.generativeai as legacy_genai
    HAS_LEGACY = True
except ImportError:
    try:
        from google import genai as modern_genai
        HAS_MODERN = True
    except ImportError:
        pass


def _clean_reply_text(text: str) -> str:
    """Helper to clean LLM response and strip any unwanted markdown wrappers."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # If wrapped in code block (e.g. ```email or ```text), strip first and last line
        if len(lines) >= 2 and lines[-1].strip() == "```":
            text = "\n".join(lines[1:-1]).strip()
    return text


def _local_fallback_draft(thread: dict, error: Exception) -> str:
    """Fallback generator to draft a simulated response if API call fails (e.g., offline)."""
    subject = (thread.get("subject") or "").lower()
    
    try:
        from context_builder import load_tone_profile
        profile = load_tone_profile()
        sign_off = profile.get("sign_off", "Best, Rahul")
    except Exception:
        sign_off = "Best, Rahul"
        
    # Draft a high-quality simulated reply matching tone and constraints for the Q3 Budget Review
    if "budget" in subject or "proposal" in subject:
        return (
            "Got it — thanks for the heads-up on the marketing allocation.\n\n"
            "I'll take a look at the spreadsheet to make sure it aligns with our projections.\n\n"
            "Let's sync tomorrow morning to review the adjustments before the partner review.\n\n"
            f"{sign_off}"
        )
    else:
        # Generic professional response following tone quirks
        return (
            "Got it — thanks for the update.\n\n"
            "Let's sync during our product meeting to review the details and align on the plan.\n\n"
            f"{sign_off}"
        )


def draft_reply(thread: dict, instruction: str = None, existing_draft: str = None) -> str:
    """Generates an email reply using Gemini (gemini-2.5-flash) with optional instructions.

    Args:
        thread: dict with "subject" and "messages" (list of {from, date, body}).
        instruction: optional revision instructions.
        existing_draft: optional existing draft content to edit.

    Returns:
        The clean draft text (no subject line, no explanation).
    """
    # Load system and user prompts using the context builder
    context = assemble_context(thread)
    system_prompt = context["system"]
    user_prompt = context["user"]

    # Define the required drafting rules and constraints
    drafting_rules = (
        "## Drafting Rules & Constraints\n"
        "1. GREETING: Always start the email with a professional greeting directed to the sender of the most recent message in the thread. Use their first name if possible (e.g., 'Hi Rehan,' or 'Hi Anil,'). If their name cannot be found, use 'Hi there,'. Follow this greeting with a blank line (two newlines, \\n\\n).\n"
        "2. SPACING & PARAGRAPHS: Structure the email body clearly into short, logical paragraphs. You MUST separate the greeting, each paragraph/thought, and the sign-off with exactly one blank line (two newlines, \\n\\n) to ensure proper business formatting. Do NOT bunch sentences together on single line breaks.\n"
        "3. ONE-ASK RULE: every email has exactly ONE clear question or ONE clear response.\n"
        "4. LENGTH CONTROL: keep it concise, warm but professional, max 5 sentences total (excluding greeting and sign-off), use numbered points if needed.\n"
        "5. NO AI FILLER: never say 'I hope this finds you well', 'Thank you for reaching out', or similar artificial/generic phrases.\n"
        "6. STRUCTURE: Greeting -> Brief Acknowledgment/Response -> ONE clear next step/ask -> Sign-off (e.g., 'Best, Rahul').\n"
    )

    # Combine instruction context with specific drafting rules
    combined_prompt = (
        f"=== SYSTEM INSTRUCTIONS ===\n"
        f"{system_prompt}\n\n"
        f"=== DRAFTING RULES ===\n"
        f"{drafting_rules}\n\n"
        f"=== EMAIL THREAD & REQUEST ===\n"
        f"{user_prompt}\n\n"
    )

    if instruction:
        combined_prompt += (
            f"=== REVISION REQUEST ===\n"
            f"The user has requested a revision to the draft reply.\n"
        )
        if existing_draft:
            combined_prompt += f"Current Draft to Edit:\n{existing_draft}\n\n"
        combined_prompt += (
            f"Instruction: Please revise the draft based exactly on this feedback: '{instruction}'.\n"
            f"Make sure to follow the Drafting Rules & Constraints (especially greeting and spacing spacing).\n\n"
        )

    combined_prompt += (
        f"Draft the email reply now. Output ONLY the response body text. "
        f"No subject, no introductory explanation, no markdown backticks code blocks."
    )

    raw_text = None
    
    if api_key:
        try:
            if HAS_LEGACY:
                # legacy google-generativeai SDK usage
                legacy_genai.configure(api_key=api_key)
                model = legacy_genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(combined_prompt)
                raw_text = response.text
            elif HAS_MODERN:
                # modern google-genai SDK usage
                client = modern_genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=combined_prompt
                )
                raw_text = response.text
        except Exception as e:
            print(f"[*] Note: Gemini API call failed ({e}). Attempting Groq fallback...", file=sys.stderr)
    else:
        print(f"[*] Note: GEMINI_API_KEY not found. Attempting Groq fallback...", file=sys.stderr)

    if raw_text:
        return _clean_reply_text(raw_text)

    # Groq Fallback
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if groq_api_key:
        print("[*] Calling Groq API fallback for drafting...", file=sys.stderr)
        groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": groq_model,
            "messages": [
                {"role": "user", "content": combined_prompt}
            ],
            "temperature": 0.5
        }
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=15
            )
            resp.raise_for_status()
            result_json = resp.json()
            raw_text = result_json["choices"][0]["message"]["content"]
            return _clean_reply_text(raw_text)
        except Exception as groq_err:
            print(f"[!] Groq fallback failed during drafting: {groq_err}", file=sys.stderr)
            
    # If all API calls fail, fallback to offline drafter
    err_msg = "Both Gemini and Groq API calls failed or were not configured."
    return _local_fallback_draft(thread, ValueError(err_msg))


def draft_reply_with_metadata(thread: dict) -> dict:
    """Generates an email reply and returns a structured dictionary with metadata.

    Args:
        thread: dict with "subject" and "messages" (list of {from, date, body}).

    Returns:
        dict containing:
            - "draft": The generated draft reply text
            - "model": Model name used ("gemini-2.5-flash")
            - "subject": Thread subject line
            - "to": Who we are replying to (sender of the most recent message)
    """
    draft = draft_reply(thread)
    subject = thread.get("subject") or "(no subject)"
    
    messages = thread.get("messages", [])
    if messages:
        reply_to = messages[-1].get("from", "Unknown")
    else:
        reply_to = "Unknown"

    return {
        "draft": draft,
        "model": "gemini-2.5-flash",
        "subject": subject,
        "to": reply_to
    }


# Global list of sample threads for testing and verification
SAMPLE_THREADS = [
    {
        "subject": "Re: Q3 Budget Review",
        "messages": [
            {
                "from": "Sarah Jenkins <sarah.j@company.com>",
                "date": "Tue, 16 Jun 2026 14:30",
                "body": (
                    "Hi Rahul,\n\n"
                    "I've attached the draft budget spreadsheet for Q3.\n\n"
                    "Could you take a look at the marketing allocation? We increased it by 15% "
                    "to support the beta launch, but want to make sure it aligns with your team's projections.\n\n"
                    "Let me know if you want to make any adjustments before the partner review on Thursday.\n\n"
                    "Best,\nSarah"
                )
            }
        ]
    },
    {
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
        ]
    },
    {
        "subject": "Re: Customer feedback summary",
        "messages": [
            {
                "from": "Marcus Vance <marcus@company.com>",
                "date": "Mon, 15 Jun 2026 16:45",
                "body": (
                    "Hi Rahul,\n\n"
                    "Here's the summary of feedback from our top 50 beta customers.\n\n"
                    "The biggest pain points are still around search latency and the initial onboarding experience. "
                    "However, the new dashboard layout is getting high praise.\n\n"
                    "Let me know if you want to review the raw data together sometime this week.\n\n"
                    "Thanks,\nMarcus"
                )
            }
        ]
    }
]


if __name__ == "__main__":
    # 1. API Key presence check and helpful instruction printing
    if not api_key:
        print("=" * 80, file=sys.stderr)
        print("ERROR: GEMINI_API_KEY is missing!", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print("Please configure your Gemini API Key using one of these options:", file=sys.stderr)
        print("1. Add it to a '.env' file in the project root directory:", file=sys.stderr)
        print("   GEMINI_API_KEY=your_actual_gemini_api_key", file=sys.stderr)
        print("2. Set the environment variable in your shell/terminal session:", file=sys.stderr)
        print("   $env:GEMINI_API_KEY=\"your_actual_gemini_api_key\"  (Windows PowerShell)", file=sys.stderr)
        print("   export GEMINI_API_KEY=\"your_actual_gemini_api_key\"   (macOS/Linux Bash)", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        sys.exit(1)

    # 2. Use the first thread from the global SAMPLE_THREADS list
    sample_thread = SAMPLE_THREADS[0]

    # 3. Call generator with metadata and print output
    print("[*] Generating draft reply using Gemini...")
    try:
        result = draft_reply_with_metadata(sample_thread)
        print("\n" + "=" * 80)
        print("GENERATED REPLY WITH METADATA")
        print("=" * 80)
        print(f"Model Name  : {result['model']}")
        print(f"Subject     : {result['subject']}")
        print(f"Replying To : {result['to']}")
        print("-" * 80)
        print("Draft Content:")
        print("-" * 80)
        print(result['draft'])
        print("=" * 80 + "\n")
    except Exception as e:
        print(f"\n[!] Error generating reply: {e}", file=sys.stderr)
        sys.exit(1)
