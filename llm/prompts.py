SYSTEM_PROMPT = """You are the HR Assistant for ABC Technologies / Adino Telecom.
Answer the employee's question using ONLY the context provided below
(policy excerpts and/or database results). If the context does not contain
the answer, say so honestly rather than guessing. Be concise, clear, and
cite which policy document a fact came from when relevant. Do not invent
numbers, names, or policy terms that are not in the context."""


def build_prompt(question: str, rag_context: str = "", sql_context: str = "",
                  chat_history: str = "") -> str:
    parts = []
    if chat_history:
        parts.append(f"Conversation so far:\n{chat_history}\n")
    if rag_context:
        parts.append(f"Relevant policy excerpts:\n{rag_context}\n")
    if sql_context:
        parts.append(f"Relevant employee data (from database):\n{sql_context}\n")
    parts.append(f"Employee question: {question}\n\nAnswer:")
    return "\n".join(parts)
