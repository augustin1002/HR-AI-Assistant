"""
llm/model.py
Thin, provider-agnostic wrapper so the rest of the app doesn't care whether
you're using OpenAI, Anthropic (Claude), a local Ollama model, or (for
offline testing) a canned mock response.

Configure via .env:
    LLM_PROVIDER=openai|anthropic|ollama|mock
    OPENAI_API_KEY=...
    ANTHROPIC_API_KEY=...
    OLLAMA_MODEL=llama3
"""
import os


def _mock_complete(prompt: str) -> str:
    return (
        "[MOCK LLM - no API key configured]\n"
        "Here is the context I would normally reason over:\n\n"
        f"{prompt[-1500:]}\n\n"
        "Set LLM_PROVIDER and the matching API key in .env to get real answers."
    )


def _openai_complete(prompt: str, system: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return resp.choices[0].message.content


def _anthropic_complete(prompt: str, system: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    resp = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1000,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text")


def _ollama_complete(prompt: str, system: str) -> str:
    import requests
    model = os.getenv("OLLAMA_MODEL", "llama3")
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": model, "prompt": f"{system}\n\n{prompt}", "stream": False},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


def complete(prompt: str, system: str) -> str:
    """Route to the configured LLM provider. Falls back to the mock
    responder if the provider call fails for any reason (missing key,
    network error, etc.) so the app never hard-crashes mid-demo."""
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    try:
        if provider == "openai":
            return _openai_complete(prompt, system)
        if provider == "anthropic":
            return _anthropic_complete(prompt, system)
        if provider == "ollama":
            return _ollama_complete(prompt, system)
        return _mock_complete(prompt)
    except Exception as e:
        return (
            f"[LLM call failed: {e}]\n\n"
            "Falling back to mock mode. Check your API key / provider in .env.\n\n"
            + _mock_complete(prompt)
        )
