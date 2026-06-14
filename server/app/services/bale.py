"""Bale messenger API client (Telegram-compatible Bot API)."""

from typing import Any

import httpx

from app.config import settings

# Bypass broken system proxy on Windows
_HTTP_CLIENT_KW = {"timeout": 30, "trust_env": False, "proxy": None}


def chat_id_candidates(chat_id: str) -> list[str]:
    """Bale groups may need @username instead of numeric id."""
    raw = (chat_id or "").strip()
    if not raw:
        return []
    out: list[str] = []
    if raw.startswith("@"):
        out.append(raw)
        if raw[1:].isdigit():
            out.append(raw[1:])
    else:
        if raw.isdigit():
            out.append(f"@{raw}")
        out.append(raw)
    seen = set()
    result = []
    for c in out:
        if c not in seen:
            seen.add(c)
            result.append(c)
    return result


def normalize_chat_id(chat_id: str) -> str:
    candidates = chat_id_candidates(chat_id)
    return candidates[0] if candidates else chat_id.strip()


class BaleClient:
    def __init__(self, token: str | None = None):
        self.token = token or settings.bale_bot_token
        self.base = settings.bale_api_base.rstrip("/")

    def _url(self, method: str) -> str:
        return f"{self.base}{self.token}/{method}"

    async def send_message(self, chat_id: str, text: str) -> dict[str, Any]:
        if not self.token:
            raise ValueError("Bale bot token is not configured")

        last_error: Exception | None = None
        for cid in chat_id_candidates(chat_id):
            try:
                async with httpx.AsyncClient(**_HTTP_CLIENT_KW) as client:
                    resp = await client.post(
                        self._url("sendMessage"),
                        json={"chat_id": cid, "text": text},
                    )
                    data = resp.json()
                    if data.get("ok"):
                        return data
                    last_error = RuntimeError(data.get("description", "Bale API error"))
            except Exception as e:
                last_error = e
        raise last_error or RuntimeError("Failed to send Bale message")

    async def get_updates(self, limit: int = 20) -> list[dict[str, Any]]:
        if not self.token:
            raise ValueError("Bale bot token is not configured")
        async with httpx.AsyncClient(**_HTTP_CLIENT_KW) as client:
            resp = await client.get(self._url("getUpdates"), params={"limit": limit})
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "Bale API error"))
            return data.get("result", [])

    async def get_me(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15, trust_env=False, proxy=None) as client:
            resp = await client.get(self._url("getMe"))
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("description", "Bale API error"))
            return data.get("result", {})
