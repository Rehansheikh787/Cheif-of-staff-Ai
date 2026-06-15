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


MCP_SERVER_CMD = _find_node()
MCP_SERVER_ARGS = [
    os.path.join(PROJECT_ROOT, "gmail-mcp-server", "dist", "index.js")
]


# ---------------------------------------------------------------------------
# Low-level MCP communication helpers
# ---------------------------------------------------------------------------

class MCPClient:
    """Minimal MCP client that speaks JSON-RPC 2.0 over stdio."""

    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._request_id = 0

    # -- lifecycle -----------------------------------------------------------

    def start(self):
        """Spawn the MCP server subprocess."""
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
            [MCP_SERVER_CMD, *MCP_SERVER_ARGS],
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
        """Read a single JSON-RPC response from the stdout stream (terminated by \n)."""
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


def _parse_read_email(text: str) -> dict:
    """
    Parse the read_email text output into a dict with thread_id, sender,
    subject, snippet, and date.
    """
    data: dict = {}

    for line in text.splitlines():
        if line.startswith("Thread ID: "):
            data["thread_id"] = line[len("Thread ID: "):]
        elif line.startswith("Subject: "):
            data["subject"] = line[len("Subject: "):]
        elif line.startswith("From: "):
            data["sender"] = line[len("From: "):]
        elif line.startswith("Date: "):
            data["date"] = line[len("Date: "):]

    # Extract the body text as snippet (first non-header paragraph)
    parts = text.split("\n\n", 2)
    snippet_text = ""

    if len(parts) > 1:
        snippet_text = parts[1].strip()
        # If snippet starts with a note marker, take the next section
        if snippet_text.startswith("[Note:") and len(parts) > 2:
            snippet_text = parts[2].strip()
    
    # If snippet is still empty, try to grab text after the last header line
    if not snippet_text:
        lines = text.splitlines()
        body_started = False
        body_lines = []
        for line in lines:
            if body_started:
                body_lines.append(line)
            elif not line.strip():
                body_started = True
        snippet_text = " ".join(l.strip() for l in body_lines if l.strip())

    # Truncate snippet to ~200 chars
    if len(snippet_text) > 200:
        snippet_text = snippet_text[:200].rstrip() + "..."

    data["snippet"] = snippet_text
    return data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_threads(max_threads: int = 10) -> list[dict]:
    """
    Fetch the last `max_threads` inbox threads from Gmail via the MCP server.

    Returns a list of dicts, each containing:
        - thread_id  : str — Gmail thread ID
        - sender     : str — sender name/email
        - subject    : str — email subject line
        - snippet    : str — short preview of the email body
        - date       : str — date string
    """
    client = MCPClient()

    try:
        # 1. Start the MCP server and complete the handshake
        print("[*] Starting Gmail MCP server...")
        client.start()
        client.initialize()
        print("[+] MCP server initialized")

        # 2. Search for recent inbox emails
        print(f"[*] Fetching last {max_threads} inbox threads...")
        search_result = client.call_tool("search_emails", {
            "query": "in:inbox",
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
            print("[-] No messages found in inbox.")
            return []

        print(f"[+] Found {len(messages)} messages. Fetching details...")

        # 3. Read each message to get full details (thread_id + snippet)
        threads: list[dict] = []
        seen_thread_ids: set = set()

        for i, msg in enumerate(messages):
            msg_id = msg.get("id")
            if not msg_id:
                continue

            read_result = client.call_tool("read_email", {
                "messageId": msg_id,
            })

            # Check for error in the tool result
            if read_result.get("isError"):
                error_text = read_result.get("content", [{}])[0].get("text", "Unknown MCP tool error")
                raise RuntimeError(f"Gmail MCP Read failed: {error_text}")

            read_text = ""
            for content_item in read_result.get("content", []):
                if content_item.get("type") == "text":
                    read_text += content_item.get("text", "")

            email_data = _parse_read_email(read_text)

            # Deduplicate by thread_id (keep only the most recent per thread)
            tid = email_data.get("thread_id", msg_id)
            if tid in seen_thread_ids:
                continue
            seen_thread_ids.add(tid)

            thread = {
                "thread_id": tid,
                "sender": email_data.get("sender", msg.get("from", "")),
                "subject": email_data.get("subject", msg.get("subject", "")),
                "snippet": email_data.get("snippet", ""),
                "date": email_data.get("date", msg.get("date", "")),
            }
            threads.append(thread)

            # Progress indicator
            print(f"  [{i + 1}/{len(messages)}] {thread['subject'][:60]}")

        print(f"\n[+] Fetched {len(threads)} unique threads.")
        return threads

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
