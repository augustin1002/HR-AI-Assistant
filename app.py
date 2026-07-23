import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from database.db import build_database, DB_PATH
from agent.router import answer

st.set_page_config(page_title="HR AI Assistant", page_icon="💼", layout="centered")

display_style = os.getenv("DISPLAY_STYLE", "claude").strip().lower()
if display_style not in {"claude", "chatgpt"}:
    display_style = "claude"


def apply_display_style(style: str) -> None:
    if style == "chatgpt":
        st.markdown(
            """
            <style>
            .stApp {
                background: linear-gradient(180deg, #f7f7f8 0%, #ffffff 100%);
            }
            .block-container {
                padding-top: 1rem;
            }
            .stChatMessage {
                border: 1px solid #e5e7eb;
                border-radius: 16px;
                padding: 0.8rem 1rem;
                margin-bottom: 0.75rem;
                background: white;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }
            [data-testid="stSidebar"] {
                background: #f8fafc;
                border-right: 1px solid #e2e8f0;
            }
            .stTextInput > div > div > input {
                border-radius: 999px;
                padding: 0.8rem 1rem;
                border: 1px solid #d0d7de;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
            .stApp {
                background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
                color: #f9fafb;
            }
            .block-container {
                padding-top: 1rem;
            }
            .stChatMessage {
                border: 1px solid rgba(255,255,255,0.12);
                border-radius: 18px;
                padding: 0.85rem 1rem;
                margin-bottom: 0.75rem;
                background: rgba(17, 24, 39, 0.86);
                box-shadow: 0 8px 24px rgba(0,0,0,0.2);
            }
            [data-testid="stSidebar"] {
                background: rgba(17, 24, 39, 0.95);
                border-right: 1px solid rgba(255,255,255,0.08);
            }
            .stTextInput > div > div > input {
                border-radius: 999px;
                padding: 0.8rem 1rem;
                border: 1px solid rgba(255,255,255,0.16);
                background: rgba(17,24,39,0.7);
                color: #f9fafb;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )


apply_display_style(display_style)

# --- One-time setup: build the SQLite DB if it doesn't exist yet ---
if not DB_PATH.exists():
    with st.spinner("Setting up employee database..."):
        build_database()

st.title("💼 HR AI Assistant")
st.caption(
    "Ask about company policies (leave, benefits, security, conduct, recruitment) "
    "or employee data (salary, department, performance, absences)."
)

with st.sidebar:
    st.subheader("Settings")
    provider = os.getenv("LLM_PROVIDER", "mock")
    st.write(f"**LLM provider:** `{provider}`")
    st.write(f"**Display style:** `{display_style.title()}`")
    if provider == "mock":
        st.warning(
            "Running in MOCK mode - no LLM API key set. Set `LLM_PROVIDER` and the "
            "matching API key in `.env` for real answers. RAG retrieval and SQL "
            "queries still work in mock mode; only the final write-up is canned."
        )
    st.subheader("Example questions")
    st.markdown(
        "- What is the maternity leave policy?\n"
        "- Who has the highest salary?\n"
        "- How many employees are in IT/IS?\n"
        "- Explain the dress code.\n"
        "- What is the password policy?\n"
        "- Show employees with low performance scores.\n"
        "- Who reports to Michael Albert, and what is the probation policy?"
    )
    if st.button("🔄 Rebuild document index"):
        from rag.retriever import get_retriever
        st.cache_resource.clear()
        get_retriever().build_index()
        st.success("Index rebuilt.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("route"):
            st.caption(f"routed via: {msg['route']}")

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
        st.caption(f"routed via: {result['route']}")
        with st.expander("Show retrieved context"):
            if result.get("rag_context"):
                st.markdown("**Policy excerpts:**")
                st.text(result["rag_context"])
            if result.get("sql_context"):
                st.markdown("**Database results:**")
                st.text(result["sql_context"])

    st.session_state.messages.append({
        "role": "assistant", "content": result["answer"], "route": result["route"],
    })
