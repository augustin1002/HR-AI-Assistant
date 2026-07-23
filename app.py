import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from database.db import build_database, DB_PATH
from agent.router import answer

st.set_page_config(page_title="HR AI Assistant", page_icon="💼", layout="centered")

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
