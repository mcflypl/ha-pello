"""HTTP client of a Pello controller."""

from __future__ import annotations

import re
from http import HTTPStatus

import aiohttp
from yarl import URL

from .const import REQUEST_TIMEOUT
from .errors import (
    PelloAuthError,
    PelloConnectionError,
    PelloInvalidHostError,
    PelloParseError,
    PelloWriteError,
)
from .models import ControllerInfo, Dictionary, Snapshot
from .parser import parse_dictionary, parse_info, parse_snapshot, parse_write_result

PATH_INFO = "info.cgi"
PATH_DICTIONARY = "config/hardware.xml"
PATH_VALUES = "syncvalues.cgi"
PATH_WRITE = "setregister.cgi"

# The register dictionary, the largest response, is about 320 kB.
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
CHUNK_BYTES = 64 * 1024

_REGISTER_ID = re.compile(r"^[A-Za-z0-9_]+$")
_REGISTER_VALUE = re.compile(r"^-?\d+(\.\d+)?$")


class PelloClient:
    """Reads and changes registers of a Pello controller over its local HTTP API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        username: str,
        password: str,
    ) -> None:
        try:
            self._base = URL.build(scheme="http", host=host)
            authorization = aiohttp.encode_basic_auth(username, password)
        except ValueError as err:
            # The original message would repeat the input, which may hold a password.
            raise PelloInvalidHostError("Invalid host or username") from err
        self._session = session
        self._headers = {"Authorization": authorization}
        self._timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

    @property
    def base_url(self) -> str:
        """URL of the controller's own web panel."""
        return str(self._base)

    async def _read(self, response: aiohttp.ClientResponse) -> str:
        chunks: list[bytes] = []
        size = 0
        async for chunk in response.content.iter_chunked(CHUNK_BYTES):
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                raise PelloParseError("Response of the controller is too large")
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")

    async def _get(self, path: str, query: dict[str, str | int] | None = None) -> str:
        url = self._base / path
        if query is not None:
            url = url.with_query(query)
        try:
            async with self._session.get(
                url, headers=self._headers, timeout=self._timeout, allow_redirects=False
            ) as response:
                if response.status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                    raise PelloAuthError("Controller rejected the credentials")
                if response.status != HTTPStatus.OK:
                    raise PelloConnectionError(f"{path} answered with HTTP {response.status}")
                return await self._read(response)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PelloConnectionError(f"Request to {path} failed: {err}") from err

    async def async_get_info(self) -> ControllerInfo:
        """Read the identity of the controller."""
        return parse_info(await self._get(PATH_INFO))

    async def async_get_dictionary(self) -> Dictionary:
        """Read the register dictionary."""
        return parse_dictionary(await self._get(PATH_DICTIONARY))

    async def async_get_snapshot(self) -> Snapshot:
        """Read the current values of all registers of all device slots."""
        return parse_snapshot(await self._get(PATH_VALUES))

    async def async_set_register(self, vid: int, tid: str, value: str) -> None:
        """Change one register. Raises PelloWriteError when the controller refuses."""
        # Anything else could smuggle a second register into the request.
        if not _REGISTER_ID.match(tid) or not _REGISTER_VALUE.match(value):
            raise PelloWriteError(f"Refusing to write an unexpected value to {tid!r}")
        # The controller expects the device first, then the register.
        response = await self._get(PATH_WRITE, {"device": vid, tid: value})
        parse_write_result(response, tid)
