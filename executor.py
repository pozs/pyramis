import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import overload, Awaitable

import httpx


@dataclass
class Result:
    request_method: str
    request_url: str
    request_headers: list[tuple[str, str]]
    request_payload: bytes | None
    response_status: int
    response_headers: list[tuple[str, str]]
    response_payload: bytes | None


class Request:
    def __init__(self, name: str, method: str, url: str, headers: list[tuple[str, str]], payload: bytes | None = None):
        self.name = name
        self.method = method
        self.url = url
        self.headers = headers
        self.payload = payload

    async def run(self, collection: 'Collection', client: httpx.AsyncClient) -> Result:
        response = await client.request(
            method=collection.resolve(self.method),
            url=collection.resolve(self.url),
            headers=[(collection.resolve(k), collection.resolve(v)) for k, v in self.headers],
            data=collection.resolve(self.payload),
        )

        return Result(
            request_method=response.request.method,
            request_url=str(response.request.url),
            request_headers=response.request.headers.multi_items(),
            request_payload=response.request.content,
            response_status=response.status_code,
            response_headers=response.headers.multi_items(),
            response_payload=response.content
        )


class Collection:
    def __init__(self, variables: dict[str, str], requests: list[Request]):
        self.variables = variables
        self.requests = requests

    @overload
    def resolve(self, value: None) -> None:
        ...

    @overload
    def resolve(self, value: str) -> str:
        ...

    @overload
    def resolve(self, value: bytes) -> bytes:
        ...

    def resolve(self, value: bytes | str | None) -> bytes | str | None:
        if value is None:
            return None

        if isinstance(value, bytes):
            def repl(match: re.Match[bytes]) -> bytes:
                key = match.group(1).decode('utf-8')
                if key in self.variables:
                    return self.variables[key].encode('utf-8')
                return match.group(0)

            return re.sub(b"\\{\\{(.*?)}}", repl, value, re.MULTILINE)

        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            if key in self.variables:
                return self.variables[key]
            return match.group(0)

        return re.sub("\\{\\{(.*?)}}", repl, value, re.MULTILINE)

    async def run(self, consumer: Callable[[Request, Result], Awaitable]) -> None:
        async with httpx.AsyncClient() as client:
            for request in self.requests:
                await consumer(request, await request.run(self, client))

    async def run_single(self, request: Request) -> Result:
        async with httpx.AsyncClient() as client:
            return await request.run(self, client)
