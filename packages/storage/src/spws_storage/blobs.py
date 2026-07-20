from __future__ import annotations

from pathlib import Path

from spws_contracts_core import DigestRecord, digest_bytes, verify_digest


class BlobStore:
    """Content-addressed blob storage under workspace/objects/."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _object_path(self, digest_value: str) -> Path:
        return self.root / digest_value[:2] / digest_value[2:]

    def put_bytes(self, data: bytes, *, media_type: str | None = None) -> DigestRecord:
        record = digest_bytes(data, media_type=media_type)
        path = self._object_path(record.value)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_bytes(data)
        return record

    def put_text(self, text: str, *, media_type: str = "text/plain") -> tuple[DigestRecord, Path]:
        data = text.encode("utf-8")
        record = self.put_bytes(data, media_type=media_type)
        return record, self._object_path(record.value)

    def get_bytes(self, digest_value: str) -> bytes:
        return self._object_path(digest_value).read_bytes()

    def exists(self, digest_value: str) -> bool:
        return self._object_path(digest_value).exists()

    def verify(self, record: DigestRecord) -> bool:
        data = self.get_bytes(record.value)
        return verify_digest(record, data)
