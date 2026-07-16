import os
import json
import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "action_log.json")

def log_action(action_type: str, thread_subject: str, detail: str, action_id: str):
    """
    Appends an action record to action_log.json.
    
    Parameters:
    - action_type: str ("sent" or "booked")
    - thread_subject: str
    - detail: str (recipient email for "sent", meeting title for "booked")
    - action_id: str (Gmail message_id or Google Calendar event_id)
    """
    if action_type not in ("sent", "booked"):
        raise ValueError("action_type must be either 'sent' or 'booked'")

    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action_type": action_type,
        "thread_subject": thread_subject,
        "detail": detail,
        "id": action_id
    }

    log_data = get_action_log()
    log_data.append(record)

    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[!] Error writing to action log file: {e}")

def get_action_log() -> list:
    """
    Reads action_log.json and returns the full list of logged actions.
    Returns [] if the file does not exist, is empty, or is malformed.
    """
    if not os.path.exists(LOG_FILE):
        return []

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[!] Warning: Action log file could not be parsed: {e}")
        return []

def clear_log():
    """
    Clears the action log by writing an empty list to action_log.json.
    """
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
    except Exception as e:
        print(f"[!] Error clearing action log file: {e}")

if __name__ == "__main__":
    import traceback
    import sys
    print("Parsing app.py with AST...")
    try:
        with open("app.py", "r", encoding="utf-8") as f:
            source = f.read()
        compile(source, "app.py", "exec")
        print("\nCOMPILATION SUCCESSFUL! No syntax errors found in app.py.")
    except SyntaxError as e:
        print("\nCOMPILE ERROR DETECTED:")
        traceback.print_exception(type(e), e, e.__traceback__)
        sys.exit(1)
