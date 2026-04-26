import os
from pathlib import Path

import httpx
from dotenv import load_dotenv, dotenv_values
from mistralai import Mistral


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_mistral_client():
    # Load from .env file directly to avoid system env variable conflicts
    env_config = dotenv_values(env_path)
    api_key = env_config.get("MISTRAL_API_KEY") or os.getenv("MISTRAL_API_KEY")
    timeout_ms = int(env_config.get("MISTRAL_TIMEOUT_MS") or os.getenv("MISTRAL_TIMEOUT_MS", "30000"))

    # Ignore broken machine-wide proxy settings so outbound AI calls can talk
    # directly to Mistral unless this app explicitly adds proxy support later.
    http_client = httpx.Client(trust_env=False, timeout=timeout_ms / 1000)
    return Mistral(api_key=api_key, client=http_client, timeout_ms=timeout_ms)
