"""
engine.py — Fetch the last 10 Gmail inbox threads via the Gmail MCP server.

Launches the gmail-mcp-server as a subprocess and communicates with it
using the Model Context Protocol (JSON-RPC over stdio).
"""

import json
import subprocess
import shutil
import sys
import os
import base64
from email.mime.text import MIMEText
from typing import Optional

# ---------------------------------------------------------------------------
# Project root — all paths are computed relative to this file
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Set up local import path for gmail-mcp-server
sys.path.append(os.path.join(PROJECT_ROOT, "gmail-mcp-server"))
from triage import triage_inbox


# ---------------------------------------------------------------------------
# MCP server configuration — auto-detected, no hardcoded paths
# ---------------------------------------------------------------------------
def _find_node() -> str:
    """Find the Node.js binary. Checks NODE_PATH env var, then PATH."""
    node = os.environ.get("NODE_PATH")
    if node and os.path.isfile(node):
        return node
    node = shutil.which("node")
    if node:
        return node
    # Fallback: check common Windows install locations
    common_paths = [
        os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright-go\1.57.0\node.exe"),
        os.path.expandvars(r"%PROGRAMFILES%\nodejs\node.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\node\node.exe"),
    ]
    for path in common_paths:
        if os.path.isfile(path):
            return path
    raise FileNotFoundError(
        "Node.js not found. Install Node.js or set the NODE_PATH environment variable."
    )


def _ensure_node_modules():
    """Ensure that npm dependencies are installed for the Gmail MCP server."""
    node_modules_path = os.path.join(PROJECT_ROOT, "gmail-mcp-server", "node_modules")
    if not os.path.exists(node_modules_path):
        import subprocess
        npm_cmd = shutil.which("npm")
        if not npm_cmd:
            common_npm = os.path.expandvars(r"%PROGRAMFILES%\nodejs\npm.cmd")
            if os.path.isfile(common_npm):
                npm_cmd = common_npm
        if npm_cmd:
            print("[*] Running npm install for Gmail MCP server...")
            try:
                server_dir = os.path.join(PROJECT_ROOT, "gmail-mcp-server")
                subprocess.run([npm_cmd, "install"], cwd=server_dir, check=True)
                print("[+] npm install completed successfully.")
            except Exception as e:
                print(f"[!] Warning: failed to run npm install: {e}")
        else:
            print("[!] Warning: npm binary not found. Cannot install MCP server dependencies.")


# Resolved lazily in start() to prevent import-time crashes when Node is missing
MCP_SERVER_CMD = None
MCP_SERVER_ARGS = [
    os.path.join(PROJECT_ROOT, "gmail-mcp-server", "dist", "index.js")
]


# ---------------------------------------------------------------------------
# Low-level MCP communication helpers
# ---------------------------------------------------------------------------

def sync_oauth_tokens(project_root: str):
    """
    Synchronizes OAuth tokens between the root token.json (Python format)
    and gmail-mcp-server/config/credentials.json (Node.js format).
    Ensures that both files are using the most recently refreshed credentials.
    """
    import os
    import json
    from datetime import datetime

    root_token_path = os.path.join(project_root, "token.json")
    node_creds_path = os.path.join(project_root, "gmail-mcp-server", "config", "credentials.json")

    # Helper to parse python expiry string into epoch milliseconds
    def python_expiry_to_ms(expiry_str):
        if not expiry_str:
            return 0
        try:
            if expiry_str.endswith("Z"):
                expiry_str = expiry_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(expiry_str)
            return int(dt.timestamp() * 1000)
        except Exception:
            return 0

    # Helper to convert epoch milliseconds to ISO string in UTC
    def ms_to_python_expiry(ms):
        if not ms:
            return ""
        try:
            from datetime import timezone
            dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
            return dt.isoformat().replace("+00:00", "Z")
        except Exception:
            return ""

    # Load root token.json if exists
    py_data = None
    if os.path.exists(root_token_path):
        try:
            with open(root_token_path, "r", encoding="utf-8") as f:
                py_data = json.load(f)
        except Exception as e:
            print(f"[!] Error reading root token.json for sync: {e}")

    # Load Node credentials.json if exists
    node_data = None
    if os.path.exists(node_creds_path):
        try:
            with open(node_creds_path, "r", encoding="utf-8") as f:
                node_data = json.load(f)
        except Exception as e:
            print(f"[!] Error reading node credentials.json for sync: {e}")

    if not py_data and not node_data:
        return

    # Determine which one has the newer / valid token
    py_expiry_ms = python_expiry_to_ms(py_data.get("expiry")) if py_data else 0
    node_expiry_ms = node_data.get("expiry_date", 0) if node_data else 0

    # If py_data is newer, sync to node
    if py_data and (not node_data or py_expiry_ms > node_expiry_ms):
        print(f"[*] Syncing credentials from token.json to node credentials.json (python expiry: {py_data.get('expiry')}, node expiry: {ms_to_python_expiry(node_expiry_ms)})")
        
        # Build node format
        scopes_str = " ".join(py_data.get("scopes", [])) if isinstance(py_data.get("scopes"), list) else py_data.get("scopes", "")
        new_node_data = {
            "access_token": py_data.get("token"),
            "refresh_token": py_data.get("refresh_token"),
            "scope": scopes_str,
            "token_type": "Bearer",
            "refresh_token_expires_in": 604799,
            "expiry_date": py_expiry_ms
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(node_creds_path), exist_ok=True)
        try:
            with open(node_creds_path, "w", encoding="utf-8") as f:
                json.dump(new_node_data, f, indent=2)
            print("[+] Node credentials.json updated successfully.")
        except Exception as e:
            print(f"[!] Failed to write node credentials.json: {e}")

    # If node_data is newer, sync to root
    elif node_data and (not py_data or node_expiry_ms > py_expiry_ms):
        print(f"[*] Syncing credentials from node credentials.json to token.json (node expiry: {ms_to_python_expiry(node_expiry_ms)}, python expiry: {py_data.get('expiry') if py_data else 'None'})")
        
        # Build python format
        scopes_list = node_data.get("scope", "").split(" ") if isinstance(node_data.get("scope"), str) else []
        new_py_data = {
            "token": node_data.get("access_token"),
            "refresh_token": node_data.get("refresh_token"),
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": py_data.get("client_id") if py_data else node_data.get("client_id", ""),
            "client_secret": py_data.get("client_secret") if py_data else node_data.get("client_secret", ""),
            "scopes": scopes_list,
            "universe_domain": "googleapis.com",
            "account": "",
            "expiry": ms_to_python_expiry(node_expiry_ms)
        }
        
        # Ensure client_id and client_secret are present
        if not new_py_data["client_id"] or not new_py_data["client_secret"]:
            root_creds_path = os.path.join(project_root, "credentials.json")
            if os.path.exists(root_creds_path):
                try:
                    with open(root_creds_path, "r", encoding="utf-8") as f:
                        creds_content = json.load(f)
                        key = "installed" if "installed" in creds_content else "web"
                        if key in creds_content:
                            new_py_data["client_id"] = creds_content[key].get("client_id")
                            new_py_data["client_secret"] = creds_content[key].get("client_secret")
                except Exception:
                    pass

        try:
            with open(root_token_path, "w", encoding="utf-8") as f:
                json.dump(new_py_data, f, indent=2)
            print("[+] Root token.json updated successfully.")
        except Exception as e:
            print(f"[!] Failed to write root token.json: {e}")


class MCPClient:
    """Minimal MCP client that speaks JSON-RPC 2.0 over stdio."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        """Spawn the MCP server subprocess."""
        # Synchronize credentials between token.json and Node credentials.json
        try:
            sync_oauth_tokens(PROJECT_ROOT)
        except Exception as sync_e:
            print(f"[!] Error synchronizing OAuth tokens: {sync_e}")

        # Ensure Node dependencies are installed
        try:
            _ensure_node_modules()
        except Exception as npm_e:
            print(f"[!] Error running npm installation: {npm_e}")

        node_cmd = _find_node()
        env = os.environ.copy()
        env["NODE_PRESERVE_SYMLINKS"] = "1"
        env["NODE_PRESERVE_SYMLINKS_MAIN"] = "1"

        # Point to workspace-local OAuth files to avoid sandbox permission errors
        env["GMAIL_OAUTH_PATH"] = os.path.join(
            PROJECT_ROOT, "gmail-mcp-server", "config", "gcp-oauth.keys.json"
        )
        env["GMAIL_CREDENTIALS_PATH"] = os.path.join(
            PROJECT_ROOT, "gmail-mcp-server", "config", "credentials.json"
        )

        self._process = subprocess.Popen(
            [node_cmd, *MCP_SERVER_ARGS],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # binary mode — we handle encoding ourselves
            shell=False,
            env=env,
        )

    def stop(self):
        """Terminate the MCP server subprocess."""
        if self._process:
            self._process.stdin.close()
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    # -- JSON-RPC helpers ----------------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send(self, method: str, params: dict | None = None) -> dict:
        """Send a JSON-RPC request and return the parsed response."""
        if not self._process or self._process.poll() is not None:
            raise RuntimeError("MCP server is not running")

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            request["params"] = params

        body = json.dumps(request) + "\n"
        self._process.stdin.write(body.encode("utf-8"))
        self._process.stdin.flush()

        return self._read_response()

    def _read_response(self) -> dict:
        """Read a single JSON-RPC response from the stdout stream (terminated by \\n)."""
        stdout = self._process.stdout

        line = stdout.readline()
        if not line:
            stderr_content = ""
            if self._process.poll() is not None:
                try:
                    stderr_content = self._process.stderr.read().decode('utf-8', errors='replace')
                except Exception as e:
                    stderr_content = f"<Could not read stderr: {e}>"
            raise RuntimeError(
                f"MCP server closed stdout unexpectedly. Process status: {self._process.poll()}.\n"
                f"Stderr:\n{stderr_content}"
            )

        return json.loads(line.decode("utf-8"))

    # -- MCP protocol methods ------------------------------------------------

    def initialize(self):
        """Send the MCP initialize handshake."""
        resp = self._send("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "engine.py",
                "version": "1.0.0"
            }
        })
        if "error" in resp:
            raise RuntimeError(f"MCP initialize error: {resp['error']}")

        # Send initialized notification (no response expected, but we
        # send it as a notification — no id)
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        body = json.dumps(notif) + "\n"
        self._process.stdin.write(body.encode("utf-8"))
        self._process.stdin.flush()

        return resp

    def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call an MCP tool and return the result."""
        resp = self._send("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })
        if "error" in resp:
            raise RuntimeError(
                f"MCP tool '{tool_name}' error: {resp['error']}"
            )
        return resp.get("result", {})


# ---------------------------------------------------------------------------
# Gmail parsing helpers
# ---------------------------------------------------------------------------

def _parse_search_results(text: str) -> list[dict]:
    """
    Parse the search_emails text output into a list of dicts.

    The MCP server returns results in this format:
        ID: <id>
        Subject: <subject>
        From: <from>
        Date: <date>
    """
    entries = []
    current: dict = {}

    for line in text.splitlines():
        line = line.strip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue

        if line.startswith("ID: "):
            current["id"] = line[4:]
        elif line.startswith("Subject: "):
            current["subject"] = line[9:]
        elif line.startswith("From: "):
            current["from"] = line[6:]
        elif line.startswith("Date: "):
            current["date"] = line[6:]

    if current:
        entries.append(current)

    return entries


def sanitize_body_text(text: str) -> str:
    """
    Cleans up the email body by stripping out inline base64 images, 
    excessive HTML tags, and massive non-spaced strings that represent binary content.
    """
    if not text:
        return ""
    
    import re
    # 1. Replace base64 image data URIs
    text = re.sub(r'data:image/[a-zA-Z+.-]+;base64,[A-Za-z0-9+/=]+', '[Inline Image Data]', text)
    
    # 2. Split into words and replace any ridiculously long words (binary data leaks or inline CSS)
    words = text.split()
    cleaned_words = []
    for word in words:
        if len(word) > 250:
            if re.match(r'^[A-Za-z0-9+/=]+$', word) or "background-image" in word or "style" in word:
                cleaned_words.append('[Binary/Large Content Truncated]')
            else:
                cleaned_words.append(word[:100] + '...[Truncated]')
        else:
            cleaned_words.append(word)
    text = " ".join(cleaned_words)
    
    # 3. Strip HTML tag clutter
    text = re.sub(r'<img[^>]+>', '[Inline Image]', text)
    
    # Compress multiple newlines/spaces
    text = re.sub(r'\n\s*\n', '\n\n', text)
    return text


def _parse_read_email(text: str) -> dict:
    """
    Parse the read_email text output into a dict with thread_id, sender,
    subject, snippet, body, and date.
    """
    text = text.replace("\r\n", "\n")
    data: dict = {}

    for line in text.splitlines():
        if line.startswith("Thread ID: "):
            data["thread_id"] = line[len("Thread ID: "):].strip()
        elif line.startswith("Subject: "):
            data["subject"] = line[len("Subject: "):].strip()
        elif line.startswith("From: "):
            data["sender"] = line[len("From: "):].strip()
        elif line.startswith("Date: "):
            data["date"] = line[len("Date: "):].strip()

    # Extract the full body text (everything after headers, split by the first double newline)
    parts = text.split("\n\n", 1)
    if len(parts) > 1:
        raw_body = parts[1].strip()
        data["body"] = sanitize_body_text(raw_body)
    else:
        data["body"] = ""

    # Keep snippet as the truncated version of the body (without note marker if possible)
    snippet_text = data["body"]
    if snippet_text.startswith("[Note:"):
        note_parts = snippet_text.split("\n\n", 1)
        if len(note_parts) > 1:
            snippet_text = note_parts[1].strip()
            
    if len(snippet_text) > 200:
        data["snippet"] = snippet_text[:200].rstrip() + "..."
    else:
        data["snippet"] = snippet_text

    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def send_reply(thread_id: str, to: str, subject: str, body: str, message_id: str = None) -> dict:
    """
    Sends a reply using the Gmail MCP server.
    """
    # Prepend "Re: " to subject if not already there
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    client = MCPClient()
    try:
        client.start()
        client.initialize()
        
        args = {
            "to": [to],
            "subject": subject,
            "body": body,
        }
        if thread_id:
            args["threadId"] = thread_id
        if message_id:
            args["inReplyTo"] = message_id

        print(f"[*] Sending reply via Gmail MCP to {to}...")
        res = client.call_tool("send_email", args)
        
        if res.get("isError"):
            error_text = res.get("content", [{}])[0].get("text", "Unknown MCP tool error")
            raise RuntimeError(f"Gmail MCP Send failed: {error_text}")
            
        # Parse result to find message ID
        msg_id = None
        for item in res.get("content", []):
            if item.get("type") == "text":
                text = item.get("text", "")
                if "ID: " in text:
                    msg_id = text.split("ID: ")[1].strip()
                    
        return {
            "message_id": msg_id,
            "thread_id": thread_id,
            "status": "sent"
        }
    finally:
        client.stop()


def fetch_threads(max_threads: int = 10) -> list[dict]:
    """
    Fetch the last `max_threads` inbox threads from Gmail via the MCP server.
    Only fetches unread threads where the user has not replied.
    For each thread, retrieves the full message history to prevent partial contents.

    Returns a list of dicts, each containing:
        - thread_id  : str — Gmail thread ID
        - sender     : str — sender name/email
        - subject    : str — email subject line
        - snippet    : str — short preview of the email body
        - body       : str — full preview of the email body
        - date       : str — date string
        - messages   : list — message history: [{"message_id", "from", "date", "body"}]
    """
    client = MCPClient()

    try:
        # 1. Start the MCP server and complete the handshake
        print("[*] Starting Gmail MCP server...")
        client.start()
        client.initialize()
        print("[+] MCP server initialized")

        # 2. Search for recent inbox emails where we haven't replied
        # query "in:inbox -from:me" matches all inbox threads that do not contain a reply from you
        print(f"[*] Fetching last {max_threads} unreplied inbox threads...")
        search_result = client.call_tool("search_emails", {
            "query": "in:inbox -from:me",
            "maxResults": max_threads,
        })

        # Check for error in the tool result
        if search_result.get("isError"):
            error_text = search_result.get("content", [{}])[0].get("text", "Unknown MCP tool error")
            raise RuntimeError(f"Gmail MCP Search failed: {error_text}")

        # Extract the text content from the MCP response
        search_text = ""
        for content_item in search_result.get("content", []):
            if content_item.get("type") == "text":
                search_text += content_item.get("text", "")

        # Parse the search results to get message IDs
        messages = _parse_search_results(search_text)

        if not messages:
            print("[-] No matching messages found in inbox.")
            return []

        print(f"[+] Found {len(messages)} messages. Fetching thread histories...")

        threads: list[dict] = []
        seen_thread_ids: set = set()

        for i, msg in enumerate(messages):
            msg_id = msg.get("id")
            if not msg_id:
                continue

            # First, read this message to get its thread ID
            read_result = client.call_tool("read_email", {
                "messageId": msg_id,
            })

            # Check for error in the tool result
            if read_result.get("isError"):
                continue

            read_text = ""
            for content_item in read_result.get("content", []):
                if content_item.get("type") == "text":
                    read_text += content_item.get("text", "")

            email_data = _parse_read_email(read_text)
            tid = email_data.get("thread_id", msg_id)

            # Deduplicate by thread_id
            if tid in seen_thread_ids:
                continue
            seen_thread_ids.add(tid)

            # Fetch all messages in this thread using a thread query
            print(f"  [{len(seen_thread_ids)}] Fetching full history for thread {tid}...")
            thread_search = client.call_tool("search_emails", {
                "query": f"thread:{tid}",
                "maxResults": 20
            })

            thread_msg_list = []
            if not thread_search.get("isError"):
                thread_search_text = ""
                for item in thread_search.get("content", []):
                    if item.get("type") == "text":
                        thread_search_text += item.get("text", "")
                thread_msg_list = _parse_search_results(thread_search_text)

            # If the search failed or was empty, fall back to just this one message
            if not thread_msg_list:
                thread_msg_list = [msg]

            # Read details of all messages in this thread to get their full bodies
            thread_messages = []
            for t_msg in thread_msg_list:
                t_msg_id = t_msg.get("id")
                if not t_msg_id:
                    continue
                t_read_result = client.call_tool("read_email", {
                    "messageId": t_msg_id
                })
                if t_read_result.get("isError"):
                    continue
                t_read_text = ""
                for item in t_read_result.get("content", []):
                    if item.get("type") == "text":
                        t_read_text += item.get("text", "")
                t_email_data = _parse_read_email(t_read_text)
                thread_messages.append({
                    "message_id": t_msg_id,
                    "from": t_email_data.get("sender", t_msg.get("from", "")),
                    "date": t_email_data.get("date", t_msg.get("date", "")),
                    "body": t_email_data.get("body", "")
                })

            # Check if we got any messages; if not, use current msg
            if not thread_messages:
                thread_messages = [{
                    "message_id": msg_id,
                    "from": email_data.get("sender", msg.get("from", "")),
                    "date": email_data.get("date", msg.get("date", "")),
                    "body": email_data.get("body", "")
                }]

            # The latest message's sender/subject/date will represent the thread
            latest_msg_data = thread_messages[-1]

            thread = {
                "thread_id": tid,
                "sender": latest_msg_data.get("from", email_data.get("sender", "")),
                "subject": email_data.get("subject", msg.get("subject", "")),
                "snippet": email_data.get("snippet", ""),
                "body": latest_msg_data.get("body", email_data.get("body", "")),
                "date": latest_msg_data.get("date", email_data.get("date", "")),
                "messages": thread_messages
            }
            threads.append(thread)

        print(f"\n[+] Fetched {len(threads)} unique threads.")
        return threads

    finally:
        client.stop()


def fetch_calendar_events(time_min: str = None, max_results: int = 10) -> list[dict]:
    """
    Fetch upcoming calendar events from Google Calendar primary calendar.
    """
    client = MCPClient()
    try:
        client.start()
        client.initialize()
        
        args = {"maxResults": max_results}
        if time_min:
            args["timeMin"] = time_min
        else:
            # Default to start of today in UTC
            import datetime
            args["timeMin"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
        res = client.call_tool("list_calendar_events", args)
        if res.get("isError"):
            error_text = res.get("content", [{}])[0].get("text", "Unknown MCP tool error")
            raise RuntimeError(f"Calendar MCP list failed: {error_text}")
            
        import json
        payload_text = ""
        for item in res.get("content", []):
            if item.get("type") == "text":
                payload_text += item.get("text", "")
                
        if not payload_text:
            return []
            
        if payload_text.startswith("Failed to") or payload_text.startswith("Error"):
            raise RuntimeError(payload_text)
            
        payload = json.loads(payload_text)
        return payload.get("events", [])
    finally:
        client.stop()


def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = None, location: str = None, attendees: list = None) -> dict:
    """
    Create a new calendar event on the primary calendar.
    """
    client = MCPClient()
    try:
        client.start()
        client.initialize()
        
        args = {
            "summary": summary,
            "startTime": start_time,
            "endTime": end_time
        }
        if description:
            args["description"] = description
        if location:
            args["location"] = location
        if attendees:
            args["attendees"] = attendees
            
        res = client.call_tool("create_calendar_event", args)
        if res.get("isError"):
            error_text = res.get("content", [{}])[0].get("text", "Unknown MCP tool error")
            raise RuntimeError(f"Calendar MCP create failed: {error_text}")
            
        import json
        payload_text = ""
        for item in res.get("content", []):
            if item.get("type") == "text":
                payload_text += item.get("text", "")
                
        if payload_text.startswith("Failed to") or payload_text.startswith("Error"):
            raise RuntimeError(payload_text)
            
        return json.loads(payload_text)
    finally:
        client.stop()


def quick_add_calendar_event(text: str) -> dict:
    """
    Quick add an event using free text.
    """
    client = MCPClient()
    try:
        client.start()
        client.initialize()
        
        res = client.call_tool("quick_add_calendar_event", {"text": text})
        if res.get("isError"):
            error_text = res.get("content", [{}])[0].get("text", "Unknown MCP tool error")
            raise RuntimeError(f"Calendar MCP quick add failed: {error_text}")
            
        import json
        payload_text = ""
        for item in res.get("content", []):
            if item.get("type") == "text":
                payload_text += item.get("text", "")
                
        if payload_text.startswith("Failed to") or payload_text.startswith("Error"):
            raise RuntimeError(payload_text)
            
        return json.loads(payload_text)
    finally:
        client.stop()


def delete_calendar_event(event_id: str) -> dict:
    """
    Delete a calendar event by ID.
    """
    client = MCPClient()
    try:
        client.start()
        client.initialize()
        
        res = client.call_tool("delete_calendar_event", {"eventId": event_id})
        if res.get("isError"):
            error_text = res.get("content", [{}])[0].get("text", "Unknown MCP tool error")
            raise RuntimeError(f"Calendar MCP delete failed: {error_text}")
            
        import json
        payload_text = ""
        for item in res.get("content", []):
            if item.get("type") == "text":
                payload_text += item.get("text", "")
                
        if payload_text.startswith("Failed to") or payload_text.startswith("Error"):
            raise RuntimeError(payload_text)
            
        return json.loads(payload_text)
    finally:
        client.stop()


# ---------------------------------------------------------------------------
# Mock data for offline / demo mode
# ---------------------------------------------------------------------------

MOCK_THREADS = [
    {
        "thread_id": "mock_thread_1",
        "sender": "boss@company.com",
        "subject": "[URGENT] Review Q3 Proposal by EOD",
        "snippet": "Hi team, please review the attached proposal before our 5pm meeting. I need your feedback on the budget slide.",
        "date": "Mon, 15 Jun 2026 09:12:00 -0400"
    },
    {
        "thread_id": "mock_thread_2",
        "sender": "recruiter@startup.io",
        "subject": "Quick call this week — Masai Live Project",
        "snippet": "Hi there! I came across your profile and was impressed by your Chief of Staff agent. Are you free for a 15-minute sync on Wednesday?",
        "date": "Mon, 15 Jun 2026 10:30:15 -0400"
    },
    {
        "thread_id": "mock_thread_3",
        "sender": "billing@aws.amazon.com",
        "subject": "AWS Invoice Available: $142.50",
        "snippet": "Your monthly AWS invoice is now available in the Billing Console. Your card ending in 4321 will be automatically charged.",
        "date": "Sun, 14 Jun 2026 23:45:00 -0400"
    },
    {
        "thread_id": "mock_thread_4",
        "sender": "newsletter@medium.com",
        "subject": "Top stories for you: The Future of Agentic Coding",
        "snippet": "Trending in Technology: How Gemini 2.5 and the Model Context Protocol are revolutionizing software development.",
        "date": "Sat, 13 Jun 2026 08:00:22 -0400"
    },
    {
        "thread_id": "mock_thread_5",
        "sender": "notifications@linkedin.com",
        "subject": "John Doe viewed your profile",
        "snippet": "See all views and search appearances on your premium dashboard. Grow your professional network today.",
        "date": "Mon, 15 Jun 2026 11:05:40 -0400"
    },
    {
        "thread_id": "mock_thread_6",
        "sender": "support@github.com",
        "subject": "[GitHub] Security Alert: New login detected",
        "snippet": "A new login was detected on your account from IP address 192.168.1.1. If this was not you, please secure your account immediately.",
        "date": "Sun, 14 Jun 2026 14:20:10 -0400"
    }
]


MOCK_EVENTS = [
    {
        "id": "mock_event_1",
        "summary": "MASAI Live Project Kickoff",
        "description": "Discuss objectives, sprint plans, and coordinate task assignments.",
        "location": "Google Meet (meet.google.com/abc-defg-hij)",
        "start": "2026-06-25T15:00:00+05:30",
        "end": "2026-06-25T16:00:00+05:30",
        "attendees": ["boss@company.com", "rehan@masai.school"]
    },
    {
        "id": "mock_event_2",
        "summary": "1-on-1 with Boss",
        "description": "Weekly status update and feedback session.",
        "location": "Rahul's Office",
        "start": "2026-06-26T10:00:00+05:30",
        "end": "2026-06-26T10:30:00+05:30",
        "attendees": ["boss@company.com"]
    },
    {
        "id": "mock_event_3",
        "summary": "Budget Review Sync",
        "description": "Prepare final figures for Q3 marketing and infrastructure allocation.",
        "location": "Zoom Meeting",
        "start": "2026-06-26T14:00:00+05:30",
        "end": "2026-06-26T15:00:00+05:30",
        "attendees": ["finance@company.com", "boss@company.com"]
    }
]


# ---------------------------------------------------------------------------
# Dashboard printer
# ---------------------------------------------------------------------------

def print_dashboard(results: list[dict], is_mock: bool = False):
    """Print a formatted triage dashboard to the terminal."""
    print("\n" + "=" * 80)
    print(f"\033[95m{'CHIEF OF STAFF EMAIL TRIAGE DASHBOARD':^80}\033[0m")
    if is_mock:
        print(f"\033[93m{'[ DEMO SIMULATOR MODE ]':^80}\033[0m")
    print("=" * 80)

    # Triage summary counts
    counts = {"urgent": 0, "needs-reply": 0, "fyi": 0, "ignore": 0, "unknown": 0}
    for r in results:
        p = r.get("priority", "unknown")
        counts[p] = counts.get(p, 0) + 1

    print(f"  Summary:  \033[91mUrgent: {counts['urgent']}\033[0m  |  \033[93mNeeds Reply: {counts['needs-reply']}\033[0m  |  \033[96mFYI: {counts['fyi']}\033[0m  |  \033[90mIgnore: {counts['ignore']}\033[0m")
    print("=" * 80)

    # Priority colors
    colors = {
        "urgent": "\033[91m",
        "needs-reply": "\033[93m",
        "fyi": "\033[96m",
        "ignore": "\033[90m",
        "unknown": "\033[37m"
    }
    reset = "\033[0m"

    for i, t in enumerate(results, 1):
        priority = t.get("priority", "unknown")
        category = t.get("category", "other")
        reason = t.get("reason", "")
        color = colors.get(priority, colors["unknown"])

        print(f"\n{'-' * 80}")
        print(f"  #{i}  {color}[{priority.upper()}]  Category: {category.upper()}{reset}")
        print(f"  Thread ID : {t.get('thread_id', 'N/A')}")
        print(f"  From      : {t.get('sender', 'N/A')}")
        print(f"  Subject   : {t.get('subject', 'N/A')}")
        print(f"  Date      : {t.get('date', 'N/A')}")
        print(f"  Reason    : \033[3m{reason}\033[0m")
        print(f"  Snippet   : {t.get('snippet', '')[:120]}...")

    print(f"\n{'-' * 80}")
    print(f"Total Triaged: {len(results)} threads")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Chief of Staff — Gmail Inbox Triage Agent"
    )
    parser.add_argument(
        "--mock", action="store_true",
        help="Force mock/demo mode (skip Gmail fetch)"
    )
    parser.add_argument(
        "--live", action="store_true",
        help="Force live mode (fail immediately if Gmail is unreachable)"
    )
    args = parser.parse_args()

    print("[*] Launching Chief of Staff Email Agent...")

    threads = []
    is_mock = False

    if args.mock:
        # User explicitly requested mock mode
        is_mock = True
        threads = MOCK_THREADS
        print("\033[96m[*] Running in MOCK mode (--mock flag).\033[0m")
    else:
        try:
            threads = fetch_threads()
        except Exception as e:
            print(f"\n\033[91m[!] Error connecting to Gmail MCP: {e}\033[0m")
            if args.live:
                print("\033[91m[!] --live flag set. Exiting without fallback.\033[0m")
                sys.exit(1)

        if not threads:
            print("\033[93m[!] No threads fetched from Gmail (sandbox or offline mode detected).\033[0m")
            print("\033[96m[*] Loading realistic mock inbox threads for Chief of Staff simulation...\033[0m")
            is_mock = True
            threads = MOCK_THREADS

    # Pass the list into triage_inbox() to classify each thread and store in results
    print("\n[*] Triaging inbox threads using Chief of Staff AI Engine...")
    results = triage_inbox(threads)

    # Print dashboard
    print_dashboard(results, is_mock=is_mock)
