"""Single LLM client for FloatNote.

Every LLM-powered feature (chatbot answers, meeting summaries, keyword
filtering) goes through this one client, so the app depends on exactly one
model: Qwen2.5-7B-Instruct served through the Hugging Face router.
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from ai_modules.utils.app_config import get_hf_token

BACKEND_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(BACKEND_ENV_PATH)

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
LLM_MODEL = os.getenv("HUGGINGFACE_CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
# Optional pinned inference provider (e.g. "together"); "auto" lets the router pick.
_PROVIDER = os.getenv("HUGGINGFACE_PROVIDER", "").strip()


def _model_id() -> str:
    if _PROVIDER and _PROVIDER.lower() != "auto":
        return f"{LLM_MODEL}:{_PROVIDER}"
    return LLM_MODEL


def chat_completion(messages, temperature=0.2, max_tokens=500) -> str:
    """Run one chat completion on the project's single LLM.

    Raises ValueError with an actionable message when the token is missing or
    rejected so callers can fall back locally and surface the real problem.
    """
    token = get_hf_token()
    if not token:
        raise ValueError(
            "No HuggingFace token configured. Set it in the app's settings "
            "screen, or set HUGGINGFACEHUB_API_TOKEN in backend/.env for dev."
        )

    response = requests.post(
        HF_ROUTER_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": _model_id(),
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    if response.status_code == 401:
        raise ValueError(
            "Hugging Face rejected the API token. Create a new token with the "
            "'Make calls to Inference Providers' permission at "
            "https://huggingface.co/settings/tokens and update "
            "HUGGINGFACEHUB_API_TOKEN in backend/.env."
        )
    response.raise_for_status()

    payload = response.json()
    return (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
