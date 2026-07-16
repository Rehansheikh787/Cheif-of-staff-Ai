import os
import re
import json
import time
import logging
import requests
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load dotenv from direct relative directories to support running from root workspace
triage_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(triage_dir, ".env"))
load_dotenv(os.path.join(os.path.dirname(triage_dir), ".env"))
load_dotenv()

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        _client = genai.Client(api_key=api_key)
    return _client

# ---------------------------------------------------------------------------
# Rate-limit configuration (Gemini free tier: 5 requests/minute)
# ---------------------------------------------------------------------------
RATE_LIMIT_BATCH_SIZE = 4   # Send this many requests before pausing
RATE_LIMIT_PAUSE_SECS = 62  # Pause duration to reset the per-minute quota


# Define Structured Output Schema
class TriageResult(BaseModel):
    priority: str = Field(description="Must be one of: urgent, needs-reply, fyi, ignore")
    category: str = Field(description="One short tag like: meeting-request, follow-up, newsletter, billing, job-app, social, admin")
    reason: str = Field(description="One sentence explaining why")

def triage_thread(sender: str, subject: str, snippet: str) -> dict:
    """Sends email metadata to Gemini to categorize and assess its priority. Falls back to Groq if Gemini fails."""
    prompt = f""" 
You are an intelligent email assistant helping triage an inbox. 

Given this email thread metadata, classify it: 

Sender: {sender}
Subject: {subject}
Preview: {snippet}
"""
    try:
        # Generate completion via Gemini-2.5-Flash with guaranteed JSON schema
        response = _get_client().models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=TriageResult,
            ),
        )
        # Parse guaranteed JSON response
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"Error during triage call for {sender}: {e}")
        
        # Groq Fallback
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if groq_api_key:
            logging.info("Attempting Groq fallback for email triage...")
            groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }
            system_instruction = (
                "You are an intelligent email assistant helping triage an inbox.\n"
                "Classify the given email thread metadata.\n"
                "You must respond ONLY with a JSON object matching this schema:\n"
                "{\n"
                '  "priority": "urgent" | "needs-reply" | "fyi" | "ignore",\n'
                '  "category": "meeting-request" | "follow-up" | "newsletter" | "billing" | "job-app" | "social" | "admin" | "other",\n'
                '  "reason": "One sentence explaining why"\n'
                "}"
            )
            payload = {
                "model": groq_model,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Sender: {sender}\nSubject: {subject}\nPreview: {snippet}"}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            }
            try:
                resp = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=10
                )
                resp.raise_for_status()
                result_json = resp.json()
                content = result_json["choices"][0]["message"]["content"]
                return json.loads(content)
            except Exception as groq_err:
                logging.error(f"Groq fallback failed during triage: {groq_err}")
                
        return _local_fallback_classify(sender, subject, snippet, e)


def _local_fallback_classify(sender: str, subject: str, snippet: str, error: Exception) -> dict:
    """Rule-based fallback classifier for sandbox/offline scenarios."""
    sender_lower = (sender or "").lower()
    subject_lower = (subject or "").lower()
    snippet_lower = (snippet or "").lower()

    def has_word(word, *texts):
        # Matches word as a whole or as part of email address domain/user
        pattern = rf"\b{re.escape(word)}\b"
        return any(re.search(pattern, text) for text in texts)

    if any(has_word(kw, sender_lower, subject_lower) for kw in ["boss", "manager", "director", "ceo", "urgent", "eod", "immediate"]):
        priority = "urgent"
        category = "follow-up"
        reason = f"Local Fallback: Authority/urgency keyword matched in sender/subject (API offline: {error})"
    elif any(has_word(kw, sender_lower, subject_lower) for kw in ["newsletter", "medium", "subscribe", "daily", "weekly", "digest"]):
        priority = "ignore"
        category = "newsletter"
        reason = f"Local Fallback: Newsletter or digest pattern detected (API offline: {error})"
    elif any(has_word(kw, sender_lower, subject_lower, snippet_lower) for kw in ["recruiter", "interview", "call", "schedule", "connect", "sync"]):
        priority = "needs-reply"
        category = "meeting-request"
        reason = f"Local Fallback: Meeting request or outreach context matched (API offline: {error})"
    elif any(has_word(kw, sender_lower, subject_lower, snippet_lower) for kw in ["invoice", "billing", "receipt", "payment", "charge"]):
        priority = "needs-reply"
        category = "billing"
        reason = f"Local Fallback: Financial or billing transaction keyword matched (API offline: {error})"
    elif any(has_word(kw, sender_lower, subject_lower) for kw in ["social", "linkedin", "facebook", "twitter", "notification"]):
        priority = "fyi"
        category = "social"
        reason = f"Local Fallback: Social media platform update (API offline: {error})"
    else:
        priority = "fyi"
        category = "admin"
        reason = f"Local Fallback: General email triage category fallback (API offline: {error})"

    return {"priority": priority, "category": category, "reason": reason}


def triage_inbox(threads: list) -> list:
    """Triages a batch list of email threads and sorts them by priority hierarchy.
    
    Includes rate-limit awareness: pauses every RATE_LIMIT_BATCH_SIZE requests
    to stay within the Gemini free tier quota (5 req/min). Can be bypassed by setting
    DISABLE_RATE_LIMIT_PAUSE=true in environment or .env.
    """
    triaged = []
    disable_pause = os.environ.get("DISABLE_RATE_LIMIT_PAUSE", "false").lower() in ("true", "1", "yes")

    for i, thread in enumerate(threads):
        # Rate-limit: pause after every batch to avoid 429 errors
        if not disable_pause and i > 0 and i % RATE_LIMIT_BATCH_SIZE == 0:
            logging.info(
                f"Rate limit pause: processed {i}/{len(threads)} threads. "
                f"Waiting {RATE_LIMIT_PAUSE_SECS}s for quota reset..."
            )
            time.sleep(RATE_LIMIT_PAUSE_SECS)

        # Query individual metric classification parameters
        label = triage_thread(
            sender=thread["sender"],
            subject=thread["subject"],
            snippet=thread["snippet"]
        )
        # Merge source metadata properties safely with the classification dict
        triaged.append({**thread, **label})

    # Predefined strict prioritization sorting scale mapping values
    priority_order = {"urgent": 0, "needs-reply": 1, "fyi": 2, "ignore": 3, "unknown": 4}

    # Sort in-place using key-mapping retrieval fallback
    triaged.sort(key=lambda x: priority_order.get(x.get("priority", "unknown"), 4))

    return triaged

# Sample Execution Logic (Derived from Pages 11–14)
if __name__ == "__main__":
    sample_threads = [
        {
            "sender": "boss@company.com",
            "subject": "Need your input by EOD",
            "snippet": "Can you review the attached proposal before 5pm?"
        },
        {
            "sender": "newsletter@medium.com",
            "subject": "Top stories for you this week",
            "snippet": "Here's what's trending in tech..."
        },
        {
            "sender": "recruiter@startup.io",
            "subject": "Quick call this week",
            "snippet": "Hi, I came across your profile and wanted to connect..."
        }
    ]

    print("Triaging inbox threads...")
    results = triage_inbox(sample_threads)

    print("\nTriage Results Summary:")
    for thread in results:
        print(f"[{thread['priority'].upper()}] Category: {thread['category']} | Subj: {thread['subject']}")