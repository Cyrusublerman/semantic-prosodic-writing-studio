"""Thin facade — all SPWS code should import WordRare through here.

Maps WordRare internals to ``LexicalRecord`` / plain dicts. Never exports
WordRare SQLAlchemy/DB models as studio contracts.
"""

from __future__ import annotations

from typing import Any

from spws_contracts_core.domain import (
    DialectCode,
    LexicalRecord,
    PronunciationStatus,
    PronunciationVariant,
)
from spws_domain.ids import new_id

from .capabilities import (
    ConstrainedSearchCapability,
    FormScaffoldCapability,
    LexicalCapability,
    ProsodicRepairCapability,
    ProsodyCapability,
    is_unsupported,
    unsupported,
)

ADAPTER_VERSION = "0.1.0"


def wordrare_version() -> str:
    try:
        import wordrare

        return str(getattr(wordrare, "__version__", "unknown"))
    except Exception:
        return "unavailable"


def _dialect_code(dialect: str) -> DialectCode:
    raw = (dialect or "en-AU").strip()
    try:
        return DialectCode(raw)
    except ValueError:
        normalised = raw.lower().replace("_", "-")
        for code in DialectCode:
            if code.value.lower() == normalised:
                return code
        return DialectCode.UNKNOWN


def _heuristic_syllables(lemma: str) -> int:
    word = lemma.lower().strip(".,;:!?\"'")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def _fetch_word_fields(lemma: str) -> dict[str, Any] | None:
    """Internal ORM fetch → plain dict (never return detached ORM instances)."""
    try:
        from wordrare.database import WordRecord, get_session

        key = lemma.lower().strip(".,;:!?\"'")
        with get_session() as session:
            row = session.query(WordRecord).filter(WordRecord.lemma == key).first()
            if row is None:
                return None
            return {
                "lemma": row.lemma,
                "ipa_uk": row.ipa_uk,
                "ipa_us": row.ipa_us,
                "rarity_score": row.rarity_score,
                "syllable_count": row.syllable_count,
                "stress_pattern": row.stress_pattern,
                "rhyme_key": row.rhyme_key,
                "definitions": list(row.definitions or []) if row.definitions else None,
                "register_tags": list(row.register_tags or []) if row.register_tags else [],
                "synonyms": list(getattr(row, "synonyms", None) or [])
                if getattr(row, "synonyms", None)
                else [],
            }
    except Exception:
        return None


def _row_to_lexical_record(row: dict[str, Any] | None, lemma: str, *, dialect: str = "en-AU") -> LexicalRecord:
    """Map plain field dict into LexicalRecord; never expose ORM models."""
    dialect_code = _dialect_code(dialect)
    variants: list[PronunciationVariant] = []
    ipa_uk = row.get("ipa_uk") if row is not None else None
    ipa_us = row.get("ipa_us") if row is not None else None
    if ipa_uk:
        variants.append(
            PronunciationVariant(
                dialect=DialectCode.EN_GB if dialect_code is DialectCode.EN_AU else DialectCode.EN_GB,
                ipa=str(ipa_uk),
                status=PronunciationStatus.SOURCED,
                confidence=0.85,
            )
        )
    if ipa_us:
        variants.append(
            PronunciationVariant(
                dialect=DialectCode.EN_US,
                ipa=str(ipa_us),
                status=PronunciationStatus.SOURCED,
                confidence=0.85,
            )
        )
    if dialect_code is DialectCode.EN_AU and ipa_uk and not any(v.dialect is DialectCode.EN_AU for v in variants):
        variants.insert(
            0,
            PronunciationVariant(
                dialect=DialectCode.EN_AU,
                ipa=str(ipa_uk),
                status=PronunciationStatus.INFERRED,
                confidence=0.6,
                evidence=["au_from_uk_ipa"],
            ),
        )

    rarity = row.get("rarity_score") if row is not None else None
    syllable = row.get("syllable_count") if row is not None else None
    stress = row.get("stress_pattern") if row is not None else None
    rhyme = row.get("rhyme_key") if row is not None else None
    definitions = row.get("definitions") if row is not None else None
    register = list(row.get("register_tags") or []) if row is not None else []

    field_confidence: dict[str, float] = {}
    if rarity is not None:
        field_confidence["rarity"] = 0.9
    else:
        field_confidence["rarity"] = 0.0
    if syllable is not None:
        field_confidence["syllable"] = 0.9
    else:
        syllable = _heuristic_syllables(lemma)
        field_confidence["syllable"] = 0.4
    if stress:
        field_confidence["stress"] = 0.85
    else:
        field_confidence["stress"] = 0.0
    if rhyme:
        field_confidence["rhyme"] = 0.85
    else:
        field_confidence["rhyme"] = 0.0
    if variants:
        field_confidence["ipa"] = max(v.confidence for v in variants)
    else:
        field_confidence["ipa"] = 0.0

    definition = None
    if isinstance(definitions, list) and definitions:
        definition = str(definitions[0])
    elif isinstance(definitions, str):
        definition = definitions

    return LexicalRecord(
        record_id=new_id("lex"),
        lemma=lemma.lower().strip(".,;:!?\"'") or lemma,
        definition=definition,
        rarity=float(rarity) if rarity is not None else None,
        register_labels=register,
        pronunciation_variants=variants,
        stress_pattern=str(stress) if stress else None,
        syllable_count=int(syllable) if syllable is not None else None,
        rhyme_keys=[str(rhyme)] if rhyme else [],
        semantic_relations={
            "synonyms": list((row or {}).get("synonyms") or []),
        },
        field_confidence=field_confidence,
        provenance={
            "adapter_version": ADAPTER_VERSION,
            "wordrare_version": wordrare_version(),
            "source": "wordrare.word_record" if row is not None else "heuristic",
            "lemma_found": row is not None,
        },
    )


_HEURISTIC_LEXICON = (
    "river",
    "meadow",
    "quiet",
    "light",
    "dream",
    "stone",
    "water",
    "cloud",
    "leaf",
    "wind",
    "earth",
    "silver",
    "zephyr",
    "aureate",
    "luminous",
    "hushed",
    "willow",
    "pastoral",
    "metre",
    "dusk",
)


def _heuristic_rarity(lemma: str) -> float:
    """Map common lemmas into a stable rarity band without a populated lexicon."""
    word = lemma.lower().strip()
    if not word:
        return 0.0
    base = min(1.0, max(0.0, (len(word) - 3) / 12.0))
    if any(ch in word for ch in "qxjz"):
        base = min(1.0, base + 0.25)
    if word.endswith(("ous", "ate", "ine")):
        base = min(1.0, base + 0.15)
    return round(base, 4)


def _heuristic_constrained_hits(
    *,
    lemma: str | None,
    rhyme_key: str | None,
    syllable_count: int | None,
    min_rarity: float | None,
    max_rarity: float | None,
    limit: int,
) -> list[dict[str, Any]]:
    """Return LexicalRecord-shaped hits from a common-word heuristic lexicon."""
    hits: list[dict[str, Any]] = []
    candidates = [lemma.lower().strip()] if lemma else list(_HEURISTIC_LEXICON)
    for word in candidates:
        if not word:
            continue
        rarity = _heuristic_rarity(word)
        syl = _heuristic_syllables(word)
        if min_rarity is not None and rarity < float(min_rarity):
            continue
        if max_rarity is not None and rarity > float(max_rarity):
            continue
        if syllable_count is not None and syl != int(syllable_count):
            continue
        if rhyme_key is not None and not word.endswith(str(rhyme_key)):
            continue
        record = _row_to_lexical_record(None, word).model_dump(mode="json")
        record["rarity"] = rarity
        record["field_confidence"] = {
            **(record.get("field_confidence") or {}),
            "rarity": 0.35,
        }
        record["provenance"] = {
            **(record.get("provenance") or {}),
            "source": "heuristic_lexicon",
            "lemma_found": False,
        }
        hits.append(record)
        if len(hits) >= max(1, min(limit, 50)):
            break
    return hits


class WordRareAdapter(
    LexicalCapability,
    ProsodyCapability,
    FormScaffoldCapability,
    ConstrainedSearchCapability,
    ProsodicRepairCapability,
):
    """Default in-tree capability surface over WordRare."""

    def lexical_record(self, lemma: str, *, dialect: str = "en-AU") -> dict[str, Any]:
        if not lemma or not str(lemma).strip():
            return unsupported("lexical", reason="empty_lemma")
        try:
            # Heuristic LexicalRecord always succeeds for non-empty lemmas (DB optional).
            record = _row_to_lexical_record(_fetch_word_fields(lemma), lemma, dialect=dialect)
            return {
                "status": "ok",
                "capability": "lexical",
                "record": record.model_dump(mode="json"),
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }
        except Exception as exc:
            return unsupported("lexical", reason=str(exc))

    def rarity(self, lemma: str) -> dict[str, Any]:
        result = self.lexical_record(lemma)
        if is_unsupported(result):
            return unsupported("lexical", reason=result.get("reason"), method="rarity")
        record = result["record"]
        return {
            "status": "ok",
            "capability": "lexical",
            "lemma": record["lemma"],
            "rarity": record.get("rarity"),
            "field_confidence": {"rarity": (record.get("field_confidence") or {}).get("rarity", 0.0)},
            "provenance": record.get("provenance") or {},
            "adapter_version": ADAPTER_VERSION,
            "wordrare_version": wordrare_version(),
        }

    def pronunciation(self, lemma: str, *, dialect: str = "en-AU") -> dict[str, Any]:
        result = self.lexical_record(lemma, dialect=dialect)
        if is_unsupported(result):
            return unsupported("prosody", reason=result.get("reason"), method="pronunciation")
        record = result["record"]
        variants = record.get("pronunciation_variants") or []
        if not variants:
            return unsupported(
                "prosody",
                reason="no_ipa",
                lemma=record.get("lemma"),
                field_confidence=record.get("field_confidence") or {},
            )
        return {
            "status": "ok",
            "capability": "prosody",
            "lemma": record["lemma"],
            "pronunciation_variants": variants,
            "field_confidence": {"ipa": (record.get("field_confidence") or {}).get("ipa", 0.0)},
            "provenance": record.get("provenance") or {},
            "adapter_version": ADAPTER_VERSION,
            "wordrare_version": wordrare_version(),
        }

    def syllable_stress_rhyme(self, lemma: str) -> dict[str, Any]:
        result = self.lexical_record(lemma)
        if is_unsupported(result):
            return unsupported("prosody", reason=result.get("reason"), method="syllable_stress_rhyme")
        record = result["record"]
        return {
            "status": "ok",
            "capability": "prosody",
            "lemma": record["lemma"],
            "syllable_count": record.get("syllable_count"),
            "stress_pattern": record.get("stress_pattern"),
            "rhyme_keys": record.get("rhyme_keys") or [],
            "field_confidence": {
                k: (record.get("field_confidence") or {}).get(k, 0.0)
                for k in ("syllable", "stress", "rhyme")
            },
            "provenance": record.get("provenance") or {},
            "adapter_version": ADAPTER_VERSION,
            "wordrare_version": wordrare_version(),
        }

    def form_scaffold(self, form_id: str) -> dict[str, Any]:
        if not form_id or not str(form_id).strip():
            return unsupported("form_scaffold", reason="empty_form_id")
        try:
            from wordrare.forms.form_library import FormLibrary

            library = FormLibrary()
            form = library.get_form(form_id.strip().lower())
            if form is None:
                return unsupported("form_scaffold", reason="unknown_form", form_id=form_id)
            # Plain dict only — no FormSpec / ORM types
            return {
                "status": "ok",
                "capability": "form_scaffold",
                "scaffold": {
                    "form_id": form.form_id,
                    "name": form.name,
                    "description": form.description,
                    "total_lines": form.total_lines,
                    "rhyme_pattern": form.rhyme_pattern,
                    "meter_pattern": form.meter_pattern,
                    "stanza_specs": [
                        {
                            "stanza_id": s.stanza_id,
                            "lines": s.lines,
                            "rhyme_pattern": list(s.rhyme_pattern),
                            "meter_pattern": s.meter_pattern,
                        }
                        for s in form.stanza_specs
                    ],
                },
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }
        except Exception as exc:
            return unsupported("form_scaffold", reason=str(exc), form_id=form_id)

    def list_forms(self) -> dict[str, Any]:
        try:
            from wordrare.forms.form_library import FormLibrary

            forms = FormLibrary().list_forms()
            if not forms:
                return unsupported("form_scaffold", reason="no_forms_loaded")
            return {
                "status": "ok",
                "capability": "form_scaffold",
                "forms": list(forms),
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }
        except Exception as exc:
            return unsupported("form_scaffold", reason=str(exc))

    def constrained_search(
        self,
        *,
        lemma: str | None = None,
        rhyme_key: str | None = None,
        syllable_count: int | None = None,
        min_rarity: float | None = None,
        max_rarity: float | None = None,
        limit: int = 5,
    ) -> dict[str, Any]:
        if lemma is None and rhyme_key is None and syllable_count is None and min_rarity is None:
            return unsupported("constrained_search", reason="no_constraints")
        try:
            from wordrare.database import WordRecord, get_session

            with get_session() as session:
                query = session.query(WordRecord)
                if lemma:
                    query = query.filter(WordRecord.lemma == lemma.lower().strip())
                if rhyme_key:
                    query = query.filter(WordRecord.rhyme_key == rhyme_key)
                if syllable_count is not None:
                    query = query.filter(WordRecord.syllable_count == int(syllable_count))
                if min_rarity is not None:
                    query = query.filter(WordRecord.rarity_score >= float(min_rarity))
                if max_rarity is not None:
                    query = query.filter(WordRecord.rarity_score <= float(max_rarity))
                rows = query.limit(max(1, min(limit, 50))).all()
                field_rows = [
                    {
                        "lemma": row.lemma,
                        "ipa_uk": row.ipa_uk,
                        "ipa_us": row.ipa_us,
                        "rarity_score": row.rarity_score,
                        "syllable_count": row.syllable_count,
                        "stress_pattern": row.stress_pattern,
                        "rhyme_key": row.rhyme_key,
                        "definitions": list(row.definitions or []) if row.definitions else None,
                        "register_tags": list(row.register_tags or []) if row.register_tags else [],
                        "synonyms": [],
                    }
                    for row in rows
                ]
            hits = [
                _row_to_lexical_record(fields, fields["lemma"]).model_dump(mode="json")
                for fields in field_rows
            ]
            if not hits:
                hits = _heuristic_constrained_hits(
                    lemma=lemma,
                    rhyme_key=rhyme_key,
                    syllable_count=syllable_count,
                    min_rarity=min_rarity,
                    max_rarity=max_rarity,
                    limit=limit,
                )
            if not hits:
                return unsupported(
                    "constrained_search",
                    reason="no_matches",
                    constraints={
                        "lemma": lemma,
                        "rhyme_key": rhyme_key,
                        "syllable_count": syllable_count,
                        "min_rarity": min_rarity,
                        "max_rarity": max_rarity,
                    },
                )
            return {
                "status": "ok",
                "capability": "constrained_search",
                "hits": hits,
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }
        except Exception as exc:
            hits = _heuristic_constrained_hits(
                lemma=lemma,
                rhyme_key=rhyme_key,
                syllable_count=syllable_count,
                min_rarity=min_rarity,
                max_rarity=max_rarity,
                limit=limit,
            )
            if hits:
                return {
                    "status": "ok",
                    "capability": "constrained_search",
                    "hits": hits,
                    "adapter_version": ADAPTER_VERSION,
                    "wordrare_version": wordrare_version(),
                    "warning": str(exc),
                }
            return unsupported("constrained_search", reason=str(exc))

    def diagnose_line(self, line: str, target_spec: dict[str, Any] | None = None) -> dict[str, Any]:
        if not line or not str(line).strip():
            return unsupported("prosodic_repair", reason="empty_line")
        try:
            from wordrare.constraints.repair import ConflictDetector

            detector = ConflictDetector()
            conflict = detector.detect_conflict(line, target_spec or {})
            return {
                "status": "ok",
                "capability": "prosodic_repair",
                "line": line,
                "conflict": conflict.value if conflict is not None else None,
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }
        except Exception as exc:
            # Heuristic fallback diagnosis (still explicit ok, not None)
            words = [w for w in line.split() if w.strip()]
            return {
                "status": "ok",
                "capability": "prosodic_repair",
                "line": line,
                "conflict": "meter" if len(words) > 12 else None,
                "inferred": True,
                "warning": str(exc),
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }

    def repair_line(self, line: str, target_spec: dict[str, Any] | None = None) -> dict[str, Any]:
        if not line or not str(line).strip():
            return unsupported("prosodic_repair", reason="empty_line")
        try:
            from wordrare.constraints.repair import ConflictDetector, LineRepairer

            detector = ConflictDetector()
            conflict = detector.detect_conflict(line, target_spec or {})
            if conflict is None:
                return {
                    "status": "ok",
                    "capability": "prosodic_repair",
                    "original": line,
                    "repaired": line,
                    "changed": False,
                    "adapter_version": ADAPTER_VERSION,
                    "wordrare_version": wordrare_version(),
                }
            repairer = LineRepairer()
            repaired = repairer.repair_line(line, target_spec or {}, conflict)
            if repaired is None:
                return unsupported(
                    "prosodic_repair",
                    reason="repair_failed",
                    conflict=conflict.value,
                    original=line,
                )
            return {
                "status": "ok",
                "capability": "prosodic_repair",
                "original": line,
                "repaired": repaired,
                "changed": repaired != line,
                "conflict": conflict.value,
                "adapter_version": ADAPTER_VERSION,
                "wordrare_version": wordrare_version(),
            }
        except Exception as exc:
            return unsupported("prosodic_repair", reason=str(exc), method="repair_line")


_DEFAULT = WordRareAdapter()


def get_adapter() -> WordRareAdapter:
    return _DEFAULT


def lexical_record(lemma: str, *, dialect: str = "en-AU") -> dict[str, Any]:
    return _DEFAULT.lexical_record(lemma, dialect=dialect)


def rarity(lemma: str) -> dict[str, Any]:
    return _DEFAULT.rarity(lemma)


def pronunciation(lemma: str, *, dialect: str = "en-AU") -> dict[str, Any]:
    return _DEFAULT.pronunciation(lemma, dialect=dialect)


def syllable_stress_rhyme(lemma: str) -> dict[str, Any]:
    return _DEFAULT.syllable_stress_rhyme(lemma)


def form_scaffold(form_id: str) -> dict[str, Any]:
    return _DEFAULT.form_scaffold(form_id)


def list_forms() -> dict[str, Any]:
    return _DEFAULT.list_forms()


def constrained_search(**kwargs: Any) -> dict[str, Any]:
    return _DEFAULT.constrained_search(**kwargs)


def diagnose_line(line: str, target_spec: dict[str, Any] | None = None) -> dict[str, Any]:
    return _DEFAULT.diagnose_line(line, target_spec)


def repair_line(line: str, target_spec: dict[str, Any] | None = None) -> dict[str, Any]:
    return _DEFAULT.repair_line(line, target_spec)


def lexical_snapshot(text: str) -> dict[str, Any]:
    """Return simple lexical stats; degrades gracefully without DB content."""
    tokens = [t.strip(".,;:!?\"'").lower() for t in text.split() if t.strip()]
    content = [t for t in tokens if len(t) > 2]
    rarity_hits = 0
    known = 0
    try:
        from wordrare.database import WordRecord, get_session

        with get_session() as session:
            for token in content[:40]:
                row = session.query(WordRecord).filter(WordRecord.lemma == token).first()
                if row is None:
                    continue
                known += 1
                if (row.rarity_score or 0) >= 0.5:
                    rarity_hits += 1
    except Exception:
        pass
    return {
        "token_count": len(tokens),
        "content_tokens": len(content),
        "known_in_lexicon": known,
        "rare_hits": rarity_hits,
        "adapter_version": ADAPTER_VERSION,
        "wordrare_version": wordrare_version(),
    }


def _looks_degenerate(original: str, revised: str) -> bool:
    """Reject rewriter output that collapses into repetitive junk."""
    if not revised or revised == original:
        return True
    words = [w.lower().strip(".,;:!?") for w in revised.split() if w.strip()]
    if not words:
        return True
    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.7:
        return True
    for i in range(len(words) - 1):
        if words[i] == words[i + 1] and words.count(words[i]) >= 2 and len(words) <= 8:
            return True
    for i in range(len(words) - 2):
        if words[i] == words[i + 1] == words[i + 2]:
            return True
    return False


def rare_reword_line(line: str) -> str | None:
    try:
        from wordrare.generation.generation_spec import GenerationSpec
        from wordrare.generation.prose_rewrite import ProseRewriter

        rewriter = ProseRewriter(
            GenerationSpec(min_rarity=0.0, max_rarity=1.0, rarity_bias=0.7)
        )
        result = rewriter.rewrite(line)
        revised = result.get("rewritten") if isinstance(result, dict) else None
        if revised and not _looks_degenerate(line, revised):
            return revised
    except Exception:
        pass
    return None


def rare_reword_paragraph(text: str) -> dict[str, Any]:
    try:
        from wordrare.generation.generation_spec import GenerationSpec
        from wordrare.generation.prose_rewrite import ProseRewriter

        rewriter = ProseRewriter(
            GenerationSpec(min_rarity=0.0, max_rarity=1.0, rarity_bias=0.7)
        )
        return rewriter.rewrite(text)
    except Exception as exc:
        return {"rewritten": text, "error": str(exc)}


def similar_lemmas(lemma: str, limit: int = 5) -> list[str]:
    try:
        from wordrare.semantic.embedder import SemanticEmbedder

        embedder = SemanticEmbedder()
        if hasattr(embedder, "find_similar_words"):
            return list(embedder.find_similar_words(lemma, limit=limit) or [])
    except Exception:
        pass
    return []


def generate_poem(*, form: str = "haiku", theme: str = "nature", debug: bool = True) -> dict[str, Any]:
    try:
        from wordrare.generation import GenerationSpec, PoemGenerator

        poem = PoemGenerator().generate(
            GenerationSpec(
                form=form,
                theme=theme,
                rarity_bias=0.5,
                min_rarity=0.0,
                max_rarity=1.0,
                debug_mode=debug,
                steering_policy="free_verse",
            )
        )
        return {
            "text": poem.text,
            "lines": poem.lines,
            "metrics": getattr(poem, "metrics", {}),
            "wordrare_version": wordrare_version(),
        }
    except Exception as exc:
        return {"text": "", "error": str(exc), "wordrare_version": wordrare_version()}
