import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from database.db import build_database, DB_PATH
from agent.router import answer

# --- Page Setup ---
st.set_page_config(
    page_title="HR AI Assistant",
    page_icon="💼",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Display Style Configuration ---
display_style = os.getenv("DISPLAY_STYLE", "claude").strip().lower()
if display_style not in {"claude", "chatgpt"}:
    display_style = "claude"

def apply_display_style(style: str) -> None:
    if style == "chatgpt":
        st.markdown(
            """
            <style>
            .stApp {
                background: #f9fafb;
                color: #111827;
            }
            .block-container {
                padding-top: 2rem;
                padding-bottom: 5rem;
                max-width: 800px;
            }
            .stChatMessage {
                border: 1px solid #eaecf0;
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 0.8rem;
                background: #ffffff;
                box-shadow: 0px 1px 3px rgba(16, 24, 40, 0.05);
            }
            [data-testid="stSidebar"] {
                background-color: #ffffff;
                border-right: 1px solid #eaecf0;
            }
            /* Fix input field styling and cursor visibility */
            div[data-baseweb="input"] {
                border-radius: 24px !important;
                background-color: #ffffff !important;
                border: 1px solid #d0d5dd !important;
            }
            div[data-baseweb="input"]:focus-within {
                border-color: #667085 !important;
                box-shadow: 0 0 0 2px rgba(102, 112, 133, 0.2) !important;
            }
            .stChatInput input {
                color: #101828 !important;
                caret-color: #101828 !important; /* Visible cursor */
                font-size: 0.95rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Claude style (Dark Mode)
        st.markdown(
            """
            <style>
            .stApp {
                background: #111827;
                color: #f9fafb;
            }
            .block-container {
                padding-top: 2rem;
                padding-bottom: 5rem;
                max-width: 800px;
            }
            .stChatMessage {
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 0.8rem;
                background: #1f2937;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
            }
            [data-testid="stSidebar"] {
                background-color: #0f172a;
                border-right: 1px solid rgba(255, 255, 255, 0.08);
            }
            /* Fix input field styling and cursor visibility */
            div[data-baseweb="input"] {
                border-radius: 24px !important;
                background-color: #1f2937 !important;
                border: 1px solid #374151 !important;
            }
            div[data-baseweb="input"]:focus-within {
                border-color: #60a5fa !important;
                box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.2) !important;
            }
            .stChatInput input {
                color: #f9fafb !important;
                caret-color: #60a5fa !important; /* Bright visible cursor */
                font-size: 0.95rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

apply_display_style(display_style)

# --- Database Setup ---
if not DB_PATH.exists():
    with st.spinner("Setting up employee database..."):
        build_database()

# --- Header ---
st.title("💼 HR AI Assistant")
st.caption("Ask about company policies or query employee records securely.")

# --- Sidebar ---
with st.sidebar:
    st.subheader("System Status")
    provider = os.getenv("LLM_PROVIDER", "mock")
    st.write(f"**LLM Provider:** `{provider.upper()}`")
    st.write(f"**Theme:** `{display_style.title()}`")
    
    st.divider()
    
    st.subheader("Suggested Queries")
    st.markdown(
        """
        * What is the maternity leave policy?
        * Who has the highest salary?
        * How many employees are in IT/IS?
        * Explain the dress code.
        * What is the password policy?
        """
    )
    
    st.divider()
    
    if st.button("🔄 Rebuild Document Index", use_container_width=True):
        from rag.retriever import get_retriever
        st.cache_resource.clear()
        get_retriever().build_index()
        st.success("Index rebuilt successfully.")

# --- Chat Messages ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("route"):
            st.caption(f"*routed via: {msg['route']}*")

# --- User Input & Logic ---
if prompt := st.chat_input("Ask about HR policy or employee data..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    history = "\n".join(
        f"{m['role']}: {m['content']}" for m in st.session_state.messages[-6:-1]
    )

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = answer(prompt, chat_history=history)
            st.markdown(result["answer"])
            st.caption(f"*routed via: {result['route']}*")

            if result.get("rag_context") or result.get("sql_context"):
                with st.expander("Show retrieved context"):
                    if result.get("rag_context"):
                        st.markdown("**Policy Excerpts:**")
                        st.text(result["rag_context"])
                    if result.get("sql_context"):
                        st.markdown("**Database Results:**")
                        st.text(result["sql_context"])

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result["answer"],
            "route": result["route"],
        }
    )
