"""Bound multipart bytes during receipt, including requests without a length header."""

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class UploadBodyLimit:
    def __init__(self, app: ASGIApp, limit: int) -> None:
        self.app = app
        self.limit = limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        consumed = 0

        async def bounded_receive() -> Message:
            nonlocal consumed
            message = await receive()
            if message["type"] == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.limit:
                    raise HTTPException(413, "Multipart body exceeds the upload limit")
            return message

        upload = scope["type"] == "http" and scope.get("path") == "/api/v1/media"
        await self.app(scope, bounded_receive if upload else receive, send)
