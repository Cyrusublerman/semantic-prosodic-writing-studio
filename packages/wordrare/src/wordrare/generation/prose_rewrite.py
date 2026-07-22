"""
Deterministic rare-word paragraph rewrite (no LLM).

Replaces eligible content words from the lexicon under POS + rarity_bias,
preserving function words. Emits before/after text and phonetic audit strip.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Set

from ..database import WordRecord, get_session
from .annotator import PoemAnnotator
from .generation_spec import GenerationSpec

logger = logging.getLogger(__name__)

FUNCTION_POS = frozenset(
    {"article", "preposition", "conjunction", "pronoun", "determiner"}
)
CONTENT_POS = frozenset({"noun", "verb", "adjective", "adverb"})

# Crude closed-class list for tokens missing from the lexicon
FUNCTION_WORDS = frozenset(
    """
    the a an of in on with to for and or but as at by from into over under
    is are was were be been being am this that these those it its he she they
    we you i my your his her their our not no nor so if then than
    """.split()
)


class ProseRewriter:
    """Rewrite prose by substituting rare lexicon content words."""

    def __init__(self, spec: Optional[GenerationSpec] = None):
        self.spec = spec or GenerationSpec(
            min_rarity=0.3, max_rarity=1.0, rarity_bias=0.7, temperature=0.5
        )
        self.annotator = PoemAnnotator()

    def rewrite(self, paragraph: str) -> Dict:
        tokens = self._tokenize(paragraph)
        replacements: List[Dict] = []
        out_tokens: List[str] = []

        for token in tokens:
            if token["kind"] != "word":
                out_tokens.append(token["text"])
                continue

            lemma = token["text"].lower()
            if lemma in FUNCTION_WORDS:
                out_tokens.append(token["text"])
                continue

            info = self._lookup_info(lemma)
            pos = info.get("pos")
            if pos in FUNCTION_POS:
                out_tokens.append(token["text"])
                continue

            # Only rewrite known content POS or unknown alpha words treated as nouns
            target_pos = pos if pos in CONTENT_POS else "noun"
            substitute = self._find_substitute(
                lemma, target_pos, info.get("syllable_count")
            )
            if not substitute or substitute.lower() == lemma:
                out_tokens.append(token["text"])
                continue

            rewritten = self._match_case(token["text"], substitute)
            replacements.append(
                {
                    "original": token["text"],
                    "replacement": rewritten,
                    "pos": target_pos,
                }
            )
            out_tokens.append(rewritten)

        rewritten_text = "".join(out_tokens)
        # Annotate as pseudo-lines (split on sentence end) for strip display
        lines = [ln.strip() for ln in re.split(r"(?<=[.!?])\s+", rewritten_text) if ln.strip()]
        if not lines:
            lines = [rewritten_text]
        annotations = self.annotator.annotate(lines)

        return {
            "original": paragraph,
            "rewritten": rewritten_text,
            "replacements": replacements,
            "annotations": annotations,
            "audit": self.annotator.format_debug_strip(annotations),
        }

    def _tokenize(self, text: str) -> List[Dict]:
        parts = re.split(r"(\w+)", text)
        tokens = []
        for part in parts:
            if not part:
                continue
            if re.fullmatch(r"\w+", part):
                tokens.append({"kind": "word", "text": part})
            else:
                tokens.append({"kind": "other", "text": part})
        return tokens

    def _lookup_info(self, lemma: str) -> Dict:
        with get_session() as session:
            record = session.query(WordRecord).filter_by(lemma=lemma).first()
            if not record:
                return {}
            return {
                "pos": record.pos_primary,
                "syllable_count": record.syllable_count,
                "rarity_score": record.rarity_score,
            }

    def _find_substitute(
        self, lemma: str, pos: str, syllable_count: Optional[int]
    ) -> Optional[str]:
        with get_session() as session:
            query = session.query(WordRecord).filter(
                WordRecord.pos_primary == pos,
                WordRecord.rarity_score >= self.spec.min_rarity,
                WordRecord.rarity_score <= self.spec.max_rarity,
                WordRecord.lemma != lemma,
            )
            if syllable_count:
                same = query.filter(
                    WordRecord.syllable_count == syllable_count
                ).limit(40).all()
                pool = same or query.limit(40).all()
            else:
                pool = query.limit(40).all()

            if not pool:
                return None

            bias = self.spec.rarity_bias
            ranked = sorted(
                [(r.lemma, r.rarity_score or 0.5) for r in pool],
                key=lambda item: abs(item[1] - bias),
            )
            if self.spec.temperature <= 0.0:
                return ranked[0][0]
            idx = min(int(self.spec.temperature * (len(ranked) - 1)), len(ranked) - 1)
            return ranked[idx][0]

    @staticmethod
    def _match_case(original: str, replacement: str) -> str:
        if original.isupper():
            return replacement.upper()
        if original[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Rare-word prose rewriter")
    parser.add_argument("text", nargs="?", help="Paragraph to rewrite")
    parser.add_argument("--file", type=str, help="Read paragraph from file")
    parser.add_argument("--rarity", type=float, default=0.7)
    parser.add_argument("--min-rarity", type=float, default=0.3)
    parser.add_argument("--max-rarity", type=float, default=1.0)
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            text = f.read().strip()
    elif args.text:
        text = args.text
    else:
        parser.error("Provide text or --file")

    rewriter = ProseRewriter(
        GenerationSpec(
            rarity_bias=args.rarity,
            min_rarity=args.min_rarity,
            max_rarity=args.max_rarity,
        )
    )
    result = rewriter.rewrite(text)
    print("ORIGINAL:")
    print(result["original"])
    print("\nREWRITTEN:")
    print(result["rewritten"])
    print(f"\nReplacements ({len(result['replacements'])}):")
    for r in result["replacements"]:
        print(f"  {r['original']} -> {r['replacement']} ({r['pos']})")
    print("\nAUDIT:")
    print(result["audit"])


if __name__ == "__main__":
    main()
