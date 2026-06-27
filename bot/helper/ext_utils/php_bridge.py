"""
Thin HTTP client for the PHP MadelineProto microservice.

Auto-disables itself if:
  * ``Config.USE_PHP_TRANSPORT`` is False
  * The PHP service is not reachable on first ``health()`` call
  * Three consecutive request failures occur (circuit breaker)

When disabled, callers transparently fall back to Kurigram HyperUP/HyperDL.
"""

import asyncio
import os
from typing import Any

import httpx

from ... import LOGGER

_PHP_URL = os.environ.get("PHP_BRIDGE_URL", "http://127.0.0.1:9090")
_CB_FAILS_BEFORE_OPEN = 3
_CB_COOLDOWN_SECONDS = 60


class _PhpBridge:
    """Singleton that holds the httpx client + circuit-breaker state."""

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._enabled = True
        self._fail_count = 0
        self._open_until: float = 0.0
        self._self_info: dict[str, Any] | None = None
        self._lock = asyncio.Lock()

    @property
    def url(self) -> str:
        return _PHP_URL

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            # Big files = long uploads. No total timeout, but reasonable read/connect timeouts.
            self._client = httpx.AsyncClient(
                base_url=_PHP_URL,
                timeout=httpx.Timeout(connect=5.0, read=None, write=None, pool=5.0),
            )
        return self._client

    def is_circuit_open(self) -> bool:
        if self._open_until == 0.0:
            return False
        return asyncio.get_event_loop().time() < self._open_until

    def _record_failure(self) -> None:
        self._fail_count += 1
        if self._fail_count >= _CB_FAILS_BEFORE_OPEN:
            self._open_until = asyncio.get_event_loop().time() + _CB_COOLDOWN_SECONDS
            LOGGER.warning(
                f"php_bridge: {_CB_FAILS_BEFORE_OPEN} consecutive failures — "
                f"circuit OPEN for {_CB_COOLDOWN_SECONDS}s, falling back to Kurigram"
            )

    def _record_success(self) -> None:
        if self._fail_count or self._open_until:
            LOGGER.info("php_bridge: recovered, circuit CLOSED")
        self._fail_count = 0
        self._open_until = 0.0

    async def health(self) -> dict[str, Any] | None:
        """Return service info dict on success, None on failure."""
        from ..core.config_manager import Config  # local import to avoid cycle
        if not getattr(Config, "USE_PHP_TRANSPORT", False):
            return None
        if self.is_circuit_open():
            return None
        try:
            c = await self._get_client()
            r = await c.get("/health", timeout=3.0)
            r.raise_for_status()
            info = r.json()
            if info.get("ok"):
                self._self_info = info
                self._record_success()
                return info
            return None
        except Exception as e:  # noqa: BLE001
            LOGGER.warning(f"php_bridge: health probe failed: {e}")
            self._record_failure()
            return None

    async def is_available(self) -> bool:
        if self._self_info is not None and not self.is_circuit_open():
            return True
        return (await self.health()) is not None

    async def upload(
        self,
        *,
        file_path: str,
        peer: int | str,
        caption: str = "",
        as_video: bool = False,
        thumb: str | None = None,
    ) -> dict[str, Any] | None:
        """Delegate one upload to PHP. Returns response dict or None on failure."""
        if not await self.is_available():
            return None
        try:
            c = await self._get_client()
            r = await c.post(
                "/upload",
                json={
                    "file_path": file_path,
                    "peer": peer,
                    "caption": caption,
                    "as_video": as_video,
                    "thumb": thumb,
                },
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                LOGGER.error(f"php_bridge: upload error: {data.get('error')}")
                self._record_failure()
                return None
            self._record_success()
            return data
        except Exception as e:  # noqa: BLE001
            LOGGER.error(f"php_bridge: upload exception: {e}")
            self._record_failure()
            return None

    async def download(
        self,
        *,
        peer: int | str,
        message_id: int,
        save_path: str,
    ) -> dict[str, Any] | None:
        if not await self.is_available():
            return None
        try:
            c = await self._get_client()
            r = await c.post(
                "/download",
                json={
                    "peer": peer,
                    "message_id": message_id,
                    "save_path": save_path,
                },
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("ok"):
                LOGGER.error(f"php_bridge: download error: {data.get('error')}")
                self._record_failure()
                return None
            self._record_success()
            return data
        except Exception as e:  # noqa: BLE001
            LOGGER.error(f"php_bridge: download exception: {e}")
            self._record_failure()
            return None

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


php_bridge = _PhpBridge()
