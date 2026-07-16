# -*- coding: utf-8 -*-
"""
# Chief of Staff Dashboard Redesigned
app.py — 'The Draft Desk' email triage and ghostwriting approval dashboard.
"""

import os
import sys
import json
import datetime
import base64
import re
# pyrefly: ignore [missing-import]
import streamlit as st
from task_logger import log_action, get_action_log

# Setup system path to import from workspace root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def clean_html(html_str: str) -> str:
    return "\n".join(line.strip() for line in html_str.split("\n"))

def get_app_logo_svg(size=28):
    logo = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 100 100" fill="none" style="vertical-align: middle; display: inline-block; filter: drop-shadow(0 2px 8px rgba(139, 92, 246, 0.3));">
        <defs>
            <linearGradient id="logo-grad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#8B5CF6" />
                <stop offset="100%" stop-color="#06B6D4" />
            </linearGradient>
        </defs>
        <polygon points="50,8 88,28 88,72 50,92 12,72 12,28" stroke="url(#logo-grad)" stroke-width="6" fill="rgba(139, 92, 246, 0.05)" stroke-linejoin="round"/>
        <polyline points="35,50 45,60 65,40" stroke="url(#logo-grad)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="50" cy="8" r="4" fill="#06B6D4"/>
        <circle cx="88" cy="28" r="4" fill="#8B5CF6"/>
        <circle cx="88" cy="72" r="4" fill="#06B6D4"/>
        <circle cx="50" cy="92" r="4" fill="#8B5CF6"/>
        <circle cx="12" cy="72" r="4" fill="#06B6D4"/>
        <circle cx="12" cy="28" r="4" fill="#8B5CF6"/>
    </svg>
    """
    return clean_html(logo)

# Available background images (photos, abstract renders, vector art, dark mode boardrooms)
WALLPAPERS = {
    "✨ 3D Glassmorphic Render": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/cos_3d_glassmorphic_bg_1783535368566.png",
    "🎨 Flat Vector Workspace": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/cos_vector_flat_bg_1783535382959.png",
    "📊 Technical Blueprint Grid": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/cos_tech_blueprint_bg_1783535396208.png",
    "📦 Triage Executive Desk": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/cos_triage_dashboard_bg_1783535100046.png",
    "📱 Minimalist Inbox Desk": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/cos_minimalist_inbox_bg_1783535115444.png",
    "📅 Productivity Planner Setup": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/cos_productivity_planner_bg_1783535129675.png",
    "☕ Scandinavian Office Desk": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/scandi_desk_bg_1783533973211.png",
    "🏠 Modern Loft Workspace": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/modern_loft_bg_1783533996200.png",
    "🏢 Glass Office Lobby": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/glass_lobby_bg_1783534037777.png",
    "🗄️ Moody Executive Desk": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/moody_desk_bg_1783440583887.png",
    "🌉 Corner Office Cityscape": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/office_cityscape_bg_1783440609560.png",
    "🪟 Glass Boardroom Table": "C:/Users/HP/.gemini/antigravity-ide/brain/86d2ed0f-b35e-4196-b08d-c7e031dca34e/boardroom_interior_bg_1783440626701.png"
}

BG_SETTINGS_FILE = os.path.join(PROJECT_ROOT, "bg_settings.json")
selected_bg_key = "🗄️ Moody Executive Desk" # Default

if os.path.exists(BG_SETTINGS_FILE):
    try:
        with open(BG_SETTINGS_FILE, "r") as sf:
            settings_data = json.load(sf)
            selected_bg_key = settings_data.get("selected_wallpaper", selected_bg_key)
    except Exception:
        pass

SELECTED_BG_PATH = WALLPAPERS.get(selected_bg_key, WALLPAPERS["✨ 3D Glassmorphic Render"])
LOCAL_BG_PATH = os.path.join(PROJECT_ROOT, "background.png")
if os.path.exists(SELECTED_BG_PATH):
    try:
        import shutil
        shutil.copy(SELECTED_BG_PATH, LOCAL_BG_PATH)
    except Exception:
        pass

def get_base64_bg():
    if os.path.exists(LOCAL_BG_PATH):
        try:
            with open(LOCAL_BG_PATH, "rb") as f:
                data = f.read()
                return base64.b64encode(data).decode()
        except Exception:
            return ""
    return ""

BG_BASE64 = get_base64_bg()



# Temporary Diagnostics Block
# Diagnostics function (can be invoked on demand)
def run_diagnostics_to_file():
    """Runs connection diagnostics and writes results to diag_output.txt."""
    try:
        import json
        import os
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        diag_result = "Diagnostics run started.\n"
        
        client_id = None
        client_secret = None
        if os.path.exists(os.path.join(PROJECT_ROOT, 'credentials.json')):
            with open(os.path.join(PROJECT_ROOT, 'credentials.json'), 'r') as f:
                client_data = json.load(f)
                key = 'installed' if 'installed' in client_data else 'web'
                if key in client_data:
                    client_id = client_data[key].get('client_id')
                    client_secret = client_data[key].get('client_secret')
                    diag_result += f"Found client_id: {client_id}\n"
        
        token_path = os.path.join(PROJECT_ROOT, 'token.json')
        if os.path.exists(token_path):
            with open(token_path, 'r') as f:
                token_data = json.load(f)
            
            # Inject client_id and client_secret if missing
            if 'client_id' not in token_data and client_id:
                token_data['client_id'] = client_id
            if 'client_secret' not in token_data and client_secret:
                token_data['client_secret'] = client_secret
                
            SCOPES = [
                'https://www.googleapis.com/auth/gmail.modify',
                'https://www.googleapis.com/auth/gmail.settings.basic',
                'https://www.googleapis.com/auth/calendar'
            ]
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
            diag_result += f"Loaded creds. Valid: {creds.valid}. Expired: {creds.expired}.\n"
            
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    diag_result += "Attempting to refresh token...\n"
                    try:
                        creds.refresh(Request())
                        diag_result += "Refresh succeeded!\n"
                        # Save refreshed credentials
                        with open(token_path, 'w') as token_file:
                            token_file.write(creds.to_json())
                        diag_result += "Saved refreshed credentials to token.json.\n"
                    except Exception as refresh_err:
                        diag_result += f"Refresh failed: {refresh_err}\n"
                else:
                    diag_result += "Creds are invalid, but cannot refresh (no refresh token or not expired).\n"
            else:
                diag_result += "Creds are already valid.\n"
                
            if creds.valid:
                diag_result += "Building service...\n"
                try:
                    service = build('calendar', 'v3', credentials=creds)
                    diag_result += "Service built. Calling FreeBusy query...\n"
                    import datetime
                    now = datetime.datetime.utcnow().isoformat() + 'Z'
                    later = (datetime.datetime.utcnow() + datetime.timedelta(minutes=30)).isoformat() + 'Z'
                    body = {
                        "timeMin": now,
                        "timeMax": later,
                        "items": [{"id": "primary"}]
                    }
                    res = service.freebusy().query(body=body).execute()
                    diag_result += f"FreeBusy response received: {json.dumps(res)}\n"
                except Exception as api_err:
                    import traceback
                    diag_result += f"FreeBusy API failed: {api_err}\n{traceback.format_exc()}\n"
        else:
            diag_result += "token.json not found.\n"
            
        # Call credentials sync
        diag_result += "Running OAuth credentials sync...\n"
        try:
            from engine import sync_oauth_tokens
            sync_oauth_tokens(PROJECT_ROOT)
            diag_result += "OAuth credentials sync succeeded!\n"
        except Exception as sync_err:
            import traceback
            diag_result += f"OAuth credentials sync failed: {sync_err}\n{traceback.format_exc()}\n"

        with open(os.path.join(PROJECT_ROOT, 'diag_output.txt'), 'w') as f:
            f.write(diag_result)
    except Exception as e:
        import traceback
        with open(os.path.join(PROJECT_ROOT, 'diag_output.txt'), 'w') as f:
            f.write(f"Global exception: {e}\n{traceback.format_exc()}")

# Setup system path to import from gmail-mcp-server folder
sys.path.append(os.path.join(PROJECT_ROOT, "gmail-mcp-server"))

try:
    from triage import triage_inbox
except ImportError:
    # Fallback import logic
    sys.path.append(PROJECT_ROOT)
    # pyrefly: ignore [missing-import]
    from triage import triage_inbox


# 1. Page Configuration
st.set_page_config(
    page_title="Chief of Staff",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject Custom CSS — Premium Immersive Dark-Tech Cyber-Glass Theme
css_style = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700;800&family=Fira+Sans:wght@300;400;500;600;700;800&family=Fira+Code:wght@300;400;500;600;700&display=swap');
    
    /* Premium custom scrollbar styling */
    ::-webkit-scrollbar {
        width: 6px !important;
        height: 6px !important;
    }
    ::-webkit-scrollbar-track {
        background: rgba(15, 23, 42, 0.3) !important;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(139, 92, 246, 0.3) !important;
        border-radius: 4px !important;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(139, 92, 246, 0.5) !important;
    }

    /* Global styling overrides targeting text containers specifically to preserve icon ligatures */
    html, body, p, li, label, h1, h2, h3, h4, h5, h6, input, textarea, select {
        font-family: 'Fira Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        color: #E2E8F0 !important;
    }
    
    html, body {
        background-color: #020617 !important;
        background-image: 
            radial-gradient(circle at center, rgba(15, 23, 42, 0.55) 0%, rgba(2, 6, 23, 0.92) 100%),
            url("data:image/png;base64,BG_IMAGE_BASE64_PLACEHOLDER") !important;
        background-size: cover !important;
        background-attachment: fixed !important;
        background-repeat: no-repeat !important;
        background-position: center center !important;
    }
    
    .stApp, [data-testid="stAppViewContainer"], .stMainViewContainer, section.main, .stMain, [data-testid="stAppViewBlockContainer"], .block-container {
        background: transparent !important;
        background-color: transparent !important;
        color: #E2E8F0 !important;
    }
    
    h1 {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        letter-spacing: -0.04em !important;
        font-family: 'Sora', sans-serif !important;
        line-height: 1.15 !important;
    }
    h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        letter-spacing: -0.03em !important;
        font-family: 'Sora', sans-serif !important;
    }
    
    /* Monospace formatting for data values, logs, code */
    code, pre, .stTextArea textarea, .stTextInput input {
        font-family: 'Fira Code', monospace !important;
    }
    
    /* ============ DARK GLASS SIDEBAR ============ */
    section[data-testid="stSidebar"] {
        background: rgba(10, 15, 30, 0.85) !important;
        backdrop-filter: blur(28px) !important;
        -webkit-backdrop-filter: blur(28px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    section[data-testid="stSidebar"] div[class*="stCaptionContainer"],
    section[data-testid="stSidebar"] .stCaptionContainer {
        color: #94A3B8 !important;
        font-weight: 500 !important;
        opacity: 1 !important;
    }
    
    /* Sidebar Navigation — ALL radio groups: dark frosted capsules */
    section[data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex !important;
        flex-direction: column !important;
        gap: 6px !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label {
        background-color: rgba(30, 41, 59, 0.4) !important;
        border-radius: 8px !important;
        padding: 10px 14px !important;
        color: #94A3B8 !important;
        font-weight: 600 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        width: 100% !important;
        font-size: 0.9rem !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(30, 41, 59, 0.6) !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
        transform: translateX(2px) !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: rgba(139, 92, 246, 0.15) !important;
        color: #C084FC !important;
        font-weight: 700 !important;
        border: 1px solid rgba(139, 92, 246, 0.4) !important;
        border-left: 6px solid #8B5CF6 !important;
        box-shadow: 0 4px 14px rgba(139, 92, 246, 0.15) !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #C084FC !important;
    }
    /* Hide ALL radio dot indicators */
    section[data-testid="stSidebar"] div[role="radiogroup"] label div[role="presentation"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarker"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label input[type="radio"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        margin-left: 0px !important;
    }
    /* Hide radio widget labels */
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
        display: none !important;
    }
    
    /* Sidebar buttons (Frosted white glass capsule) */
    section[data-testid="stSidebar"] div.stButton > button,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"] {
        background: rgba(30, 41, 59, 0.6) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    section[data-testid="stSidebar"] div.stButton > button:hover,
    section[data-testid="stSidebar"] button[data-testid="stBaseButton-primary"]:hover {
        background: rgba(139, 92, 246, 0.2) !important;
        border-color: #8B5CF6 !important;
        transform: translateY(-1px) !important;
        color: #FFFFFF !important;
    }
    
    /* ============ BENTO CARD PANELS (EXPANDERS) ============ */
    div[data-testid="stExpander"] {
        background-color: rgba(11, 17, 33, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25) !important;
        margin-bottom: 20px !important;
        backdrop-filter: blur(28px) !important;
        -webkit-backdrop-filter: blur(28px) !important;
        overflow: hidden;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stExpander"]:hover {
        box-shadow: 0 12px 40px rgba(139, 92, 246, 0.08) !important;
        border-color: rgba(139, 92, 246, 0.3) !important;
    }
    div[data-testid="stExpander"] summary, 
    div[data-testid="stExpander"] .streamlit-expanderHeader {
        background-color: transparent !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 14px 18px !important;
    }
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span[data-testid="stMarkdownContainer"] p,
    div[data-testid="stExpander"] .streamlit-expanderHeader p {
        color: #FFFFFF !important;
        font-family: 'Sora', sans-serif !important;
        font-size: 1rem !important;
    }
    div[data-testid="stExpander"] summary svg,
    div[data-testid="stExpander"] .streamlit-expanderHeader svg {
        fill: #8B5CF6 !important;
        color: #8B5CF6 !important;
    }
    div[data-testid="stExpander"] .streamlit-expanderContent {
        background-color: rgba(10, 16, 32, 0.4) !important;
        color: #E2E8F0 !important;
        border-top: 1px solid rgba(255, 255, 255, 0.06) !important;
        padding: 20px !important;
    }
    
    /* ============ BUTTONS — Secondary (default dark glass) ============ */
    div.stButton > button, 
    div.stDownloadButton > button,
    button[data-testid="stBaseButton-secondary"] {
        background-color: rgba(30, 41, 59, 0.6) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        font-weight: 600 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
        font-size: 0.82rem !important;
    }
    div.stButton > button:hover, 
    div.stDownloadButton > button:hover,
    button[data-testid="stBaseButton-secondary"]:hover {
        border-color: #06B6D4 !important;
        color: #FFFFFF !important;
        background-color: rgba(6, 182, 212, 0.15) !important;
        box-shadow: 0 4px 15px rgba(6, 182, 212, 0.2) !important;
    }
    
    /* ============ BUTTONS — Primary (cyber gradient) ============ */
    button[data-testid="stBaseButton-primary"],
    div.stFormSubmitButton > button {
        background: linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        box-shadow: 0 4px 14px rgba(124, 58, 237, 0.3) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    button[data-testid="stBaseButton-primary"]:hover,
    div.stFormSubmitButton > button:hover {
        box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4) !important;
        transform: translateY(-1px) !important;
        color: #FFFFFF !important;
    }
    div.stButton > button:active, 
    div.stDownloadButton > button:active, 
    div.stFormSubmitButton > button:active,
    button[data-testid="stBaseButton-primary"]:active,
    button[data-testid="stBaseButton-secondary"]:active {
        transform: scale(0.97) !important;
    }
    
    /* ============ TEXT INPUTS ============ */
    .stTextInput input, .stTextArea textarea {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
        caret-color: #FFFFFF !important;
        transition: all 0.2s ease !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.1) !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #06B6D4 !important;
        box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.25) !important;
    }
    /* Explicit placeholder styles for high visibility and contrast */
    .stTextInput input::placeholder, 
    .stTextArea textarea::placeholder,
    .stTextInput input::-webkit-input-placeholder,
    .stTextArea textarea::-webkit-input-placeholder {
        color: #94A3B8 !important;
        opacity: 1 !important;
        -webkit-text-fill-color: #94A3B8 !important;
    }
    .stTextInput label, .stTextArea label, label, [data-testid="stWidgetLabel"] p {
        color: #CBD5E1; /* High contrast label text */
        font-weight: 600 !important;
        font-size: 0.85rem !important;
    }
    
    /* ============ METRIC CARDS ============ */
    div[data-testid="stMetric"] {
        background-color: rgba(11, 17, 33, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 12px !important;
        padding: 18px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 40px rgba(139, 92, 246, 0.12) !important;
        border-color: rgba(139, 92, 246, 0.3) !important;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        font-size: 1.85rem !important;
        font-family: 'Sora', sans-serif !important;
        letter-spacing: -0.02em !important;
        font-variant-numeric: tabular-nums !important;
    }
    div[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p {
        color: #94A3B8 !important;
        font-weight: 700 !important;
        font-size: 0.72rem !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-family: 'Fira Sans', sans-serif !important;
    }
    
    /* ============ INLINE CODE ============ */
    code {
        background-color: rgba(139, 92, 246, 0.12) !important;
        color: #C084FC !important;
        padding: 3px 6px !important;
        border-radius: 6px !important;
        font-size: 0.8rem !important;
        font-family: 'Fira Code', monospace !important;
        border: 1px solid rgba(139, 92, 246, 0.2) !important;
    }
    
    /* ============ TAB BAR ============ */
    div[data-testid="stTabBar"] button, div[data-testid="stTabBar"] p {
        color: #94A3B8 !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        font-family: 'Sora', sans-serif !important;
    }
    div[data-testid="stTabBar"] button[aria-selected="true"], 
    div[data-testid="stTabBar"] button[aria-selected="true"] p {
        color: #06B6D4 !important;
        font-weight: 700 !important;
    }
    div[data-testid="stTabBar"] button:hover, div[data-testid="stTabBar"] button:hover p {
        color: #06B6D4 !important;
    }
 
    /* ============ COLLAPSE CONTROL (Excludes font override to fix icon bug) ============ */
    button[data-testid="collapsedControl"] {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
    }
    button[data-testid="collapsedControl"] svg,
    button[data-testid="collapsedControl"] path,
    [data-testid="collapsedControl"] svg,
    [data-testid="collapsedControl"] span {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        opacity: 1 !important;
    }
    
    /* ============ STATUS CONTAINER ============ */
    div[data-testid="stStatusWidget"],
    div[data-testid="stStatus"] {
        background-color: rgba(11, 17, 33, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stStatusWidget"] * {
        color: #FFFFFF !important;
    }
    
    /* ============ ALERTS ============ */
    .stAlert {
        background-color: rgba(11, 17, 33, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25) !important;
    }
    .stAlert p {
        color: #FFFFFF !important;
        font-weight: 500;
    }
    
    /* ============ FILE UPLOADER ============ */
    div[data-testid="stFileUploader"] > section {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 2px dashed rgba(255, 255, 255, 0.15) !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }
    div[data-testid="stFileUploader"] > section [data-testid="stMarkdownContainer"] p,
    div[data-testid="stFileUploader"] > section span {
        color: #94A3B8 !important;
    }
    div[data-testid="stFileUploader"] button {
        background: linear-gradient(135deg, #7C3AED 0%, #06B6D4 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 12px rgba(124, 58, 237, 0.25) !important;
    }
    div[data-testid="stFileUploader"] button:hover {
        box-shadow: 0 6px 18px rgba(6, 182, 212, 0.35) !important;
    }
    
    /* ============ SELECTBOX / DROPDOWN ============ */
    div[data-testid="stSelectbox"] > div, div[data-testid="stSelectbox"] div[role="button"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        color: #FFFFFF !important;
        border-radius: 8px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    div[data-testid="stSelectbox"] div[role="button"] * {
        color: #FFFFFF !important;
    }
    div[data-baseweb="popover"], div[data-baseweb="menu"], li[role="option"] {
        background-color: #0F172A !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        color: #E2E8F0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
    }
    li[role="option"]:hover {
        color: #06B6D4 !important;
        background-color: rgba(6, 182, 212, 0.1) !important;
    }
    li[role="option"] * {
        color: inherit !important;
    }
    
    /* ============ CUSTOM BADGE CLASSES ============ */
    .badge-urgent {
        background: rgba(244, 63, 94, 0.15) !important;
        color: #FB7185 !important;
        border: 1px solid rgba(244, 63, 94, 0.3) !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        display: inline-block;
    }
    .badge-needs-reply {
        background: rgba(245, 158, 11, 0.15) !important;
        color: #FBBF24 !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        display: inline-block;
    }
    .badge-fyi {
        background: rgba(20, 184, 166, 0.15) !important;
        color: #2DD4BF !important;
        border: 1px solid rgba(20, 184, 166, 0.3) !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        display: inline-block;
    }
    .badge-ignore {
        background: rgba(148, 163, 184, 0.15) !important;
        color: #94A3B8 !important;
        border: 1px solid rgba(148, 163, 184, 0.3) !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        display: inline-block;
    }
    .badge-sent {
        background: rgba(16, 185, 129, 0.15) !important;
        color: #34D399 !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        padding: 4px 12px !important;
        border-radius: 20px !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        display: inline-block;
    }
    
    /* ============ DIVIDERS ============ */
    hr {
        border: none !important;
        border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
        margin: 20px 0 !important;
    }
 
    /* ============ HEADER ACTIONS (DEPLOY, THREE DOTS) ============ */
    header[data-testid="stHeader"] {
        background-color: rgba(10, 15, 30, 0.75) !important;
        backdrop-filter: blur(12px) !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.06) !important;
    }
    header[data-testid="stHeader"] * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    header[data-testid="stHeader"] button:hover *,
    header[data-testid="stHeader"] a:hover * {
        color: #06B6D4 !important;
        fill: #06B6D4 !important;
    }
    
    /* Styled Deploy button */
    header[data-testid="stHeader"] a[href*="share"] {
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        background-color: rgba(30, 41, 59, 0.6) !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
    }
</style>
"""
st.markdown(clean_html(css_style.replace("BG_IMAGE_BASE64_PLACEHOLDER", BG_BASE64)), unsafe_allow_html=True)



# 2. Session State Initialization
def _init_session_state():
    from engine import MOCK_EVENTS
    defaults = {
        "threads": [],
        "triaged": {
            "urgent": [],
            "needs-reply": [],
            "fyi": [],
            "ignore": []
        },
        "drafts": {},
        "approved": {},
        "rejected": set(),
        "sent": set(),
        "booked": {},
        "source": "Sample",
        "pipeline_running": False,
        "pipeline_log": [],
        "current_phase": "Inbox & Triage",
        "mock_events": list(MOCK_EVENTS)
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

_init_session_state()
sidebar_header_html = f"""
<div style='display: flex; align-items: center; gap: 12px; margin-top: 10px; margin-bottom: 20px;'>
    {get_app_logo_svg(32)}
    <div>
        <h1 style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin: 0; line-height: 1.1; font-family: 'Sora', sans-serif;">Chief of Staff AI</h1>
        <p style="font-size: 0.65rem; color: #94A3B8; margin: 0; text-transform: uppercase; font-weight: 600; letter-spacing: 0.05em; font-family: 'Sora', sans-serif; margin-top: 2px;">Executive Workspace</p>
    </div>
</div>
"""
st.sidebar.markdown(clean_html(sidebar_header_html), unsafe_allow_html=True)

# Run Full Pipeline button
if st.sidebar.button("\u25B7 Run Full Pipeline", type="primary", use_container_width=True):
    st.session_state["pipeline_running"] = True
st.sidebar.caption("Fetches, triages, and drafts — stops at Approval Gate.")
st.sidebar.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 14px 0 10px 0;'>", unsafe_allow_html=True)

# 4. Helper Function: Map Custom Thread structure to Triage structure
def map_thread_for_triage(raw_thread: dict) -> dict:
    """Formats raw sample thread data to match requirements of the triage classifier."""
    messages = raw_thread.get("messages", [])
    last_msg = messages[-1] if messages else {}
    sender = last_msg.get("from", "Unknown")
    date = last_msg.get("date", "")
    body = last_msg.get("body", "")
    
    # Calculate a short text preview (snippet)
    snippet = body.strip()
    if len(snippet) > 120:
        snippet = snippet[:120] + "..."
        
    return {
        "id": raw_thread.get("id", "unknown"),
        "sender": sender,
        "subject": raw_thread.get("subject", "(no subject)"),
        "snippet": snippet,
        "date": date,
        "messages": messages
    }


def generate_proof_markdown(approved: dict, actionable_threads: list) -> str:
    """Generates markdown document for approved drafts."""
    today_str = datetime.date.today().strftime("%B %d, %Y")
    md = f"# The Draft Desk - Approved Proof\n"
    md += f"**Date:** {today_str}\n\n"
    md += f"This document contains the approved email drafts verified by your AI Chief of Staff.\n\n"
    md += "---\n\n"
    
    for t in actionable_threads:
        t_id = t.get("id")
        if t_id in approved:
            subject = t.get("subject", "No Subject")
            md += f"## Thread: {subject}\n"
            md += f"**Approved Draft:**\n"
            md += f"```text\n{approved[t_id]}\n```\n\n"
            md += f"**Original Thread History:**\n"
            for msg in t.get("messages", []):
                md += f"> **From:** {msg.get('from')}\n"
                md += f"> **Date:** {msg.get('date')}\n"
                md += f"> \n"
                body_lines = msg.get('body', '').splitlines()
                for line in body_lines:
                    md += f"> {line}\n"
                md += f"> \n"
            md += "\n---\n\n"
            
    # Append Action Log
    from task_logger import get_action_log
    log_entries = get_action_log()
    if log_entries:
        md += "# Action Log\n\n"
        md += "| Action Type | Thread Subject | Detail | Timestamp |\n"
        md += "| :--- | :--- | :--- | :--- |\n"
        for entry in log_entries:
            # Format timestamp
            formatted_ts = ""
            try:
                import datetime as dt
                ts_str = entry.get("timestamp", "")
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                ts = dt.datetime.fromisoformat(ts_str)
                formatted_ts = ts.strftime("%b %d %I:%M %p")
            except Exception:
                formatted_ts = entry.get("timestamp", "")
            
            a_type = entry.get("action_type", "").upper()
            subject = entry.get("thread_subject", "")
            detail = entry.get("detail", "")
            md += f"| {a_type} | {subject} | `{detail}` | {formatted_ts} |\n"
        md += "\n"
        
    return md


def generate_proof_html(approved: dict, actionable_threads: list) -> str:
    """Generates a responsive dark-theme HTML document with side-by-side comparison grid."""
    today_str = datetime.date.today().strftime("%B %d, %Y")
    
    html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>The Draft Desk - Approved Proof</title>
    <style>
        body {
            background-color: #f1f3f4;
            color: #1e293b;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 40px;
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #1e293b;
            border-bottom: 2px solid #dadce0;
            padding-bottom: 10px;
        }
        .meta {
            color: #5f6368;
            margin-bottom: 30px;
        }
        .thread-container {
            margin-bottom: 40px;
            border: 1px solid #dadce0;
            border-radius: 8px;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.7);
        }
        .thread-title {
            color: #1e293b;
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1.5em;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .left-col {
            border: 2px solid #fde293;
            border-radius: 6px;
            padding: 15px;
            background-color: rgba(255, 255, 255, 0.5);
            max-height: 400px;
            overflow-y: auto;
        }
        .right-col {
            border: 2px solid #ceead6;
            border-radius: 6px;
            padding: 15px;
            background-color: rgba(255, 255, 255, 0.5);
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 1.1em;
            color: #1e293b;
        }
        .message-block {
            margin-bottom: 15px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.05);
            padding-bottom: 10px;
        }
        .message-block:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }
        .msg-meta {
            font-size: 0.85em;
            color: #5f6368;
            margin-bottom: 8px;
        }
        .msg-body {
            white-space: pre-wrap;
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <h1>✍️ The Draft Desk - Approved Proofs</h1>
    <div class="meta">Generated on {today_str} | Verified by Chief of Staff Agent</div>
""".replace("{today_str}", today_str)
    
    for t in actionable_threads:
        t_id = t.get("id")
        if t_id in approved:
            subject = t.get("subject", "No Subject")
            draft_text = approved[t_id]
            
            html += """
    <div class="thread-container">
        <div class="thread-title">Subject: {subject}</div>
        <div class="grid">
            <div class="left-col">
                <h3>Original Thread</h3>
""".replace("{subject}", subject)
            for msg in t.get("messages", []):
                html += """
                <div class="message-block">
                    <div class="msg-meta"><strong>From:</strong> {msg_from} | <strong>Date:</strong> {msg_date}</div>
                    <div class="msg-body">{msg_body}</div>
                </div>
""".replace("{msg_from}", str(msg.get('from', ''))).replace("{msg_date}", str(msg.get('date', ''))).replace("{msg_body}", str(msg.get('body', '')))
            html += """
            </div>
            <div class="right-col">
                <h3>Approved Draft Reply</h3>
                {draft_text}
            </div>
        </div>
    </div>
""".replace("{draft_text}", draft_text)
            
    # Append Action Log
    from task_logger import get_action_log
    log_entries = get_action_log()
    if log_entries:
        html += """
    <div style="margin-top: 40px; border: 1px solid #dadce0; border-radius: 8px; padding: 20px; background-color: rgba(255,255,255,0.7);">
        <h2 style="color: #1e293b; margin-top: 0; border-bottom: 2px solid #dadce0; padding-bottom: 10px;">📋 Action Log</h2>
        <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
            <thead>
                <tr style="border-bottom: 2px solid #dadce0; text-align: left; color: #5f6368;">
                    <th style="padding: 10px;">Action</th>
                    <th style="padding: 10px;">Subject</th>
                    <th style="padding: 10px;">Detail</th>
                    <th style="padding: 10px;">Timestamp</th>
                </tr>
            </thead>
            <tbody>
"""
        for entry in log_entries:
            # Format timestamp
            formatted_ts = ""
            try:
                import datetime as dt
                ts_str = entry.get("timestamp", "")
                if ts_str.endswith("Z"):
                    ts_str = ts_str[:-1] + "+00:00"
                ts = dt.datetime.fromisoformat(ts_str)
                formatted_ts = ts.strftime("%b %d %I:%M %p")
            except Exception:
                formatted_ts = entry.get("timestamp", "")
            
            a_type = entry.get("action_type", "").upper()
            icon = "📄" if entry.get("action_type") == "sent" else "🗓️"
            subject = entry.get("thread_subject", "")
            detail = entry.get("detail", "")
            
            html += """
                <tr style="border-bottom: 1px solid #dadce0;">
                    <td style="padding: 10px; font-weight: bold; color: #1e293b;">{icon} {a_type}</td>
                    <td style="padding: 10px; color: #1e293b;">{subject}</td>
                    <td style="padding: 10px; font-family: monospace; color: #1e293b;">{detail}</td>
                    <td style="padding: 10px; color: #5f6368; font-size: 0.9em;">{formatted_ts}</td>
                </tr>
""".replace("{icon}", icon).replace("{a_type}", a_type).replace("{subject}", subject).replace("{detail}", detail).replace("{formatted_ts}", formatted_ts)
        html += """
            </tbody>
        </table>
    </div>
"""

    html += """
</body>
</html>
"""
    return html


def _get_fetch_threads():
    """Loader for fetch_threads from engine."""
    from engine import fetch_threads
    return fetch_threads


def _get_send_reply():
    """Loader for send_reply from engine."""
    from engine import send_reply
    return send_reply


def _get_calendar_engine():
    """Loader for calendar_engine module and forces reloading from disk."""
    import calendar_engine
    import importlib
    importlib.reload(calendar_engine)
    return calendar_engine


def _get_draft_reply():
    """Loader for draft_reply from draft_machine."""
    from draft_machine import draft_reply
    return draft_reply


def load_sample_threads():
    """Loads and maps sample threads from sample_threads.json."""
    with open("sample_threads.json", "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    mapped_threads = []
    for t in raw_data:
        mapped_threads.append(map_thread_for_triage(t))
    return mapped_threads


def fetch_threads_via_engine():
    """Fetches and maps threads from the Gmail MCP engine."""
    fetch_threads = _get_fetch_threads()
    raw_threads = fetch_threads()
    mapped_threads = []
    for t in raw_threads:
        mapped_threads.append({
            "id": t.get("thread_id"),
            "subject": t.get("subject"),
            "sender": t.get("sender"),
            "snippet": t.get("snippet"),
            "date": t.get("date"),
            "messages": t.get("messages", [
                {"from": t.get("sender"), "date": t.get("date"), "body": t.get("body", t.get("snippet"))}
            ])
        })
    return mapped_threads


def triage_threads(mapped_threads):
    """Triages the given mapped threads and stores them in session state."""
    from triage import triage_inbox
    triaged_results = triage_inbox(mapped_threads)
    groups = {
        "urgent": [],
        "needs-reply": [],
        "fyi": [],
        "ignore": []
    }
    for t in triaged_results:
        t["_category"] = t.get("category", "")
        p = t.get("priority", "fyi").lower()
        if p not in groups:
            p = "fyi"
        groups[p].append(t)
    st.session_state["threads"] = triaged_results
    st.session_state["triaged"] = groups
    return triaged_results


def run_full_pipeline():
    """
    Runs the full email processing pipeline:
    1. Read source from session state.
    2. Load or fetch threads.
    3. Triage threads.
    4. Reset downstream state.
    5. Generate draft replies for urgent and needs-reply threads.
    6. Switch phase to Approval Gate.
    Returns a list of log strings.
    """
    logs = []
    logs.append("[INFO] Starting run_full_pipeline...")
    
    # 1. Read source
    source = st.session_state.get("source", "Sample")
    logs.append(f"[INFO] Thread source determined as: {source}")
    
    # 2. Fetch threads
    mapped_threads = []
    try:
        if source == "Sample":
            logs.append("[INFO] Loading sample threads...")
            mapped_threads = load_sample_threads()
        else:
            logs.append("[INFO] Fetching threads via Gmail engine...")
            try:
                mapped_threads = fetch_threads_via_engine()
            except Exception as e:
                logs.append(f"[WARNING] Could not connect to Gmail MCP: {e}. Falling back to mock engine threads.")
                from engine import MOCK_THREADS
                raw_threads = MOCK_THREADS
                mapped_threads = []
                for t in raw_threads:
                    mapped_threads.append({
                        "id": t.get("thread_id"),
                        "subject": t.get("subject"),
                        "sender": t.get("sender"),
                        "snippet": t.get("snippet"),
                        "date": t.get("date"),
                        "messages": t.get("messages", [
                            {"from": t.get("sender"), "date": t.get("date"), "body": t.get("body", t.get("snippet"))}
                        ])
                    })
        logs.append(f"[INFO] Successfully loaded/fetched {len(mapped_threads)} threads.")
    except Exception as e:
        logs.append(f"[ERROR] Failed to fetch threads: {e}")
        return logs

    # 3. Call triage_threads
    if not mapped_threads:
        logs.append("[WARNING] No threads to triage. Pipeline stopping.")
        return logs
        
    try:
        logs.append("[INFO] Running priority classification...")
        triage_threads(mapped_threads)
        logs.append("[INFO] Triage completed successfully.")
    except Exception as e:
        logs.append(f"[ERROR] Triage failed: {e}")
        return logs

    # 4. Reset downstream state
    logs.append("[INFO] Resetting downstream session states...")
    st.session_state["drafts"] = {}
    st.session_state["approved"] = {}
    st.session_state["rejected"] = set()
    st.session_state["sent"] = set()
    st.session_state["booked"] = {}
    st.session_state["balloons_triggered"] = False
    
    # 5. Generate drafts for urgent + needs-reply threads
    triaged = st.session_state.get("triaged", {})
    actionable_threads = triaged.get("urgent", []) + triaged.get("needs-reply", [])
    logs.append(f"[INFO] Found {len(actionable_threads)} actionable threads (Urgent/Needs Reply) needing replies.")
    
    if actionable_threads:
        try:
            draft_reply_func = _get_draft_reply()
            for idx, t in enumerate(actionable_threads):
                t_id = t.get("id", "unknown")
                subject = t.get("subject", "No Subject")
                logs.append(f"[INFO] ({idx+1}/{len(actionable_threads)}) Drafting reply for: '{subject}'...")
                try:
                    draft_text = draft_reply_func(t)
                    st.session_state["drafts"][t_id] = draft_text
                    logs.append(f"[INFO] Draft generated successfully for: '{subject}'.")
                except Exception as draft_err:
                    logs.append(f"[ERROR] Failed to generate draft for '{subject}': {draft_err}")
        except Exception as e:
            logs.append(f"[ERROR] Setup for draft generation failed: {e}")
    else:
        logs.append("[INFO] No actionable threads found. Skipping draft generation.")

    # 6. Set current_phase to "Approval Gate"
    logs.append("[INFO] Switching current phase to 'Approval Gate'.")
    st.session_state["current_phase"] = "Approval Gate"
    
    logs.append("[INFO] run_full_pipeline finished.")
    return logs


def _render_pipeline_execution(source):
    """
    Executes the full pipeline inline, showing live progress within a st.status container,
    and updates session state upon completion.
    """
    pipeline_log = []
    pipeline_log.append("[INFO] Starting pipeline execution...")
    
    # Use st.status as the container
    with st.status("Running full pipeline...", expanded=True) as status:
        # Step 1: Fetch
        status.update(label="Fetching threads...")
        pipeline_log.append(f"[INFO] Thread source determined as: {source}")
        
        mapped_threads = []
        try:
            if source == "Sample":
                pipeline_log.append("[INFO] Loading sample threads...")
                mapped_threads = load_sample_threads()
            else:
                pipeline_log.append("[INFO] Fetching threads via Gmail engine...")
                try:
                    mapped_threads = fetch_threads_via_engine()
                except Exception as fetch_err:
                    pipeline_log.append(f"[WARNING] Could not connect to Gmail MCP: {fetch_err}. Falling back to mock engine threads.")
                    from engine import MOCK_THREADS
                    raw_threads = MOCK_THREADS
                    mapped_threads = []
                    for t in raw_threads:
                        mapped_threads.append({
                            "id": t.get("thread_id"),
                            "subject": t.get("subject"),
                            "sender": t.get("sender"),
                            "snippet": t.get("snippet"),
                            "date": t.get("date"),
                            "messages": t.get("messages", [
                                {"from": t.get("sender"), "date": t.get("date"), "body": t.get("body", t.get("snippet"))}
                            ])
                        })
            pipeline_log.append(f"[INFO] Successfully loaded/fetched {len(mapped_threads)} threads.")
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #059669; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                Threads fetched successfully
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            pipeline_log.append(f"[ERROR] Failed to fetch threads: {e}")
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #E11D48; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                Fetch failed: {e}
            </div>
            """, unsafe_allow_html=True)
            status.update(state="error", label="Pipeline failed at fetch step")
            st.session_state["pipeline_running"] = False
            st.session_state["pipeline_log"] = pipeline_log
            return
            
        # Step 2: Triage
        status.update(label="Triaging threads...")
        if not mapped_threads:
            pipeline_log.append("[WARNING] No threads to triage. Pipeline stopping.")
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #E11D48; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                No threads to triage.
            </div>
            """, unsafe_allow_html=True)
            status.update(state="error", label="Pipeline stopped: No threads found")
            st.session_state["pipeline_running"] = False
            st.session_state["pipeline_log"] = pipeline_log
            return
            
        try:
            pipeline_log.append("[INFO] Running priority classification...")
            triage_threads(mapped_threads)
            pipeline_log.append("[INFO] Triage completed successfully.")
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #059669; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                Triage completed successfully
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            pipeline_log.append(f"[ERROR] Triage failed: {e}")
            st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #E11D48; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                Triage failed: {e}
            </div>
            """, unsafe_allow_html=True)
            status.update(state="error", label="Pipeline failed at triage step")
            st.session_state["pipeline_running"] = False
            st.session_state["pipeline_log"] = pipeline_log
            return
            
        # Reset downstream state
        pipeline_log.append("[INFO] Resetting downstream session states...")
        st.session_state["drafts"] = {}
        st.session_state["approved"] = {}
        st.session_state["rejected"] = set()
        st.session_state["sent"] = set()
        st.session_state["booked"] = {}
        st.session_state["balloons_triggered"] = False
        
        # Step 3: Draft loop
        status.update(label="Generating drafts...")
        triaged = st.session_state.get("triaged", {})
        actionable_threads = triaged.get("urgent", []) + triaged.get("needs-reply", [])
        pipeline_log.append(f"[INFO] Found {len(actionable_threads)} actionable threads (Urgent/Needs Reply) needing replies.")
        
        if actionable_threads:
            try:
                draft_reply_func = _get_draft_reply()
                for idx, t in enumerate(actionable_threads):
                    t_id = t.get("id", "unknown")
                    subject = t.get("subject", "No Subject")
                    pipeline_log.append(f"[INFO] ({idx+1}/{len(actionable_threads)}) Drafting reply for: '{subject}'...")
                    try:
                        draft_text = draft_reply_func(t)
                        st.session_state["drafts"][t_id] = draft_text
                        pipeline_log.append(f"[INFO] Draft generated successfully for: '{subject}'.")
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #059669; margin-bottom: 6px;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                            Generated draft for: '{subject}'
                        </div>
                        """, unsafe_allow_html=True)
                    except Exception as draft_err:
                        pipeline_log.append(f"[ERROR] Failed to generate draft for '{subject}': {draft_err}")
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #E11D48; margin-bottom: 6px;">
                            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                            Failed to generate draft for '{subject}': {draft_err}
                        </div>
                        """, unsafe_allow_html=True)
            except Exception as e:
                pipeline_log.append(f"[ERROR] Setup for draft generation failed: {e}")
                st.markdown(f"""
                <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #E11D48; margin-bottom: 6px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                    Draft generation setup failed: {e}
                </div>
                """, unsafe_allow_html=True)
        else:
            pipeline_log.append("[INFO] No actionable threads found. Skipping draft generation.")
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px; font-family: 'Fira Sans', sans-serif; font-size: 0.82rem; color: #64748B; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                No actionable threads found. Skipped draft generation.
            </div>
            """, unsafe_allow_html=True)
            
        pipeline_log.append("[INFO] Pipeline execution completed successfully.")
        status.update(state="complete", label="Pipeline execution complete!")

    # Outside the status block:
    st.session_state["pipeline_log"] = pipeline_log
    st.session_state["current_phase"] = "Approval Gate"
    st.session_state["pipeline_running"] = False
    st.rerun()


def _render_top_navbar(title, show_actions=True):
    source_val = st.session_state.get("source", "Sample")
    if source_val == "Gmail":
        badge_html = """
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 6px; padding: 6px 12px; font-family: 'Fira Sans', sans-serif; font-size: 0.78rem; color: #34D399; font-weight: 600; display: flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(16,185,129,0.05);">
            <span style="width: 6px; height: 6px; background: #34D399; border-radius: 50%; display: inline-block;"></span>
            LIVE GMAIL API
        </div>
        """
    else:
        badge_html = """
        <div style="background: rgba(139, 92, 246, 0.08); border: 1px solid rgba(139, 92, 246, 0.2); border-radius: 6px; padding: 6px 12px; font-family: 'Fira Sans', sans-serif; font-size: 0.78rem; color: #C084FC; font-weight: 600; display: flex; align-items: center; gap: 6px; box-shadow: 0 4px 12px rgba(139,92,246,0.05);">
            <span style="width: 6px; height: 6px; background: #8B5CF6; border-radius: 50%; display: inline-block;"></span>
            DEMO SANDBOX
        </div>
        """
    badge_html = clean_html(badge_html)

    logo_svg = get_app_logo_svg(26)
    navbar_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px 24px; background: rgba(11, 17, 33, 0.95); backdrop-filter: blur(12px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; margin-bottom: 24px; box-shadow: 0 8px 32px rgba(0,0,0,0.25); min-height: 68px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            {logo_svg}
            <div>
                <h2 style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; margin: 0; font-family: 'Sora', sans-serif; line-height: 1.1;">{title}</h2>
                <p style="font-size: 0.62rem; color: #94A3B8; margin: 0; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; font-family: 'Sora', sans-serif; margin-top: 1px;">Chief of Staff Workspace</p>
            </div>
        </div>
        <div>
            {badge_html}
        </div>
    </div>
    """
    st.markdown(clean_html(navbar_html), unsafe_allow_html=True)


def render_unified_dashboard():
    """Renders the single-screen integrated Chief of Staff dashboard workspace."""
    if not st.session_state.get("threads"):
        _render_top_navbar("Workspace", show_actions=False)
    else:
        _render_top_navbar("Workspace", show_actions=True)
    
    # 1. State extraction
    triaged = st.session_state["triaged"]
    actionable_threads = triaged.get("urgent", []) + triaged.get("needs-reply", [])
    drafts = st.session_state["drafts"]
    approved = st.session_state["approved"]
    rejected = st.session_state["rejected"]
    sent = st.session_state["sent"]

    # Render premium unified top metrics stats deck
    if st.session_state.get("threads"):
        inbox_count = len(st.session_state.get("threads", []))
        action_count = len(triaged.get("urgent", [])) + len(triaged.get("needs-reply", []))
        draft_count = len(drafts)
        approved_count = len(approved)
        
        metrics_html = f"""
        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
            <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 14px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);">
                <div style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 8px; background: rgba(6, 182, 212, 0.15); color: #06B6D4; flex-shrink: 0;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-inbox"><polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/></svg>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #94A3B8; letter-spacing: 0.08em; font-family: 'Fira Sans', sans-serif; line-height: 1.1;">Inbox Threads</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; margin-top: 2px; line-height: 1.1;">{inbox_count}</div>
                </div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 14px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);">
                <div style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 8px; background: rgba(244, 63, 94, 0.15); color: #FB7185; flex-shrink: 0;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-alert-triangle"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #94A3B8; letter-spacing: 0.08em; font-family: 'Fira Sans', sans-serif; line-height: 1.1;">Action Required</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; margin-top: 2px; line-height: 1.1;">{action_count}</div>
                </div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 14px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);">
                <div style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 8px; background: rgba(139, 92, 246, 0.15); color: #C084FC; flex-shrink: 0;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-file-text"><path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #94A3B8; letter-spacing: 0.08em; font-family: 'Fira Sans', sans-serif; line-height: 1.1;">Drafts Ready</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; margin-top: 2px; line-height: 1.1;">{draft_count}</div>
                </div>
            </div>
            <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 14px; box-shadow: 0 8px 32px rgba(0,0,0,0.2);">
                <div style="display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 8px; background: rgba(16, 185, 129, 0.15); color: #34D399; flex-shrink: 0;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-check-circle"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <div>
                    <div style="font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #94A3B8; letter-spacing: 0.08em; font-family: 'Fira Sans', sans-serif; line-height: 1.1;">Approved</div>
                    <div style="font-size: 1.6rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; margin-top: 2px; line-height: 1.1;">{approved_count}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(clean_html(metrics_html), unsafe_allow_html=True)
    
    # 2. Welcome Banner: If no threads are pulled or triaged yet
    if not st.session_state.get("threads"):
        logo_welcome = get_app_logo_svg(72)
        welcome_banner_html = f"""
        <div style='text-align: center; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px; margin-bottom: 24px; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4); backdrop-filter: blur(24px); max-width: 700px; margin-left: auto; margin-right: auto; overflow: hidden; background-color: rgba(11, 17, 33, 0.95); background-image: radial-gradient(at 10% 10%, rgba(139, 92, 246, 0.1) 0px, transparent 50%), radial-gradient(at 90% 10%, rgba(6, 182, 212, 0.1) 0px, transparent 50%); padding: 50px 30px;'>
            <div style='margin-bottom: 24px; display: inline-block;'>{logo_welcome}</div>
            <h2 style='color: #FFFFFF; margin-bottom: 12px; font-size: 2.25rem; font-weight: 800; letter-spacing: -0.03em; font-family: "Sora", sans-serif;'>Welcome to your Chief of Staff</h2>
            <p style='color: #CBD5E1; max-width: 520px; margin: 0 auto; font-size: 1.05rem; line-height: 1.6; font-weight: 500;'>Pull your latest email threads from Gmail or sample files. Gemini will classify priorities and generate draft replies.</p>
        </div>
        """
        st.markdown(clean_html(welcome_banner_html), unsafe_allow_html=True)
        
        # Center container for button
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            pull_clicked = st.button("Pull & Triage Inbox", type="primary", use_container_width=True)
            if pull_clicked:
                st.session_state["drafts"] = {}
                st.session_state["approved"] = {}
                st.session_state["rejected"] = set()
                st.session_state["balloons_triggered"] = False
               # Helper function to render horizontal categories bento grids
    def _render_bento_grid(triaged_groups):
        st.markdown("### Active Threads Feed")
        
        # Priority accent color map (Stripe/Figma Vibrant Accents)
        accent_colors = {
            "urgent": "#E11D48",        # Crimson
            "needs-reply": "#D97706",    # Amber
            "fyi": "#0D9488",            # Teal
            "ignore": "#64748B"          # Slate
        }
        
        categories = [
            ("🚨 Action Required", "urgent"),
            ("💬 Awaiting Response", "needs-reply"),
            ("📋 Needs Review", "fyi"),
            ("🗑️ Ignore", "ignore")
        ]
        
        for title, key in categories:
            threads = triaged_groups.get(key, [])
            accent = accent_colors.get(key, "#64748B")
            
            svg_icon = {
                "urgent": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #E11D48; display: inline-block; vertical-align: middle;"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
                "needs-reply": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #D97706; display: inline-block; vertical-align: middle;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
                "fyi": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #0D9488; display: inline-block; vertical-align: middle;"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
                "ignore": '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #64748B; display: inline-block; vertical-align: middle;"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>'
            }.get(key, "")
            
            title_text = {
                "urgent": "Action Required",
                "needs-reply": "Awaiting Response",
                "fyi": "Needs Review",
                "ignore": "Ignore"
            }.get(key, title)
            
            header_html = f"""
            <div style="display: flex; align-items: center; gap: 8px; margin-top: 14px; margin-bottom: 8px;">
                {svg_icon}
                <span style="font-size: 0.88rem; font-weight: 700; color: #FFFFFF; font-family: 'Sora', sans-serif;">{title_text}</span>
                <span style="font-size: 0.7rem; font-weight: 600; color: #94A3B8; background: rgba(255, 255, 255, 0.06); padding: 2px 8px; border-radius: 20px; font-family: 'Fira Sans', sans-serif;">{len(threads)}</span>
            </div>
            """
            st.markdown(clean_html(header_html), unsafe_allow_html=True)
            
            if not threads:
                st.caption("No threads in this category.")
                st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid rgba(255, 255, 255, 0.08);'>", unsafe_allow_html=True)
                continue
                
            # Show all threads horizontally in rows of 3 per category
            for row_start in range(0, len(threads), 3):
                row_threads = threads[row_start:row_start+3]
                cols = st.columns(3)
                for idx, t in enumerate(row_threads):
                    with cols[idx]:
                        sender_name = t.get('sender', 'Unknown').split("<")[0].strip()
                        sender_initial = sender_name[0].upper() if sender_name else "?"
                        subject = t.get('subject', 'No Subject')
                        snippet = t.get('snippet', '')
                        t_id = t.get('id')
                    
                    is_selected = st.session_state.get("selected_thread_id") == t_id
                    border_style = f"border: 1px solid #8B5CF6; border-left: 5px solid {accent};" if is_selected else f"border: 1px solid rgba(255, 255, 255, 0.08); border-left: 5px solid {accent};"
                    card_bg = "background: rgba(139, 92, 246, 0.22);" if is_selected else "background: rgba(11, 17, 33, 0.95);"
                    shadow = "box-shadow: 0 8px 32px rgba(139, 92, 246, 0.12);" if is_selected else "box-shadow: 0 4px 15px rgba(0,0,0,0.2);"
                    
                    card_style = f"""
                    <div style='{card_bg} {border_style} border-radius: 12px; padding: 14px; {shadow} backdrop-filter: blur(12px); min-height: 110px; display: flex; flex-direction: column; justify-content: space-between; transition: all 0.2s ease;'>
                        <div>
                           <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
                               <div style='display: flex; align-items: center; gap: 8px;'>
                                   <div style='width: 24px; height: 24px; background: rgba(139, 92, 246, 0.2); color: #C084FC; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.72rem; font-weight: 700;'>{sender_initial}</div>
                                   <span style='font-size: 0.75rem; font-weight: 700; color: #FFFFFF; font-family: "Fira Sans", sans-serif;'>{sender_name}</span>
                                </div>
                               <span style='font-size: 0.65rem; color: #94A3B8; font-weight: 600;'>Now</span>
                           </div>
                           <div style='font-size: 0.8rem; font-weight: 800; color: #FFFFFF; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: "Sora", sans-serif;'>{subject}</div>
                           <div style='font-size: 0.72rem; color: #94A3B8; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; font-family: "Fira Sans", sans-serif;'>{snippet}</div>
                        </div>
                    </div>
                    """
                    st.markdown(clean_html(card_style), unsafe_allow_html=True)
                    
                    if is_selected:
                        st.button("👉 Selected", key=f"sel_{t_id}", use_container_width=True, type="primary")
                    else:
                        btn_label = "✏️ Review Draft" if key in ["urgent", "needs-reply"] else "👀 View History"
                        if st.button(btn_label, key=f"sel_{t_id}", use_container_width=True):
                            st.session_state["selected_thread_id"] = t_id
                            st.rerun()
            st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(255, 255, 255, 0.08);'>", unsafe_allow_html=True)

    # 3. Generate Drafts Banner: If triage has finished but drafts are empty
    if actionable_threads and not drafts:
        _render_bento_grid(triaged)
        st.markdown("---")
        logo_drafts = get_app_logo_svg(64)
        drafts_banner_html = f"""
        <div style='text-align: center; padding: 40px 30px; background: rgba(11, 17, 33, 0.95); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px; margin-bottom: 24px; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4); backdrop-filter: blur(12px); max-width: 700px; margin-left: auto; margin-right: auto; margin-top: 20px;'>
            <div style='margin-bottom: 16px; display: inline-block;'>{logo_drafts}</div>
            <h3 style='color: #FFFFFF; margin-bottom: 8px; font-size: 1.6rem; font-weight: 800; letter-spacing: -0.02em;'>Generate AI Drafts</h3>
            <p style='color: #CBD5E1; max-width: 520px; margin: 0 auto; font-size: 1rem; line-height: 1.5; font-weight: 400;'>Generate context-aware email replies and calendar bookings using your Tone Profile.</p>
        </div>
        """
        st.markdown(clean_html(drafts_banner_html), unsafe_allow_html=True)
        
        # Center container for button
        _, btn_col, _ = st.columns([1, 2, 1])
        with btn_col:
            gen_clicked = st.button("Generate Drafts for All Actionable Emails", type="primary", use_container_width=True)
        if gen_clicked:
            from draft_machine import draft_reply
            progress_bar = st.progress(0.0)
            status_text = st.empty()
            
            for idx, t in enumerate(actionable_threads):
                t_id = t.get("id", "unknown")
                status_text.text(f"Drafting reply for: {t.get('subject', 'No Subject')}...")
                try:
                    st.session_state["drafts"][t_id] = draft_reply(t)
                except Exception as e:
                    st.error(f"Error drafting: {e}")
                progress_bar.progress((idx + 1) / len(actionable_threads))
                
            status_text.text("Drafting completed!")
            st.success("Generated drafts successfully!")
            st.rerun()
        return

    # 4. Determine currently selected thread ID
    selected_thread_id = st.session_state.get("selected_thread_id")
    actionable_with_drafts = [t for t in actionable_threads if t.get("id") in drafts]
    
    if selected_thread_id not in drafts and actionable_with_drafts:
        selected_thread_id = actionable_with_drafts[0].get("id")
        st.session_state["selected_thread_id"] = selected_thread_id
        
    selected_thread = next((t for t in actionable_threads if t.get("id") == selected_thread_id), None)

    # 3. Main Workspace Grid: True 3-Column Layout
    col_feed, col_editor, col_widgets = st.columns([1.1, 1.3, 0.9])
    
    with col_feed:
        st.markdown("### ⚡ Active Threads Feed")
        
        # Scrollable feed container to prevent page vertical stretch
        with st.container(height=600, border=False):
            # Priority accent color map (Stripe/Figma Vibrant Accents)
            accent_colors = {
                "urgent": "#E11D48",        # Crimson
                "needs-reply": "#D97706",    # Amber
                "fyi": "#0D9488",            # Teal
                "ignore": "#64748B"          # Slate
            }
            
            categories = [
                ("🚨 Action Required", "urgent"),
                ("💬 Awaiting Response", "needs-reply"),
                ("📋 Needs Review", "fyi"),
                ("🗑️ Ignore", "ignore")
            ]
            
            for title, key in categories:
                threads_in_cat = triaged.get(key, [])
                accent = accent_colors.get(key, "#64748B")
                
                svg_icon = {
                    "urgent": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #E11D48; display: inline-block; vertical-align: middle;"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>',
                    "needs-reply": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #D97706; display: inline-block; vertical-align: middle;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
                    "fyi": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #0D9488; display: inline-block; vertical-align: middle;"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
                    "ignore": '<svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="color: #64748B; display: inline-block; vertical-align: middle;"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>'
                }.get(key, "")
                
                title_text = {
                    "urgent": "Action Required",
                    "needs-reply": "Awaiting Response",
                    "fyi": "Needs Review",
                    "ignore": "Ignore"
                }.get(key, title)
                
                header_html = f"""
                <div style="display: flex; align-items: center; gap: 8px; margin-top: 14px; margin-bottom: 8px;">
                    {svg_icon}
                    <span style="font-size: 0.82rem; font-weight: 700; color: #FFFFFF; font-family: 'Sora', sans-serif;">{title_text}</span>
                    <span style="font-size: 0.68rem; font-weight: 600; color: #94A3B8; background: rgba(255, 255, 255, 0.06); padding: 2px 7px; border-radius: 20px; font-family: 'Fira Sans', sans-serif;">{len(threads_in_cat)}</span>
                </div>
                """
                st.markdown(header_html, unsafe_allow_html=True)
                
                if not threads_in_cat:
                    st.caption("No threads in this category.")
                    continue
                    
                for t in threads_in_cat:
                    sender_name = t.get('sender', 'Unknown').split("<")[0].strip()
                    sender_initial = sender_name[0].upper() if sender_name else "?"
                    subject = t.get('subject', 'No Subject')
                    snippet = t.get('snippet', '')
                    t_id = t.get('id')
                    
                    is_selected = (selected_thread_id == t_id)
                    border_style = f"border: 1px solid #8B5CF6; border-left: 5px solid {accent};" if is_selected else f"border: 1px solid rgba(255, 255, 255, 0.08); border-left: 5px solid {accent};"
                    card_bg = "background: rgba(139, 92, 246, 0.22);" if is_selected else "background: rgba(11, 17, 33, 0.95);"
                    shadow = "box-shadow: 0 8px 32px rgba(139, 92, 246, 0.12);" if is_selected else "box-shadow: 0 4px 15px rgba(0,0,0,0.2);"
                    
                    # Check status
                    status_label = "Pending"
                    if t_id in sent:
                        status_label = "Sent"
                    elif t_id in approved:
                        status_label = "Approved"
                    elif t_id in rejected:
                        status_label = "Rejected"
                    elif key in ["urgent", "needs-reply"]:
                        status_label = "Action Required"
                    else:
                        status_label = "FYI"
                    
                    status_badge = ""
                    if status_label == "Action Required":
                        status_badge = f"<span class='badge-urgent'>Action Required</span>"
                    elif status_label == "Approved":
                        status_badge = f"<span class='badge-sent'>Approved</span>"
                    elif status_label == "Sent":
                        status_badge = f"<span class='badge-sent'>Sent</span>"
                    elif status_label == "Rejected":
                        status_badge = f"<span class='badge-urgent'>Rejected</span>"
                    else:
                        status_badge = f"<span class='badge-fyi'>{status_label}</span>"
                    
                    card_style = f"""
                    <div style='{card_bg} {border_style} border-radius: 12px; padding: 12px; {shadow} backdrop-filter: blur(16px); display: flex; flex-direction: column; gap: 8px; margin-bottom: 8px; transition: all 0.2s ease;'>
                        <div style='display: flex; justify-content: space-between; align-items: center;'>
                            <div style='display: flex; align-items: center; gap: 6px;'>
                                <div style='width: 22px; height: 22px; background: rgba(139, 92, 246, 0.2); color: #C084FC; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.68rem; font-weight: 700;'>{sender_initial}</div>
                                <span style='font-size: 0.72rem; font-weight: 700; color: #FFFFFF; font-family: "Fira Sans", sans-serif;'>{sender_name}</span>
                            </div>
                            {status_badge}
                        </div>
                        <div style='font-size: 0.78rem; font-weight: 800; color: #FFFFFF; line-height: 1.25; font-family: "Sora", sans-serif;'>{subject}</div>
                        <div style='font-size: 0.7rem; color: #94A3B8; line-height: 1.35; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; font-family: "Fira Sans", sans-serif;'>{snippet}</div>
                    </div>
                    """
                    st.markdown(card_style, unsafe_allow_html=True)
                    
                    # Review button below card
                    if is_selected:
                        st.button("👉 Selected", key=f"sel_{t_id}", use_container_width=True, type="primary")
                    else:
                        btn_label = "✏️ Review Draft" if key in ["urgent", "needs-reply"] else "👀 View History"
                        if st.button(btn_label, key=f"sel_{t_id}", use_container_width=True):
                            st.session_state["selected_thread_id"] = t_id
                            st.rerun()
                st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1px solid rgba(255, 255, 255, 0.08);'>", unsafe_allow_html=True)

    # ==================== COLUMN 2: EDITABLE AI DRAFTS ====================
    with col_editor:
        header_html = """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6; display: inline-block; vertical-align: middle;"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
            <span style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; display: inline-block; vertical-align: middle;">Review & Edit Draft</span>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
        
        if not selected_thread:
            # Check if balloons should trigger if all are reviewed
            reviewed_ids = set(approved.keys()) | rejected | sent
            actionable_ids = {t.get("id") for t in actionable_threads if t.get("id") in drafts}
            if actionable_ids and actionable_ids.issubset(reviewed_ids):
                if "balloons_triggered" not in st.session_state:
                    st.session_state["balloons_triggered"] = False
                if not st.session_state["balloons_triggered"]:
                    st.balloons()
                    st.session_state["balloons_triggered"] = True
                st.success("🎉 All generated drafts have been reviewed and approved!")
                
                if st.button("👉 Go to Export Proof", use_container_width=True, type="primary"):
                    st.session_state["current_phase"] = "Export Proof"
                    st.rerun()
            else:
                st.info("No active thread selected. Select an email from the feed on the left to review or edit its reply.")
        else:
            subject = selected_thread.get("subject", "No Subject")
            sender = selected_thread.get("sender", "Unknown")
            draft_text = drafts.get(selected_thread_id, "")
            
            is_sent = selected_thread_id in sent
            is_approved = selected_thread_id in approved and not is_sent
            is_rejected = selected_thread_id in rejected and not is_sent
            is_pending = not is_sent and not is_approved and not is_rejected
            
            metadata_html = f"""
            <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px; margin-bottom: 16px;">
                <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 700; font-family: 'Fira Sans', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; line-height: 1.1;">Sender</div>
                <div style="font-size: 0.85rem; color: #FFFFFF; font-weight: 700; font-family: 'Fira Sans', sans-serif; margin-top: 2px; margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{sender}</div>
                <div style="font-size: 0.72rem; color: #94A3B8; font-weight: 700; font-family: 'Fira Sans', sans-serif; text-transform: uppercase; letter-spacing: 0.05em; line-height: 1.1;">Subject</div>
                <div style="font-size: 0.85rem; color: #FFFFFF; font-weight: 700; font-family: 'Fira Sans', sans-serif; margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{subject}</div>
            </div>
            """
            st.markdown(clean_html(metadata_html), unsafe_allow_html=True)
            
            # Message History details
            with st.expander("Show Original Message History", expanded=False):
                for msg in selected_thread.get("messages", []):
                    st.markdown(f"**From:** {msg.get('from')} | **Date:** {msg.get('date')}")
                    body_content = msg.get('body', '')
                    st.markdown(clean_html(f"<div style='background-color: rgba(15, 23, 42, 0.4); border: 1px solid rgba(255, 255, 255, 0.06); padding: 12px; border-radius: 8px; font-family: \"Fira Code\", monospace; font-size: 0.8rem; line-height: 1.4; white-space: pre-wrap; color: #E2E8F0; margin-bottom: 8px;'>{body_content}</div>"), unsafe_allow_html=True)
                    st.markdown("---")
                    
            if is_sent:
                st.success("✉️ Sent Response:")
                sent_text = approved.get(selected_thread_id, draft_text)
                st.markdown(clean_html(f"<div style='background-color: rgba(11, 17, 33, 0.95); border: 1px solid rgba(16, 185, 129, 0.25); padding: 16px; border-radius: 10px; font-family: \"Fira Code\", monospace; font-size: 0.85rem; line-height: 1.5; white-space: pre-wrap; color: #FFFFFF; margin-bottom: 12px;'>{sent_text}</div>"), unsafe_allow_html=True)
                if st.button("🔄 Reset Status", key=f"reset_{selected_thread_id}", use_container_width=True):
                    if selected_thread_id in sent:
                        sent.remove(selected_thread_id)
                    if selected_thread_id in approved:
                        del approved[selected_thread_id]
                    st.rerun()
            elif is_approved:
                st.success("✅ Approved Draft Reply (Ready to Send):")
                app_text = approved[selected_thread_id]
                st.markdown(clean_html(f"<div style='background-color: rgba(11, 17, 33, 0.95); border: 1px solid rgba(16, 185, 129, 0.25); padding: 16px; border-radius: 10px; font-family: \"Fira Code\", monospace; font-size: 0.85rem; line-height: 1.5; white-space: pre-wrap; color: #FFFFFF; margin-bottom: 12px;'>{app_text}</div>"), unsafe_allow_html=True)
                
                # Send Email
                if st.button("✉️ Send Reply", key=f"send_{selected_thread_id}", use_container_width=True, type="primary"):
                    messages = selected_thread.get("messages", [])
                    last_msg = messages[-1] if messages else {}
                    from_field = last_msg.get("from", sender)
                    
                    import re
                    email_match = re.search(r'<([^>]+)>', from_field)
                    recipient = email_match.group(1).strip() if email_match else from_field.strip()
                    
                    send_reply = _get_send_reply()
                    with st.spinner("Sending email..."):
                        try:
                            last_msg_id = last_msg.get("message_id")
                            result = send_reply(
                                thread_id=selected_thread_id,
                                to=recipient,
                                subject=subject,
                                body=app_text,
                                message_id=last_msg_id
                            )
                            if result and "message_id" in result and "id" not in result:
                                result["id"] = result["message_id"]
                            if result and result.get("id"):
                                log_action(
                                    action_type="sent",
                                    thread_subject=selected_thread["subject"],
                                    detail=recipient,
                                    action_id=result["id"],
                                )
                            st.session_state["sent"].add(selected_thread_id)
                            st.success("Email sent successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error sending email: {e}")
                if st.button("🔄 Reset Status", key=f"reset_{selected_thread_id}", use_container_width=True):
                    if selected_thread_id in approved:
                        del approved[selected_thread_id]
                    st.rerun()
            elif is_rejected:
                st.info("❌ This draft was rejected.")
                if st.button("🔄 Reset Status", key=f"reset_{selected_thread_id}", use_container_width=True):
                    if selected_thread_id in rejected:
                        rejected.remove(selected_thread_id)
                    st.rerun()
            else:
                st.markdown("**Edit draft content:**")
                version = st.session_state.get(f"version_{selected_thread_id}", 0)
                edited_val = st.text_area(
                    "Edit draft before approving:", 
                    value=draft_text, 
                    key=f"edit_{selected_thread_id}_v{version}", 
                    height=240,
                    label_visibility="collapsed"
                )
                
                def handle_tweak_callback():
                    t_key = f"tweak_inp_{selected_thread_id}"
                    val = st.session_state.get(t_key, "").strip()
                    if val:
                        from draft_machine import draft_reply
                        try:
                            current_ver = st.session_state.get(f"version_{selected_thread_id}", 0)
                            current_draft_val = st.session_state.get(f"edit_{selected_thread_id}_v{current_ver}", draft_text)
                            new_draft = draft_reply(selected_thread, instruction=val, existing_draft=current_draft_val)
                            st.session_state["drafts"][selected_thread_id] = new_draft
                            st.session_state[f"version_{selected_thread_id}"] = current_ver + 1
                            st.session_state["tweak_success_flag"] = True
                        except Exception as e:
                            st.session_state["tweak_error_msg"] = str(e)
                        # Clean input box safely
                        st.session_state[t_key] = ""

                tweak_key = f"tweak_inp_{selected_thread_id}"
                
                # Show success/error notifications from callback
                if st.session_state.get("tweak_success_flag"):
                    st.success("Draft updated!")
                    del st.session_state["tweak_success_flag"]
                if "tweak_error_msg" in st.session_state:
                    st.error(f"Error tweaking draft: {st.session_state['tweak_error_msg']}")
                    del st.session_state["tweak_error_msg"]

                st.text_input(
                    "Instruct AI to tweak this draft...",
                    placeholder="e.g. make it more concise, or add a request to meet next week",
                    key=tweak_key,
                    on_change=handle_tweak_callback
                )
                
                st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
                btn_col1, btn_col2, btn_col3 = st.columns([1.1, 1.25, 0.9])
                with btn_col1:
                    if st.button("✅ Approve", key=f"approve_{selected_thread_id}", use_container_width=True, type="primary"):
                        current_ver = st.session_state.get(f"version_{selected_thread_id}", 0)
                        st.session_state["approved"][selected_thread_id] = st.session_state.get(f"edit_{selected_thread_id}_v{current_ver}", draft_text)
                        st.success("Draft approved!")
                        st.rerun()
                with btn_col2:
                    if st.button("🔄 Regenerate", key=f"regen_{selected_thread_id}", use_container_width=True):
                        from draft_machine import draft_reply
                        with st.spinner("Regenerating draft..."):
                            try:
                                new_draft = draft_reply(selected_thread)
                                st.session_state["drafts"][selected_thread_id] = new_draft
                                st.session_state[f"version_{selected_thread_id}"] = st.session_state.get(f"version_{selected_thread_id}", 0) + 1
                                st.success("Draft regenerated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error regenerating draft: {e}")
                with btn_col3:
                    if st.button("❌ Reject", key=f"reject_{selected_thread_id}", use_container_width=True):
                        st.session_state["rejected"].add(selected_thread_id)
                        st.warning("Draft rejected.")
                        st.rerun()

    # ==================== COLUMN 3: CONTEXT & BOOKING ====================
    with col_widgets:
        header_html = """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #06B6D4; display: inline-block; vertical-align: middle;"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
            <span style="font-size: 1.1rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; display: inline-block; vertical-align: middle;">Context & Booking</span>
        </div>
        """
        st.markdown(clean_html(header_html), unsafe_allow_html=True)
        
        # Upcoming meetings & Booking details
        if selected_thread:
            is_meeting = selected_thread.get("_category") == "meeting-request" or selected_thread.get("category") == "meeting-request"
            if is_meeting:
                meeting_banner = """
                <div style="background: rgba(6, 182, 212, 0.15); border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 8px; padding: 10px 12px; margin-bottom: 14px; font-family: 'Fira Sans', sans-serif; font-size: 0.8rem; color: #06B6D4; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                    Meeting request details detected!
                </div>
                """
                st.markdown(clean_html(meeting_banner), unsafe_allow_html=True)
                
                # Load calendar engine
                calendar_engine = _get_calendar_engine()
                
                # Parse details from draft reply
                with st.spinner("Extracting meeting details from email..."):
                    try:
                        current_ver = st.session_state.get(f"version_{selected_thread_id}", 0)
                        active_reply = st.session_state.get(f"edit_{selected_thread_id}_v{current_ver}", draft_text)
                        details = calendar_engine.parse_meeting_request(selected_thread, draft_reply=active_reply)
                    except Exception as e:
                        details = {"topic": "Meeting Topic Finder", "duration_minutes": 30, "proposed_times": [], "attendees": []}
                        
                st.markdown(f"**Topic:** `{details.get('topic', 'Meeting')}`")
                st.markdown(f"**Duration:** `{details.get('duration_minutes', 30)} minutes`")
                st.markdown(f"**Proposed Times:** {details.get('proposed_times', [])}")
                
                if "booked" not in st.session_state:
                    st.session_state["booked"] = {}
                is_booked = selected_thread_id in st.session_state["booked"]
                
                if is_booked:
                    st.info(f"✅ Meeting booked! ID: `{st.session_state['booked'][selected_thread_id]}`")
                else:
                    if st.button("📅 Book Meeting", key=f"book_{selected_thread_id}", use_container_width=True, type="primary"):
                        with st.spinner("Checking availability for proposed times..."):
                            proposed_times = details.get("proposed_times", [])
                            duration = details.get("duration_minutes", 30)
                            
                            if source_option == "Sample":
                                free_slot = None
                                import datetime
                                for start_time_str in proposed_times:
                                    try:
                                        cleaned_start = start_time_str.strip()
                                        iso_start = cleaned_start.replace("Z", "+00:00")
                                        start_dt = datetime.datetime.fromisoformat(iso_start)
                                        end_dt = start_dt + datetime.timedelta(minutes=duration)
                                        
                                        conflict = False
                                        for event in st.session_state.get("mock_events", []):
                                            e_start_str = event.get("start", "").strip().replace("Z", "+00:00")
                                            e_end_str = event.get("end", "").strip().replace("Z", "+00:00")
                                            if not e_start_str or not e_end_str:
                                                continue
                                            e_start = datetime.datetime.fromisoformat(e_start_str)
                                            e_end = datetime.datetime.fromisoformat(e_end_str)
                                            
                                            if start_dt < e_end and end_dt > e_start:
                                                conflict = True
                                                break
                                        if not conflict:
                                            free_slot = start_time_str
                                            break
                                    except Exception:
                                        continue
                            else:
                                try:
                                    free_slot = calendar_engine.find_free_slot(proposed_times, duration)
                                except Exception as availability_err:
                                    st.error(f"Could not check calendar availability: {availability_err}. Please verify your Google Account authentication in App Settings.")
                                    free_slot = None
                                
                        if not free_slot:
                            st.error("No free slots found among the proposed times.")
                        else:
                            with st.spinner("Booking meeting..."):
                                try:
                                    if source_option == "Sample":
                                        import datetime
                                        cleaned_start = free_slot.strip()
                                        iso_start = cleaned_start.replace("Z", "+00:00")
                                        start_dt = datetime.datetime.fromisoformat(iso_start)
                                        end_dt = start_dt + datetime.timedelta(minutes=duration)
                                        event = {
                                            "id": f"mock_event_auto_{datetime.datetime.now().timestamp()}",
                                            "summary": details.get("topic", "Meeting"),
                                            "description": "Auto-booked meeting from email",
                                            "location": "Google Meet",
                                            "start": start_dt.isoformat(),
                                            "end": end_dt.isoformat(),
                                            "attendees": details.get("attendees", []),
                                            "htmlLink": "https://calendar.google.com/calendar/r/eventedit"
                                        }
                                        st.session_state["mock_events"].append({
                                            "id": event["id"],
                                            "summary": event["summary"],
                                            "description": event["description"],
                                            "location": event["location"],
                                            "start": event["start"],
                                            "end": event["end"],
                                            "attendees": event["attendees"]
                                        })
                                    else:
                                        event = calendar_engine.create_event(
                                            summary=details.get("topic", "Meeting"),
                                            start_time=free_slot,
                                            duration_minutes=duration,
                                            attendees=details.get("attendees", []),
                                            description=f"Auto-booked from email thread: {selected_thread.get('subject')}"
                                        )
                                    
                                    if event and event.get("id"):
                                        log_action(
                                            action_type="booked",
                                            thread_subject=selected_thread["subject"],
                                            detail=details.get("topic", selected_thread["subject"]),
                                            action_id=event["id"]
                                        )
                                        st.session_state["booked"][selected_thread_id] = event["id"]
                                        link = event.get("htmlLink", "#")
                                        st.success(f"Meeting booked successfully! [View Event]({link})")
                                        import time
                                        time.sleep(2)
                                        st.rerun()
                                except Exception as ex:
                                    st.error(f"Failed to book: {ex}")
            else:
                st.info("ℹ️ No meeting request details detected for this email thread.")
        else:
            st.info("Select an active thread to view meeting details.")
            
        # Agenda list
        st.markdown("---")
        agenda_header = """
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #94A3B8; display: inline-block; vertical-align: middle;"><path d="M8 6h13"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M3 6h.01"/><path d="M3 12h.01"/><path d="M3 18h.01"/></svg>
            <span style="font-size: 0.95rem; font-weight: 700; color: #FFFFFF; font-family: 'Sora', sans-serif; display: inline-block; vertical-align: middle;">Today's Agenda</span>
        </div>
        """
        st.markdown(clean_html(agenda_header), unsafe_allow_html=True)
        
        agenda_events = []
        source_mode = st.session_state.get("source", "Sample")
        if source_mode == "Gmail" and os.path.exists("token.json"):
            try:
                from engine import fetch_calendar_events
                agenda_events = fetch_calendar_events(max_results=5)
            except Exception:
                agenda_events = st.session_state.get("mock_events", [])
        else:
            agenda_events = st.session_state.get("mock_events", [])

        if not agenda_events:
            st.caption("No events scheduled for today.")
        else:
            for event in agenda_events[:4]:
                e_title = event.get("summary", "Meeting")
                e_start_str = event.get("start", "")
                if isinstance(e_start_str, dict):
                    e_start_str = e_start_str.get("dateTime", e_start_str.get("date", ""))
                try:
                    import datetime as dt
                    e_start = dt.datetime.fromisoformat(e_start_str.replace("Z", "+00:00"))
                    local_start = e_start.astimezone()
                    formatted_time = local_start.strftime("%I:%M %p")
                except Exception:
                    formatted_time = e_start_str
                
                chip_html = f"""
                <div style="background: rgba(11, 17, 33, 0.95); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 4px solid #8B5CF6; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px;">
                    <div style="font-size: 0.78rem; font-weight: 700; color: #FFFFFF; font-family: 'Fira Sans', sans-serif;">{e_title}</div>
                    <div style="font-size: 0.68rem; color: #94A3B8; font-family: 'Fira Code', monospace; margin-top: 2px;">{formatted_time}</div>
                </div>
                """
                st.markdown(clean_html(chip_html), unsafe_allow_html=True)





# 5. Sidebar Layout & Phase Navigation
st.sidebar.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 14px 0 10px 0;'>", unsafe_allow_html=True)

# Main menu selection — styled header
st.sidebar.markdown("<p style='font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;'>MENU</p>", unsafe_allow_html=True)
menu_mode = st.sidebar.radio(
    "Choose Section:",
    ["🚀 Chief of Staff Flow", "⚙️ App Settings"],
    index=1 if st.session_state.get("current_phase") == "⚙️ Settings" else 0,
    key="menu_mode",
    label_visibility="collapsed",
    format_func=lambda x: {
        "🚀 Chief of Staff Flow": "🥞 Chief of Staff Flow",
        "⚙️ App Settings": "⚙️ App Settings"
    }.get(x, x)
)

if menu_mode == "⚙️ App Settings":
    current_phase = "⚙️ Settings"
    st.session_state["current_phase"] = "⚙️ Settings"
else:
    # If returning from settings, default to Inbox & Triage
    if st.session_state.get("current_phase") == "⚙️ Settings":
        st.session_state["current_phase"] = "Inbox & Triage"
        
    # Main workflow phases — styled header
    st.sidebar.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 10px 0;'>", unsafe_allow_html=True)
    st.sidebar.markdown("<p style='font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;'>WORKFLOW</p>", unsafe_allow_html=True)
    phases = ["Inbox & Triage", "Draft Generation", "Approval Gate", "Export Proof"]
    try:
        default_idx = phases.index(st.session_state.get("current_phase", "Inbox & Triage"))
    except ValueError:
        default_idx = 0

    current_phase = st.sidebar.radio(
        "Navigation",
        phases,
        index=default_idx,
        label_visibility="collapsed",
        format_func=lambda x: {
            "Inbox & Triage": "📬 Inbox & Triage",
            "Draft Generation": "✍️ Draft Generation",
            "Approval Gate": "🤝 Approval Gate",
            "Export Proof": "📤 Export Proof"
        }.get(x, x)
    )
    st.session_state["current_phase"] = current_phase

# Source selector — styled header
st.sidebar.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 10px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 0.7rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;'>DATA SOURCE</p>", unsafe_allow_html=True)
source_option = st.sidebar.radio(
    "Select Email Source:",
    ("Sample", "Gmail"),
    index=0,
    key="source",
    label_visibility="collapsed",
    format_func=lambda x: {
        "Sample": "📄 Sample",
        "Gmail": "✉️ Gmail"
    }.get(x, x)
)



# Sidebar footer
st.sidebar.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.08); margin: 14px 0 8px 0;'>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='font-size: 0.7rem; color: #94A3B8; text-align: center; margin: 0;'>v1.0 · Chief of Staff</p>", unsafe_allow_html=True)

# Route main area to pipeline execution UI if running
if st.session_state.get("pipeline_running", False):
    _render_pipeline_execution(source_option)
    st.stop()

if current_phase == "Inbox & Triage":
    render_unified_dashboard()

elif current_phase == "Draft Generation":
    render_unified_dashboard()

elif current_phase == "Approval Gate":
    render_unified_dashboard()

elif current_phase == "Export Proof":
    _render_top_navbar("Export Proof", show_actions=True)
    st.markdown("<h2 style='font-family: Sora, sans-serif; font-weight: 800; letter-spacing: -0.04em; margin-bottom: 4px; color: #FFFFFF;'>Export Proof</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8; font-size: 1rem; margin-bottom: 24px; font-family: \"Fira Sans\", sans-serif;'>Review approved drafts, configure parameters, and download the finalized triage records.</p>", unsafe_allow_html=True)
    
    triaged = st.session_state["triaged"]
    actionable_threads = triaged.get("urgent", []) + triaged.get("needs-reply", [])
    approved = st.session_state["approved"]
    
    if not approved:
        st.info("No approved drafts found. Please review and approve drafts in the Approval Gate phase.")
        if st.button("👉 Go to Approval Gate", use_container_width=True):
            st.session_state["current_phase"] = "Approval Gate"
            st.rerun()
    else:
        # Bento Layout: Preview on Left, Config & Downloads on Right
        col_preview, col_sidebar = st.columns([1.6, 1])
        
        with col_preview:
            preview_header_html = """
            <div style='background-color: rgba(11, 17, 33, 0.95); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); margin-bottom: 20px;'>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6; display: inline-block; vertical-align: middle;"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Preview of Approved Drafts</span>
                </div>
                <p style='color: #94A3B8; font-size: 0.76rem; margin: 0; font-family: "Fira Sans", sans-serif;'>These drafts are approved and finalized.</p>
            </div>
            """
            st.markdown(clean_html(preview_header_html), unsafe_allow_html=True)
            
            approved_threads = [t for t in actionable_threads if t.get("id") in approved]
            for t in approved_threads:
                t_id = t.get("id")
                subject = t.get("subject", "No Subject")
                sender = t.get("sender", "Unknown")
                approved_draft = approved[t_id]
                
                st.markdown(f"**Subject:** `{subject}`")
                sub_col_left, sub_col_right = st.columns(2)
                
                with sub_col_left:
                    st.markdown("<p style='font-size: 0.75rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; font-family: \"Fira Sans\", sans-serif;'>Thread History</p>", unsafe_allow_html=True)
                    for msg in t.get("messages", []):
                        st.markdown(f"**From:** {msg.get('from')}")
                        body_text = msg.get('body', '')
                        st.markdown(clean_html(f"<div style='background-color: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.06); padding: 12px; border-radius: 8px; font-family: \"Fira Code\", monospace; font-size: 0.8rem; line-height: 1.4; white-space: pre-wrap; color: #E2E8F0; margin-bottom: 8px;'>{body_text}</div>"), unsafe_allow_html=True)
                        st.markdown("---")
                    
                with sub_col_right:
                    st.markdown("<p style='font-size: 0.75rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; font-family: \"Fira Sans\", sans-serif;'>Approved Draft Reply</p>", unsafe_allow_html=True)
                    st.markdown(clean_html(f"<div style='background-color: rgba(11, 17, 33, 0.95); border: 1px solid rgba(255, 255, 255, 0.08); padding: 12px; border-radius: 8px; font-family: \"Fira Code\", monospace; font-size: 0.8rem; line-height: 1.4; white-space: pre-wrap; color: #FFFFFF;'>{approved_draft}</div>"), unsafe_allow_html=True)
                
                st.markdown("<hr style='margin: 16px 0; border: none; border-top: 1px solid rgba(255, 255, 255, 0.08);'>", unsafe_allow_html=True)
                
        with col_sidebar:
            # Session Metrics Card
            metrics_sidebar_html = f"""
            <div style='background-color: rgba(11, 17, 33, 0.95); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); margin-bottom: 20px;'>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6; display: inline-block; vertical-align: middle;"><circle cx="12" cy="12" r="10"/><path d="m12 8-4 4h8z"/><path d="m12 16-4-4h8z"/></svg>
                    <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Session Metrics</span>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    <div style="background: rgba(15, 23, 42, 0.8); padding: 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.08); text-align: center;">
                        <div style="font-size: 0.65rem; text-transform: uppercase; font-weight: 700; color: #94A3B8; font-family: 'Fira Sans', sans-serif;">Processed</div>
                        <div style="font-size: 1.3rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; margin-top: 2px;">{len(st.session_state.get("threads", []))}</div>
                    </div>
                    <div style="background: rgba(15, 23, 42, 0.8); padding: 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.08); text-align: center;">
                        <div style="font-size: 0.65rem; text-transform: uppercase; font-weight: 700; color: #94A3B8; font-family: 'Fira Sans', sans-serif;">Approved</div>
                        <div style="font-size: 1.3rem; font-weight: 800; color: #FFFFFF; font-family: 'Sora', sans-serif; margin-top: 2px;">{len(approved)}</div>
                    </div>
                </div>
            </div>
            """
            st.markdown(clean_html(metrics_sidebar_html), unsafe_allow_html=True)
            
            # Export Configurations Card
            config_sidebar_html = """
            <div style='background-color: rgba(11, 17, 33, 0.95); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); margin-bottom: 12px;'>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6; display: inline-block; vertical-align: middle;"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                    <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Export Configuration</span>
                </div>
            </div>
            """
            st.markdown(clean_html(config_sidebar_html), unsafe_allow_html=True)
            
            st.checkbox("Include Metadata Tags", value=True)
            st.checkbox("Append Action Logs", value=True)
            st.checkbox("Anonymize Entities (Preview)", value=False)
            
            # Download actions
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
            proof_md = generate_proof_markdown(approved, actionable_threads)
            proof_html = generate_proof_html(approved, actionable_threads)
            
            st.download_button(
                label="📥 Download Proof (Markdown)",
                data=proof_md,
                file_name="proof.md",
                mime="text/markdown",
                use_container_width=True
            )
            st.download_button(
                label="📥 Download Proof (HTML)",
                data=proof_html,
                file_name="proof.html",
                mime="text/html",
                use_container_width=True,
                type="primary"
            )
            
        # Full width Action Log Card at bottom
        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
        log_entries = get_action_log()
        if log_entries:
            if st.button("🧹 Clear Action Log", key="clear_log_btn_btn", use_container_width=True):
                from task_logger import clear_log
                clear_log()
                st.success("Action log cleared successfully!")
                st.rerun()
                
        if not log_entries:
            st.info("No actions logged yet.")
        else:
            html_table = """
            <div style='background-color: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; backdrop-filter: blur(24px); box-shadow: 0 8px 32px rgba(0,0,0,0.2); margin-top: 10px;'>
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #94A3B8; display: inline-block; vertical-align: middle;"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
                    <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Action Log</span>
                </div>
                <table style='width: 100%; border-collapse: collapse; text-align: left;'>
                    <thead>
                        <tr style='border-bottom: 1px solid rgba(255, 255, 255, 0.08); font-size: 0.72rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; letter-spacing: 0.08em; font-family: "Fira Sans", sans-serif;'>
                            <th style='padding: 10px 8px;'>Timestamp</th>
                            <th style='padding: 10px 8px;'>Action Type</th>
                            <th style='padding: 10px 8px;'>Target Thread</th>
                            <th style='padding: 10px 8px;'>Detail</th>
                        </tr>
                    </thead>
                    <tbody style='font-size: 0.78rem; color: #FFFFFF; font-family: "Fira Sans", sans-serif;'>
            """
            for entry in log_entries:
                ts_str = entry.get("timestamp", "")
                try:
                    import datetime as dt
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    ts = dt.datetime.fromisoformat(ts_str)
                    local_ts = ts.astimezone()
                    formatted_ts = local_ts.strftime("%b %d, %I:%M %p")
                except Exception:
                    formatted_ts = ts_str
                    
                a_type = entry.get("action_type", "").upper()
                badge_class = "badge-urgent" if a_type in ["SENT", "REJECTED"] else "badge-sent"
                
                html_table += f"""
                        <tr style='border-bottom: 1px solid rgba(255, 255, 255, 0.06);'>
                            <td style='padding: 10px 8px; color: #94A3B8; font-family: "Fira Code", monospace;'>{formatted_ts}</td>
                            <td style='padding: 10px 8px;'><span class='{badge_class}'>{a_type}</span></td>
                            <td style='padding: 10px 8px; font-weight: 600; color: #FFFFFF;'>{entry.get('thread_subject', '')}</td>
                            <td style='padding: 10px 8px; font-family: "Fira Code", monospace; font-size: 0.72rem;'>{entry.get('detail', '')}</td>
                        </tr>
                """
            html_table += """
                    </tbody>
                </table>
            </div>
            """
            st.markdown(clean_html(html_table), unsafe_allow_html=True)
            
        st.markdown("---")
        st.info("💡 **Ghostwriter Badge:** Share with `#MyAIChiefOfStaff` to earn your Ghostwriter badge!")

elif current_phase == "⚙️ Settings":
    _render_top_navbar("Configuration", show_actions=True)
    st.markdown("<h2 style='font-family: Sora, sans-serif; font-weight: 800; letter-spacing: -0.04em; margin-bottom: 4px; color: #FFFFFF;'>App Settings</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8; font-size: 1rem; margin-bottom: 24px; font-family: \"Fira Sans\", sans-serif;'>Configure your AI Chief of Staff profile, communication tone, and API credentials.</p>", unsafe_allow_html=True)
    
    # Load current tone profile
    from context_builder import load_tone_profile
    import json
    import os
    
    try:
        profile = load_tone_profile()
    except Exception as e:
        profile = {
            "name": "Rahul Mehta",
            "role": "Senior Product Manager",
            "tone": "professional but warm",
            "formality": "semi-formal",
            "sign_off": "Best, Rahul",
            "quirks": [
                "Keeps emails under 5 sentences whenever possible",
                "Uses numbered points for any list of action items",
                "Inserts dashes for asides — like this — instead of parentheses",
                "Opens with a quick acknowledgment before diving into substance",
                "Avoids corporate jargon — says 'sync' not 'align on deliverables'",
                "Ends with a clear next step or ask, never leaves things vague"
            ],
            "vocabulary_preferences": {
                "use": ["sync", "flag", "ship", "loop in", "heads-up", "got it"],
                "avoid": ["circle back", "leverage", "synergize", "per my last email", "as per"]
            }
        }

    # Bento Grid upper columns: Identity (Left) vs Persona Match (Right)
    col_settings_left, col_settings_right = st.columns([1.6, 1])
    
    with col_settings_left:
        identity_header_html = """
        <div style='background-color: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); margin-bottom: 20px;'>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6; display: inline-block; vertical-align: middle;"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Executive Identity</span>
            </div>
            <p style='color: #94A3B8; font-size: 0.76rem; margin: 0; font-family: "Fira Sans", sans-serif;'>Configure the signature and identity tags attached to AI drafts.</p>
        </div>
        """
        st.markdown(clean_html(identity_header_html), unsafe_allow_html=True)
        
        # Identity Form fields
        with st.form("edit_profile_form"):
            new_name = st.text_input("Your Name:", value=profile.get("name", ""))
            new_role = st.text_input("Your Role:", value=profile.get("role", ""))
            new_sign_off = st.text_area("Your Email Sign-off / Signature:", value=profile.get("sign_off", ""), height=100)
            new_tone = st.text_input("Communication Tone (e.g. professional but warm):", value=profile.get("tone", ""))
            
            # Formality & Directness sliders
            new_formality_pct = st.slider("Formality Level (%):", min_value=0, max_value=100, value=int(profile.get("formality_percent", 75)))
            new_directness_pct = st.slider("Directness Level (%):", min_value=0, max_value=100, value=int(profile.get("directness_percent", 90)))
            
            submitted = st.form_submit_button("Save Profile Settings", type="primary")
            if submitted:
                profile["name"] = new_name
                profile["role"] = new_role
                profile["sign_off"] = new_sign_off
                profile["tone"] = new_tone
                profile["formality_percent"] = new_formality_pct
                profile["directness_percent"] = new_directness_pct
                
                # Map formality text value for context builder
                if new_formality_pct < 35:
                    profile["formality"] = "casual"
                elif new_formality_pct < 70:
                    profile["formality"] = "semi-formal"
                else:
                    profile["formality"] = "formal"
                
                profile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tone_profile.json")
                try:
                    with open(profile_path, "w", encoding="utf-8") as f:
                        json.dump(profile, f, indent=2, ensure_ascii=False)
                    st.success("Profile saved successfully! Future generated drafts will use your details.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Error saving profile: {ex}")

    with col_settings_right:
        f_pct = profile.get("formality_percent", 75)
        d_pct = profile.get("directness_percent", 90)
        
        persona_header_html = f"""
        <div style='background-color: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); height: 100%;'>
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #8B5CF6; display: inline-block; vertical-align: middle;"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"/><path d="M12 6v12"/><path d="M8 10h8"/></svg>
                <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Persona Match</span>
            </div>
            <p style='color: #94A3B8; font-size: 0.76rem; margin-bottom: 20px; font-family: "Fira Sans", sans-serif;'>The AI currently interprets your communication style weights as:</p>
            
            <div style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 700; color: #FFFFFF; font-family: 'Fira Sans', sans-serif; margin-bottom: 4px;">
                    <span>Formality</span>
                    <span>{f_pct}%</span>
                </div>
                <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;">
                    <div style="width: {f_pct}%; height: 100%; background: linear-gradient(90deg, #7C3AED 0%, #06B6D4 100%); border-radius: 3px;"></div>
                </div>
            </div>
            
            <div>
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; font-weight: 700; color: #FFFFFF; font-family: 'Fira Sans', sans-serif; margin-bottom: 4px;">
                    <span>Directness</span>
                    <span>{d_pct}%</span>
                </div>
                <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.06); border-radius: 3px; overflow: hidden;">
                    <div style="width: {d_pct}%; height: 100%; background: linear-gradient(90deg, #7C3AED 0%, #06B6D4 100%); border-radius: 3px;"></div>
                </div>
            </div>
        </div>
        """
        st.markdown(clean_html(persona_header_html), unsafe_allow_html=True)

    # Bento Grid lower full width block: Google API Authentication
    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
    google_header_html = """
    <div style='background-color: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.2); margin-bottom: 20px;'>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #06B6D4; display: inline-block; vertical-align: middle;"><rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            <span style='font-family: "Sora", sans-serif; font-weight: 800; color: #FFFFFF; font-size: 0.95rem; display: inline-block; vertical-align: middle;'>Google API & Calendar Authentication</span>
        </div>
        <p style='color: #94A3B8; font-size: 0.76rem; margin: 0; font-family: "Fira Sans", sans-serif;'>Authenticate your Google Account to load Gmail and Google Calendar details dynamically.</p>
    </div>
    """
    st.markdown(clean_html(google_header_html), unsafe_allow_html=True)
    
    # Check credentials files
    has_credentials = os.path.exists("credentials.json")
    has_token = os.path.exists("token.json")
    
    col_status_cred, col_status_token = st.columns(2)
    with col_status_cred:
        if has_credentials:
            cred_html = """
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 10px 12px; font-family: 'Fira Sans', sans-serif; font-size: 0.8rem; color: #059669; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                credentials.json is loaded.
            </div>
            """
            st.markdown(clean_html(cred_html), unsafe_allow_html=True)
        else:
            cred_html = """
            <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: 8px; padding: 10px 12px; font-family: 'Fira Sans', sans-serif; font-size: 0.8rem; color: #DC2626; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
                credentials.json is missing.
            </div>
            """
            st.markdown(clean_html(cred_html), unsafe_allow_html=True)
            
    with col_status_token:
        if has_token:
            token_html = """
            <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 10px 12px; font-family: 'Fira Sans', sans-serif; font-size: 0.8rem; color: #059669; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                token.json is loaded.
            </div>
            """
            st.markdown(clean_html(token_html), unsafe_allow_html=True)
        else:
            token_html = """
            <div style="background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.2); border-radius: 8px; padding: 10px 12px; font-family: 'Fira Sans', sans-serif; font-size: 0.8rem; color: #2563EB; font-weight: 600; display: flex; align-items: center; gap: 8px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
                token.json is missing. Authentication required.
            </div>
            """
            st.markdown(clean_html(token_html), unsafe_allow_html=True)
            
    st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
            
    # Auth instructions and credential upload
    auth_col1, auth_col2 = st.columns(2)
    
    with auth_col1:
        st.markdown("**Step 1: Credentials File**")
        st.caption("Upload the credentials JSON file downloaded from your Google Cloud Console Desktop application:")
        uploaded_file = st.file_uploader("Upload your credentials.json file:", type=["json"])
        if uploaded_file is not None:
            try:
                file_bytes = uploaded_file.getvalue()
                uploaded_json = json.loads(file_bytes.decode("utf-8"))
                
                # Check for token file mismatch
                if "access_token" in uploaded_json or "token" in uploaded_json:
                    st.error("⚠️ The file uploaded appears to be a Token file (token.json), NOT client secrets. Please upload the correct credentials.json file downloaded from Google Cloud Console.")
                elif "installed" not in uploaded_json and "web" not in uploaded_json:
                    st.error("⚠️ Invalid credentials.json format. The file must contain either an 'installed' or 'web' application configuration.")
                else:
                    already_saved = False
                    if os.path.exists("credentials.json"):
                        try:
                            with open("credentials.json", "rb") as f:
                                if f.read() == file_bytes:
                                    already_saved = True
                        except Exception:
                            pass
                    if not already_saved:
                        try:
                            with open("credentials.json", "wb") as f:
                                f.write(file_bytes)
                            st.success("credentials.json saved successfully! Refreshing status...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error saving credentials.json: {e}")
            except Exception as e:
                st.error(f"Error parsing uploaded file: {e}")
                
        # Manual entry expander
        with st.expander("Alternative: Enter details manually"):
            man_client_id = st.text_input("OAuth Client ID:")
            man_client_secret = st.text_input("OAuth Client Secret:")
            if st.button("Save Client Secret"):
                if man_client_id and man_client_secret:
                    cred_dict = {
                        "installed": {
                            "client_id": man_client_id,
                            "client_secret": man_client_secret,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                        }
                    }
                    try:
                        with open("credentials.json", "w") as f:
                            json.dump(cred_dict, f, indent=2)
                        st.success("Saved credentials.json from manual entry!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save: {e}")
                else:
                    st.warning("Please fill in both client_id and client_secret.")
                    
    with auth_col2:
        st.markdown("**Step 2: Sign In with Google**")
        st.caption("Authorize the application to sync your live Gmail and Google Calendar details. This launches a browser authentication tab.")
        
        if not has_credentials:
            st.info("Please complete Step 1 (credentials.json) before starting authorization.")
        else:
            if st.button("🔐 Start Google Authorization Flow", type="primary", use_container_width=True):
                import os
                os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
                from google_auth_oauthlib.flow import InstalledAppFlow
                from calendar_engine import SCOPES
                from engine import sync_oauth_tokens
                
                # Delete existing token if exists to force fresh login
                if os.path.exists("token.json"):
                    try:
                        os.remove("token.json")
                    except Exception as e:
                        st.warning(f"Could not remove old token.json: {e}")
                
                with st.spinner("Initializing auth flow... A browser tab will open automatically. Please authorize the app."):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                        creds = flow.run_local_server(port=0)
                        
                        # Save the credentials
                        with open('token.json', 'w') as token:
                            token.write(creds.to_json())
                            
                        # Synchronize tokens with Node.js MCP server
                        sync_oauth_tokens(os.path.dirname(os.path.abspath(__file__)))
                        st.success("Gmail & Calendar successfully authenticated!")
                        st.rerun()
                    except Exception as auth_ex:
                        st.error(f"Authentication flow encountered an error: {auth_ex}")
        
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
        st.markdown("**🔍 Calendar Connection Diagnostics**")
        if st.button("🔍 Run Diagnostics", use_container_width=True):
            st.info("Running diagnostics...")
            try:
                engine = _get_calendar_engine()
                service = engine._build_calendar_service()
                st.success("Successfully built Google Calendar service!")
                
                # Test FreeBusy query
                import datetime
                now = datetime.datetime.utcnow().isoformat() + 'Z'
                later = (datetime.datetime.utcnow() + datetime.timedelta(minutes=30)).isoformat() + 'Z'
                body = {
                    "timeMin": now,
                    "timeMax": later,
                    "items": [{"id": "primary"}]
                }
                res = service.freebusy().query(body=body).execute()
                st.success("✅ Google Calendar connection diagnostics completed successfully! Integration is fully operational.")
            except Exception as diag_e:
                error_str = str(diag_e)
                if "insufficientPermissions" in error_str or "insufficient authentication scopes" in error_str:
                    st.error("❌ **Diagnostics Failed: Insufficient Permissions (Google Error 403)**")
                    st.warning("""
                    Your Google Calendar Integration is NOT working. 
                    
                    **Why this happens:**
                    You authenticated your account, but Google has not granted the app calendar permissions.
                    
                    **How to fix it:**
                    1. Click **🔐 Start Google Authorization Flow** again to sign in.
                    2. In the Google Consent screen in your browser, **make sure to check the box** that says:
                       *\"See, edit, share, and permanently delete all the calendars you can access using Google Calendar\"*. 
                       *(If you leave this box unchecked, Google blocks calendar features).*
                    3. If you do not see this checkbox on the screen, go to your **Google Cloud Console**, navigate to **APIs & Services -> Enabled APIs**, and ensure that the **Google Calendar API** is enabled for your project.
                    """)
                else:
                    st.error(f"❌ **Diagnostics Failed: {diag_e}**")
