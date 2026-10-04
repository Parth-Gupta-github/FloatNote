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
LLM_MODEL = os.getenv("HUGGINGFACE_CHAT_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
# Optional pinned inference provider (e.g. "together"); "auto" lets the router pick.
_PROVIDER = os.getenv("HUGGINGFACE_PROVIDER", "").strip()


FALLBACK_MODELS = [
    os.getenv("HUGGINGFACE_CHAT_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
    "Qwen/Qwen2.5-Coder-7B-Instruct",
    "google/gemma-3-4b-it",
]


def chat_completion(messages, temperature=0.2, max_tokens=500) -> str:
    """Run one chat completion on Hugging Face Router with automatic model fallback."""
    token = get_hf_token()
    if not token:
        raise ValueError(
            "No HuggingFace token configured. Set it in the app's settings "
            "screen, or set HUGGINGFACEHUB_API_TOKEN in backend/.env for dev."
        )

    # De-duplicate fallback list while preserving order
    models_to_try = []
    for m in FALLBACK_MODELS:
        if m and m not in models_to_try:
            models_to_try.append(m)

    last_error = None
    for model_name in models_to_try:
        model_spec = f"{model_name}:{_PROVIDER}" if (_PROVIDER and _PROVIDER.lower() != "auto") else model_name
        try:
            response = requests.post(
                HF_ROUTER_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_spec,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=60,
            )
            if response.status_code == 401:
                raise ValueError(
                    "Hugging Face rejected the API token. Please make sure your token has "
                    "'Make calls to Inference Providers' permission enabled."
                )
            if response.status_code == 200:
                payload = response.json()
                content = (
                    payload.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if content:
                    return content
            # If 400 (e.g. model not supported on router) or 503, try next candidate
            last_error = f"Model {model_name} returned {response.status_code}: {response.text[:120]}"
        except ValueError:
            raise
        except Exception as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"All LLM candidates failed. Last error: {last_error}")

