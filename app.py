"""
Skylark Drones - Operations Coordinator AI Agent
Streamlit conversational UI.
"""
import os
import streamlit as st

# Make Streamlit Cloud Secrets visible to config (before importing config).
# Locally, skip if secrets aren't set up—use .env instead.
try:
    if hasattr(st, "secrets") and st.secrets:
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass

import config
from agent import handle_message

st.set_page_config(
    page_title="Skylark Ops Coordinator",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a more attractive UI
st.markdown("""
<style>
    /* Main container - subtle gradient background */
    .stApp {
        background: linear-gradient(160deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    }
    
    /* Hero header */
    .hero {
        background: linear-gradient(135deg, #0ea5e9 0%, #06b6d4 50%, #0891b2 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(6, 182, 212, 0.25);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .hero h1 {
        color: white !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        margin-bottom: 0.25rem !important;
    }
    .hero p {
        color: rgba(255,255,255,0.9) !important;
        font-size: 0.95rem !important;
        margin: 0 !important;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: 1px solid rgba(14, 165, 233, 0.2);
    }
    [data-testid="stSidebar"] .stMarkdown h2 {
        color: #38bdf8 !important;
        font-size: 1.1rem !important;
    }
    
    /* Quick action buttons - pill style */
    .quick-btn {
        width: 100%;
        padding: 0.6rem 1rem;
        margin: 0.35rem 0;
        border-radius: 12px;
        border: 1px solid rgba(14, 165, 233, 0.4);
        background: rgba(14, 165, 233, 0.15);
        color: #38bdf8;
        font-weight: 500;
        transition: all 0.2s;
    }
    .quick-btn:hover {
        background: rgba(14, 165, 233, 0.3);
        border-color: #0ea5e9;
        color: white;
    }
    
    /* Chat message containers */
    [data-testid="stChatMessage"] {
        padding: 1rem 1.25rem;
        border-radius: 16px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.15);
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: linear-gradient(135deg, #1e3a5f 0%, #1e293b 100%);
        border: 1px solid rgba(14, 165, 233, 0.25);
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: linear-gradient(135deg, #134e4a 0%, #1e293b 100%);
        border: 1px solid rgba(20, 184, 166, 0.25);
    }
    
    /* Chat input - prominent */
    [data-testid="stChatInput"] {
        border-radius: 16px;
        border: 1px solid rgba(14, 165, 233, 0.3);
        background: rgba(15, 23, 42, 0.8);
    }
    
    /* Status badge in sidebar */
    .sync-badge {
        display: inline-block;
        padding: 0.35rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 0.5rem 0;
    }
    .sync-badge.sheets {
        background: rgba(34, 197, 94, 0.2);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.4);
    }
    .sync-badge.local {
        background: rgba(251, 191, 36, 0.2);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.4);
    }
    
    /* Capability pills */
    .caps {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### 🛸 Skylark Ops")
    st.markdown("---")
    
    if config.use_google_sheets():
        st.markdown('<span class="sync-badge sheets">✓ Google Sheets · 2-way sync</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="sync-badge local">○ Local CSV</span>', unsafe_allow_html=True)
    
    st.markdown("")
    st.markdown("**Quick actions**")
    
    if st.button("👥 Who is available?", use_container_width=True, type="secondary"):
        st.session_state.pending_prompt = "Who is available?"
    if st.button("📋 Current assignments", use_container_width=True, type="secondary"):
        st.session_state.pending_prompt = "Current assignments"
    if st.button("⚠️ Check conflicts", use_container_width=True, type="secondary"):
        st.session_state.pending_prompt = "Any conflicts?"
    if st.button("🚁 Drone fleet", use_container_width=True, type="secondary"):
        st.session_state.pending_prompt = "Show drone fleet"
    if st.button("❓ Help", use_container_width=True, type="secondary"):
        st.session_state.pending_prompt = "Help"
    
    st.markdown("---")
    st.markdown('<p class="caps">Roster · Assignments · Drones · Conflicts · Urgent reassignments</p>', unsafe_allow_html=True)

# Chat state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi, I'm the **Skylark Operations Coordinator**. I can help you with pilot roster, assignments, drone inventory, conflicts, and urgent reassignments. Say **help** for example prompts."}
    ]

# Process pending prompt from sidebar
if st.session_state.get("pending_prompt"):
    prompt = st.session_state.pop("pending_prompt", None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        try:
            reply = handle_message(prompt)
        except Exception as e:
            reply = f"Error: {e}"
        st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

# Hero header
st.markdown("""
<div class="hero">
    <h1>🛸 Drone Operations Coordinator</h1>
    <p>Roster · Assignments · Drone inventory · Conflicts · Urgent reassignments</p>
</div>
""", unsafe_allow_html=True)

# Chat area - limit width for readability on wide layout
col1, col2, col3 = st.columns([1, 3, 1])
with col2:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about pilots, drones, assignments, or conflicts..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            try:
                reply = handle_message(prompt)
                st.markdown(reply)
            except Exception as e:
                st.error(f"Something went wrong: {e}")
                reply = str(e)
        st.session_state.messages.append({"role": "assistant", "content": reply})
