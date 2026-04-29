import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv, dotenv_values
from openai import OpenAI


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_mistral_client():
    """Get Grok (xAI) client via OpenAI-compatible API."""
    # Load from .env file directly to avoid system env variable conflicts
    env_config = dotenv_values(env_path)
    api_key = env_config.get("GROK_API_KEY") or os.getenv("GROK_API_KEY")
    if not api_key:
        # Fallback to MISTRAL_API_KEY for backward compatibility during transition
        api_key = env_config.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    
    timeout_ms = int(env_config.get("LLM_TIMEOUT_MS") or os.getenv("LLM_TIMEOUT_MS", "30000"))

    # Ignore broken machine-wide proxy settings so outbound AI calls can talk directly to xAI
    http_client = httpx.Client(trust_env=False, timeout=timeout_ms / 1000)
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.x.ai/v1",
        http_client=http_client,
    )


def chat_complete_with_retry(client, *, model: str = "grok-4.20", messages, attempts: int = 3, base_delay: float = 0.6, **kwargs):
    """Retry wrapper for Grok chat completion calls with exponential backoff."""
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            # Use OpenAI-compatible chat.completions.create() for xAI Grok
            return client.chat.completions.create(model=model, messages=messages, **kwargs)
        except Exception as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            time.sleep(base_delay * attempt)

    raise last_error
