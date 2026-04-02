"""OpenRouter client for optional AI-assisted analysis."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Type

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Thin wrapper around OpenRouter chat completions."""

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.model = settings.openrouter_model
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self.app_name = settings.openrouter_app_name
        self.site_url = settings.openrouter_site_url

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        temperature: float = 0.1,
    ) -> Optional[BaseModel]:
        """Request a structured JSON response and validate it."""
        if not self.enabled:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url or "https://cloudaegis.local",
            "X-Title": self.app_name,
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                response.raise_for_status()

            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return response_model.model_validate(parsed)
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning(f"OpenRouter structured completion failed: {exc}")
            return None
