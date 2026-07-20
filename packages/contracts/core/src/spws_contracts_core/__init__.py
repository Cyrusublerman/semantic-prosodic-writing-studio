"""Semantic–Prosodic Writing Studio core contract reference primitives."""

from .digests import (
    RECORD_PROJECTION_V1,
    DigestRecord,
    canonical_json_bytes,
    digest_bytes,
    digest_json,
    digest_record_projection,
    digest_text,
    verify_digest,
)
from .domain import *
from .envelope import CoreObjectEnvelope, ObjectState, PayloadDescriptor, PayloadKind
from .extensions import ExtensionRecord, check_extensions
from .identifiers import *
from .policy import *
from .provenance import *
from .quality import *
from .references import *
from .release import *
from .schema import *
from .text import *
from .time import *

__version__ = "0.1.0.dev2"
