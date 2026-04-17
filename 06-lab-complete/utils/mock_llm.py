"""Mock LLM used when OPENAI_API_KEY is not configured."""

from datetime import datetime


def ask(question: str, history: list[dict] | None = None) -> str:
    history = history or []
    context_hint = ""
    if history:
        context_hint = f" (I can see {len(history)} prior messages in this conversation.)"
    return (
        f"[mock-llm {datetime.utcnow().isoformat()}] "
        f"Answer to: '{question}'.{context_hint}"
    )
