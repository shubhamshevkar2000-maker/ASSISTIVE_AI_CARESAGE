"""
LLM Sidecar — Local LLM (Ollama) client.
Feature-flagged, PHI-sanitized, never influences clinical decisions.
Completely local and offline to satisfy project restrictions.
"""
import json
import logging
import time
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger("acuvera.llm.client")


def _is_llm_enabled(feature_flags: dict) -> bool:
    return feature_flags.get("LLM_ENABLED", settings.LLM_ENABLED_DEFAULT)


def call_llm(
    system_prompt: str,
    user_content: str,
    feature_flags: dict,
    max_tokens: int = 512,
    retries: int = 2,
) -> Optional[str]:
    """
    Call Local Ollama API with retry + timeout.
    Returns raw text output or None on failure.
    """
    if not _is_llm_enabled(feature_flags):
        logger.debug("LLM disabled — skipping local LLM call")
        return None

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.1,
        },
    }

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                settings.OLLAMA_URL,
                json=payload,
                timeout=settings.LLM_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["message"]["content"]
            logger.info("Local LLM call success attempt=%d", attempt)
            return content
        except requests.Timeout:
            logger.warning("Local LLM timeout attempt %d/%d", attempt, retries)
        except requests.HTTPError as e:
            logger.warning("Local LLM HTTP error %s attempt %d/%d", e, attempt, retries)
        except Exception as e:
            logger.error("Local LLM unexpected error: %s attempt %d/%d", e, attempt, retries)

        if attempt < retries:
            time.sleep(1)

    return None


def call_llm_json(
    system_prompt: str,
    user_content: str,
    feature_flags: dict,
    expected_keys: list = None,
    max_tokens: int = 512,
) -> Optional[dict]:
    """
    Call Local LLM and parse response as JSON.
    """
    raw = call_llm(system_prompt, user_content, feature_flags, max_tokens)
    if raw is None:
        return None

    # Extract JSON block if wrapped in markdown fences
    text = raw.strip()
    if text.startswith("```"):
        # Handle cases like ```json ... ```
        if "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            text = text[start:end]
        else:
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Local LLM returned invalid JSON: %s", text[:200])
        return None

    if expected_keys:
        missing = [k for k in expected_keys if k not in result]
        if missing:
            logger.warning("Local LLM JSON missing expected keys: %s", missing)
            # Try to return it anyway if it's partially valid? 
            # Better to be strict for safety.
            return None

    return result

