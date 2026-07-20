"""Read-only discovery of PKL markdown files in the Library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from ..snapshot.snapshot import SnapshotReader, sha256_hex


@dataclass(frozen=True, slots=True)
class ScannedFile:
    relative_path: str
    content_digest: str
    size_bytes: int


def scan_markdown(reader: SnapshotReader) -> Iterator[ScannedFile]:
    for relative_path in sorted(reader.list_markdown_paths()):
        data = reader.read_bytes(relative_path)
        yield ScannedFile(
            relative_path=relative_path,
            content_digest=sha256_hex(data),
            size_bytes=len(data),
        )
