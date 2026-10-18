"""Exclusive content-addressed writes; references never contain client filesystem paths."""

import re
from pathlib import Path

from app.evidence.canonical import sha256


class IntegrityMismatch(Exception):
    """Retained evidence differs from its registered hash or canonical representation."""


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, digest: str) -> Path:
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("Invalid SHA-256 identifier")
        return self.root / digest[:2] / digest

    def put(self, data: bytes) -> str:
        digest = sha256(data)
        path = self._path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as output:
                output.write(data)
                output.flush()
        except FileExistsError:
            self.read(digest)
        return digest

    def read(self, digest: str) -> bytes:
        try:
            data = self._path(digest).read_bytes()
        except FileNotFoundError as exc:
            raise IntegrityMismatch("Registered evidence is missing") from exc
        if sha256(data) != digest:
            raise IntegrityMismatch("Retained bytes do not match registered hash")
        return data
