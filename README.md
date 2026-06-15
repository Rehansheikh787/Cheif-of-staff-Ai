# Chief of Staff — Gmail Inbox Triage Agent

An AI-powered email triage agent that fetches your Gmail inbox threads and classifies them by priority using Google's Gemini 2.5 Flash model.

## What It Does

1. **Fetches** your last 10 Gmail inbox threads via a local MCP (Model Context Protocol) server
2. **Triages** each thread using Gemini AI into priority categories: `urgent`, `needs-reply`, `fyi`, `ignore`
3. **Displays** a color-coded CLI dashboard sorted by priority

## Architecture

```
engine.py (Python)
  ├── Spawns gmail-mcp-server (Node.js) as subprocess
  │     └── Communicates via JSON-RPC over stdio
  │     └── Authenticates via OAuth2 to Gmail API
  ├── Passes fetched threads to triage.py
  │     └── Classifies each thread via Gemini 2.5 Flash
  │     └── Falls back to local regex classifier if API is down
  └── Prints color-coded triage dashboard
```

## Setup

### Prerequisites
- Python 3.12+
- Node.js 14+
- A Google Cloud project with Gmail API enabled
- A Gemini API key

### Installation

```bash
# 1. Clone the repo and navigate to the project
cd "Jun First week Chief of Staff"

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell
# or: source .venv/bin/activate  # macOS/Linux

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install Node.js dependencies for the MCP server
cd gmail-mcp-server
npm install
npm run build
cd ..

# 5. Set up your Gemini API key
# Create gmail-mcp-server/.env with:
# GEMINI_API_KEY=your_key_here

# 6. Authenticate with Gmail (opens browser)
cd gmail-mcp-server
npm run auth
cd ..
```

## Usage

### Live Mode (fetches real Gmail threads)
```bash
python engine.py
```

### Demo Mode (uses mock data — no Gmail connection needed)
```bash
python engine.py --mock
```

### Strict Live Mode (fails if Gmail is unreachable)
```bash
python engine.py --live
```

## Rate Limits

The Gemini free tier allows 5 requests per minute. The triage engine automatically pauses after every 4 classifications to stay within quota. For 10 threads, expect ~2 minutes total runtime.

## Project Structure

```
├── engine.py                  # Main entry point — MCP client + CLI dashboard
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore rules
├── chief_of_staff.ipynb       # Jupyter notebook (alternative runner)
└── gmail-mcp-server/          # Gmail MCP server (Node.js)
    ├── triage.py              # Gemini triage logic + fallback classifier
    ├── .env                   # Gemini API key (gitignored)
    ├── config/
    │   ├── gcp-oauth.keys.json   # OAuth client config (gitignored)
    │   └── credentials.json      # OAuth tokens (gitignored)
    ├── src/                   # TypeScript source
    └── dist/                  # Compiled JavaScript
```
