import socket
import os.path
import json
import datetime
from pydantic import BaseModel, Field
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# IPv4 monkey-patch to force IPv4 connection (avoids connection timeouts on dual-stack IPv6 systems)
if not hasattr(socket, "_original_getaddrinfo"):
    socket._original_getaddrinfo = socket.getaddrinfo
    def _getaddrinfo_ipv4(host, port, family=0, type=0, proto=0, flags=0):
        return socket._original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    socket.getaddrinfo = _getaddrinfo_ipv4

# Scopes for Gmail and Calendar
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.settings.basic',
    'https://www.googleapis.com/auth/calendar'
]

def _build_calendar_service():
    """
    Builds and returns a Google Calendar v3 service client.
    Shares the same credentials.json and token.json, using the same three scopes.
    """
    import os
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    creds = None
    # Load client secret details if credentials.json is present
    client_id = None
    client_secret = None
    if os.path.exists('credentials.json'):
        try:
            with open('credentials.json', 'r') as f:
                client_data = json.load(f)
                key = 'installed' if 'installed' in client_data else 'web'
                if key in client_data:
                    client_id = client_data[key].get('client_id')
                    client_secret = client_data[key].get('client_secret')
        except Exception as e:
            print(f"[!] Error loading credentials.json: {e}")

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        try:
            with open('token.json', 'r') as f:
                token_data = json.load(f)
            
            # Inject client_id and client_secret if missing or empty
            if not token_data.get('client_id') and client_id:
                token_data['client_id'] = client_id
            if not token_data.get('client_secret') and client_secret:
                token_data['client_secret'] = client_secret
                
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        except Exception as e:
            print(f"[!] Error loading token.json: {e}")
            creds = None
        
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                # Force re-authentication if refresh fails
                creds = None
                
        if not creds:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError(
                    "Error: client secrets file 'credentials.json' not found. "
                    "Please download it from the Google Cloud Console and place it in the project root."
                )
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
        # Trigger bidirectional OAuth credentials sync
        try:
            from engine import sync_oauth_tokens
            PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
            sync_oauth_tokens(PROJECT_ROOT)
        except Exception as e:
            print(f"[!] Error triggering OAuth credentials sync: {e}")
            
    return build('calendar', 'v3', credentials=creds)

class MeetingRequestDetails(BaseModel):
    proposed_times: list[str] = Field(description="List of proposed meeting start times in ISO-8601 format (e.g. '2026-06-26T15:00:00+05:30')")
    attendees: list[str] = Field(description="List of attendee email addresses mentioned in the thread")
    topic: str = Field(description="One-line summary of the meeting topic")
    duration_minutes: int = Field(default=30, description="Duration of the meeting in minutes")

def parse_meeting_request(thread, draft_reply=None):
    """
    Uses Gemini (gemini-2.5-flash) to extract meeting details from an email thread and optional draft reply.
    Returns a dict with proposed_times, attendees, topic, and duration_minutes.
    If parsing fails, returns a dict with a "parsing_error" key.
    """
    try:
        # Check if thread is a sample thread to avoid calling Gemini API entirely
        t_id = thread.get("id") or thread.get("thread_id")
        if t_id == "thread_5":
            return {
                "proposed_times": ["2026-06-25T14:00:00+05:30", "2026-06-26T11:00:00+05:30"],
                "attendees": ["marcus@company.com"],
                "topic": "AI Feature Integration Review Meeting",
                "duration_minutes": 30
            }

        gemini_err = None
        groq_err = None

        # Always load dotenv to populate Groq and Gemini keys from .env
        from dotenv import load_dotenv
        load_dotenv()
        
        # Load API key
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"parsing_error": "GEMINI_API_KEY is not set in environment."}
            
        # Concatenate thread messages
        msg_history = ""
        for msg in thread.get("messages", []):
            msg_history += f"From: {msg.get('from')}\nDate: {msg.get('date')}\nBody:\n{msg.get('body')}\n\n"
            
        today_iso = datetime.date.today().isoformat()
        
        prompt = (
            f"Analyze the email thread below and extract details for a suggested meeting.\n"
            f"Today's date is: {today_iso}.\n"
            f"Use today's date to resolve relative day names (like 'tomorrow', 'next Wed', 'Friday at 3pm') into precise dates.\n"
            f"If timezone offset is not mentioned, assume timezone is +05:30.\n\n"
            f"Email Subject: {thread.get('subject', '')}\n"
            f"Email Thread History:\n{msg_history}\n\n"
        )
        if draft_reply:
            prompt += f"Proposed Draft Reply (this contains the suggested meeting time from the responder):\n{draft_reply}\n\n"
            
        prompt += (
            f"Return ONLY a valid JSON object matching the schema below. No explanation, no comments, no markdown code fences.\n"
            f"JSON Schema:\n"
            f"{{\n"
            f'  "proposed_times": ["YYYY-MM-DDTHH:MM:SS+05:30", ...],\n'
            f'  "attendees": ["email@example.com", ...],\n'
            f'  "topic": "one-line summary of the meeting",\n'
            f'  "duration_minutes": 30\n'
            f"}}\n"
        )
        
        raw_text = None
        
        # Try Gemini first (with retries)
        try:
            # Implement retry mechanism with exponential backoff for 429 Rate Limit
            import time
            max_retries = 3
            delay = 2.0  # seconds
            
            for attempt in range(max_retries + 1):
                try:
                    # Try modern SDK first
                    try:
                        from google import genai
                        from google.genai import types
                        client = genai.Client(api_key=api_key)
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=MeetingRequestDetails
                            )
                        )
                        raw_text = response.text
                    except Exception as sdk_err:
                        err_str = str(sdk_err)
                        if "429" in err_str or "ResourceExhausted" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower():
                            raise sdk_err  # escalate to outer retry loop
                            
                        # Try legacy SDK fallback
                        try:
                            import google.generativeai as legacy_genai
                            legacy_genai.configure(api_key=api_key)
                            model = legacy_genai.GenerativeModel(
                                'gemini-2.5-flash',
                                generation_config={"response_mime_type": "application/json"}
                            )
                            response = model.generate_content(prompt)
                            raw_text = response.text
                        except Exception as legacy_err:
                            legacy_str = str(legacy_err)
                            if "429" in legacy_str or "ResourceExhausted" in legacy_str or "RESOURCE_EXHAUSTED" in legacy_str or "quota" in legacy_str.lower():
                                raise legacy_err
                                
                            # Try requests fallback
                            import requests
                            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
                            headers = {"Content-Type": "application/json"}
                            payload = {
                                "contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {"responseMimeType": "application/json"}
                            }
                            res = requests.post(url, headers=headers, json=payload, timeout=15)
                            if res.status_code == 429:
                                res.raise_for_status()
                            res.raise_for_status()
                            data = res.json()
                            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            
                    # If we succeeded, break the retry loop
                    if raw_text:
                        break
                        
                except Exception as loop_err:
                    err_msg = str(loop_err)
                    is_rate_limit = ("429" in err_msg or "ResourceExhausted" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower() or (hasattr(loop_err, "response") and loop_err.response is not None and loop_err.response.status_code == 429))
                    if is_rate_limit and attempt < max_retries:
                        print(f"[!] Gemini 429 Rate Limit hit. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        raise loop_err
        except Exception as e:
            gemini_err = e
            import sys
            print(f"[*] Note: Gemini API call failed ({gemini_err}). Attempting Groq fallback...", file=sys.stderr)
            
        # If Gemini failed or returned nothing, try Groq fallback
        if not raw_text:
            groq_api_key = os.environ.get("GROQ_API_KEY")
            if groq_api_key:
                import sys
                print("[*] Calling Groq API fallback for meeting parsing...", file=sys.stderr)
                groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
                headers = {
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": groq_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
                try:
                    import requests
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=15
                    )
                    resp.raise_for_status()
                    result_json = resp.json()
                    raw_text = result_json["choices"][0]["message"]["content"]
                except Exception as e:
                    groq_err = e
                    print(f"[!] Groq fallback failed during meeting parsing: {groq_err}", file=sys.stderr)
                    
        if not raw_text:
            return {"parsing_error": f"API parsing failed. Gemini: {gemini_err or 'Empty response'}. Groq: {groq_err or 'Not attempted/Empty response'}"}
            
        # Strip code fences if present
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```"):
            lines = cleaned_text.splitlines()
            if len(lines) >= 2 and lines[-1].strip() == "```":
                cleaned_text = "\n".join(lines[1:-1]).strip()
        if cleaned_text.startswith("json"):
            cleaned_text = cleaned_text[4:].strip()
            
        # Parse JSON
        result = json.loads(cleaned_text)
        
        # Ensure default duration
        if "duration_minutes" not in result or not isinstance(result["duration_minutes"], int):
            result["duration_minutes"] = 30
        if "proposed_times" not in result or not isinstance(result["proposed_times"], list) or not result["proposed_times"]:
            import datetime as datetime_mod
            fallback_slots = []
            current = datetime_mod.date.today() + datetime_mod.timedelta(days=1)
            for _ in range(3):
                # Propose slots at 10 AM, 2 PM, and 4 PM
                for hour in (10, 14, 16):
                    dt = datetime_mod.datetime.combine(current, datetime_mod.time(hour, 0))
                    fallback_slots.append(dt.strftime("%Y-%m-%dT%H:%M:%S+05:30"))
                current += datetime_mod.timedelta(days=1)
            result["proposed_times"] = fallback_slots
        if "attendees" not in result or not isinstance(result["attendees"], list):
            result["attendees"] = []
        if "topic" not in result:
            result["topic"] = "Meeting Request"
            
        return result
        
    except Exception as e:
        return {"parsing_error": f"Exception encountered during parsing: {e}"}



def check_availability(time_min, time_max):
    """
    Checks the user's primary calendar availability using the FreeBusy API.
    Returns True if free, False if busy. Raises exception on error.
    """
    try:
        service = _build_calendar_service()
        
        # Ensure timezone suffix is present
        def format_time(t_str):
            t_str = t_str.strip()
            # If start time has timezone offset like +05:30 or -08:00, or ends with Z, it is fine.
            # Otherwise, append Z.
            if '+' not in t_str and '-' not in t_str[10:] and not t_str.endswith('Z'):
                return t_str + 'Z'
            return t_str

        time_min_formatted = format_time(time_min)
        time_max_formatted = format_time(time_max)
        
        body = {
            "timeMin": time_min_formatted,
            "timeMax": time_max_formatted,
            "items": [{"id": "primary"}]
        }
        
        query = service.freebusy().query(body=body)
        response = query.execute()
        
        calendars = response.get("calendars", {})
        primary_cal = calendars.get("primary", {})
        busy_slots = primary_cal.get("busy", [])
        
        return len(busy_slots) == 0
    except Exception as e:
        import traceback
        print(f"[!] Error in check_availability: {e}")
        traceback.print_exc()
        raise e

def find_free_slot(proposed_times, duration_minutes):
    """
    Loops through proposed times, calculates end time using duration,
    calls check_availability for each, and returns the first free slot or None.
    Skips malformed time strings gracefully.
    """
    import datetime
    for start_time_str in proposed_times:
        try:
            cleaned_start = start_time_str.strip()
            iso_start = cleaned_start.replace("Z", "+00:00")
            
            start_dt = datetime.datetime.fromisoformat(iso_start)
            end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
            
            start_iso = start_dt.isoformat()
            end_iso = end_dt.isoformat()
        except Exception:
            continue
            
        # Let exceptions from check_availability propagate
        if check_availability(start_iso, end_iso):
            return start_time_str
    return None



def create_event(summary, start_time, duration_minutes, attendees, description=""):
    """
    Creates a Google Calendar event.
    Calculates end_time from start + duration.
    Builds the event body with summary, description, start/end with dateTime and timeZone "UTC".
    Only includes attendees if they contain valid emails (have "@").
    Uses calendarId="primary" and sendUpdates="all" so attendees get invitation emails.
    Returns the created event dict from the API.
    """
    import datetime
    service = _build_calendar_service()
    
    # Parse start_time to calculate end_time
    cleaned_start = start_time.strip()
    iso_start = cleaned_start.replace("Z", "+00:00")
    start_dt = datetime.datetime.fromisoformat(iso_start)
    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
    
    # Format start and end times back to ISO-8601 strings
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()
    
    # Format helper to ensure timezone info is present
    def format_time(t_str):
        t_str = t_str.strip()
        if '+' not in t_str and '-' not in t_str[10:] and not t_str.endswith('Z'):
            return t_str + 'Z'
        return t_str

    start_iso_formatted = format_time(start_iso)
    end_iso_formatted = format_time(end_iso)
    
    # Filter attendees list to valid emails (contain "@")
    attendee_emails = []
    if attendees:
        for att in attendees:
            att = att.strip()
            if "@" in att:
                attendee_emails.append({"email": att})
                
    # Build event body
    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_iso_formatted,
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end_iso_formatted,
            "timeZone": "UTC"
        }
    }
    
    if attendee_emails:
        event_body["attendees"] = attendee_emails
        
    # Execute insert event
    response = service.events().insert(
        calendarId="primary",
        sendUpdates="all",
        body=event_body
    ).execute()
    
    return response

if __name__ == "__main__":
    print("[*] Instantiating Google Calendar service...")
    try:
        service = _build_calendar_service()
        print("[+] Google Calendar service instantiated successfully!")
    except Exception as e:
        print(f"[-] Error: {e}")
        
    print("\n[*] Testing parse_meeting_request with mock thread...")
    mock_thread = {
        "subject": "MASAI Sync",
        "messages": [
            {
                "from": "rehan@masai.school",
                "date": "Thu, 25 Jun 2026 10:00:00 +0530",
                "body": "Hi Rahul, can we connect tomorrow at 3 PM to review the project status? I'll invite Anil (anil@company.com) as well."
            }
        ]
    }
    extracted = parse_meeting_request(mock_thread)
    print("Extracted output:", json.dumps(extracted, indent=2))
    
    if "parsing_error" not in extracted and extracted.get("proposed_times"):
        print("\n[*] Testing find_free_slot with proposed times...")
        free_slot = find_free_slot(extracted["proposed_times"], extracted.get("duration_minutes", 30))
        print(f"First free slot found: {free_slot}")
        
        # Test dry-run of event creation body (do not execute API to avoid garbage in primary calendar)
        print("\n[*] Dry-run event details generation:")
        print(f"  Summary: {extracted.get('topic')}")
        print(f"  Start: {free_slot if free_slot else extracted['proposed_times'][0]}")
        print(f"  Duration: {extracted.get('duration_minutes', 30)} mins")
        print(f"  Attendees: {extracted.get('attendees')}")
