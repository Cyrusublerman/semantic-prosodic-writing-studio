"""
Poetic device enforcement (deterministic, rate-driven).
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional

from ..database import Phonetics, WordRecord, get_session
from ..forms import SoundEngine
from ..forms.grammar_engine import resolve_articles

logger = logging.getLogger(__name__)

_CLOSED = frozenset({"the", "a", "an", "of", "in", "on", "to", "and", "or", "but", "with"})


def merge_device_profile(form_defaults: Dict, spec_profile: Dict) -> Dict[str, float]:
    out = dict(form_defaults or {})
    for k, v in (spec_profile or {}).items():
        out[k] = v
    return out


class DeviceEnforcer:
    """Bias/rewrite lines toward device_profile rates."""

    def __init__(self, profile: Dict[str, float]):
        self.profile = profile or {}
        self.sound = SoundEngine()
        self.stats = {
            "alliteration_hits": 0,
            "assonance_hits": 0,
            "consonance_hits": 0,
            "internal_rhyme_hits": 0,
            "caesura_hits": 0,
            "enjambment_hits": 0,
            "lines": 0,
        }

    def apply(self, lines: List[str], motif_lemmas: Optional[List[str]] = None) -> List[str]:
        motif_lemmas = motif_lemmas or []
        out: List[str] = []
        for i, line in enumerate(lines):
            if line.startswith("["):
                out.append(line)
                continue
            self.stats["lines"] += 1
            words = line.split()
            content_idx = [
                j
                for j, w in enumerate(words)
                if w.lower().strip(".,!?;:") not in _CLOSED
            ]

            # Alliteration: rewrite one content onset to match neighbor
            rate = float(self.profile.get("alliteration_rate", 0) or 0)
            if rate > 0 and len(content_idx) >= 2 and random.random() < rate:
                content = [words[j] for j in content_idx]
                if self.sound.check_alliteration(content[:3]):
                    self.stats["alliteration_hits"] += 1
                else:
                    rewritten = self._rewrite_onset_match(words, content_idx)
                    if rewritten:
                        words = rewritten
                        self.stats["alliteration_hits"] += 1

            # Assonance / consonance: nucleus/coda swaps when rate unmet
            if float(self.profile.get("assonance_rate", 0) or 0) > 0:
                content = [
                    words[j]
                    for j in content_idx
                    if j < len(words)
                ]
                if len(content) >= 2 and self.sound.check_assonance(content):
                    self.stats["assonance_hits"] += 1
                elif (
                    float(self.profile.get("assonance_rate", 0) or 0) > 0.3
                    and len(content_idx) >= 2
                    and random.random()
                    < float(self.profile.get("assonance_rate", 0) or 0)
                ):
                    rewritten = self._rewrite_nucleus_match(words, content_idx)
                    if rewritten:
                        words = rewritten
                        self.stats["assonance_hits"] += 1

            if float(self.profile.get("consonance_rate", 0) or 0) > 0:
                content = [words[j] for j in content_idx if j < len(words)]
                if len(content) >= 2 and self.sound.check_consonance(content):
                    self.stats["consonance_hits"] += 1
                elif (
                    float(self.profile.get("consonance_rate", 0) or 0) > 0.3
                    and len(content_idx) >= 2
                    and random.random()
                    < float(self.profile.get("consonance_rate", 0) or 0)
                ):
                    rewritten = self._rewrite_coda_match(words, content_idx)
                    if rewritten:
                        words = rewritten
                        self.stats["consonance_hits"] += 1

            # Internal rhyme: align mid content key to end key
            ir = float(self.profile.get("internal_rhyme_rate", 0) or 0)
            if ir > 0 and len(content_idx) >= 3 and random.random() < ir:
                mid_i = content_idx[len(content_idx) // 2]
                end_i = content_idx[-1]
                # Never rewrite final token for internal rhyme (plan fidelity)
                if mid_i != end_i and mid_i < len(words) - 1:
                    end = words[end_i].lower().strip(".,!?;:")
                    m = self.sound.check_rhyme(
                        words[mid_i].lower().strip(".,!?;:"), end
                    )
                    if m and m.similarity >= 0.7:
                        self.stats["internal_rhyme_hits"] += 1
                    else:
                        alt = self._find_rhyme_lemma(
                            end,
                            pos=None,
                            syllables=self._syllables(words[mid_i]),
                            exclude={end},
                        )
                        if alt:
                            words[mid_i] = alt
                            self.stats["internal_rhyme_hits"] += 1

            # Caesura: insert medial comma — never on final token
            cr = float(self.profile.get("caesura_rate", 0) or 0)
            if cr > 0 and len(words) >= 4 and random.random() < cr and "," not in " ".join(words):
                mid = min(len(words) // 2, len(words) - 2)
                if mid >= 0 and mid < len(words) - 1:
                    words = list(words)
                    words[mid] = words[mid].rstrip(",.!?;:") + ","
                    self.stats["caesura_hits"] += 1

            words = resolve_articles(words)
            out.append(" ".join(words))

            # Enjambment: strip terminal punctuation between lines
            er = float(self.profile.get("enjambment_rate", 0) or 0)
            if er > 0 and i + 1 < len(lines) and random.random() < er:
                if out[-1] and out[-1][-1] in ".!?;:":
                    out[-1] = out[-1].rstrip(".!?;:")
                self.stats["enjambment_hits"] += 1

        return out

    def _syllables(self, word: str) -> int:
        from ..forms import MeterEngine

        return MeterEngine().get_word_syllables(word.lower().strip(".,!?;:"))

    def _onset_of(self, lemma: str) -> str:
        with get_session() as session:
            p = session.query(Phonetics).filter_by(lemma=lemma.lower()).first()
            if p and p.onset:
                return p.onset.split()[0] if " " in p.onset else p.onset
        return lemma[:1].lower() if lemma else ""

    def _find_by_onset(
        self, onset: str, syllables: int, exclude: set, pos: Optional[str] = None
    ) -> Optional[str]:
        with get_session() as session:
            q = session.query(WordRecord).filter(WordRecord.syllable_count == syllables)
            if pos:
                q = q.filter(WordRecord.pos_primary == pos)
            for rec in q.limit(80).all():
                if rec.lemma.lower() in exclude:
                    continue
                if self._onset_of(rec.lemma) == onset:
                    return rec.lemma
        return None

    def _find_rhyme_lemma(
        self,
        rhyme_with: str,
        pos: Optional[str],
        syllables: int,
        exclude: set,
    ) -> Optional[str]:
        key = self.sound.get_rhyme_key(rhyme_with)
        if not key:
            return None
        with get_session() as session:
            q = session.query(WordRecord).filter(
                WordRecord.rhyme_key == key,
                WordRecord.syllable_count == syllables,
            )
            if pos:
                q = q.filter(WordRecord.pos_primary == pos)
            for rec in q.limit(40).all():
                if rec.lemma.lower() not in exclude:
                    return rec.lemma
        return None

    def _rewrite_onset_match(
        self, words: List[str], content_idx: List[int]
    ) -> Optional[List[str]]:
        """Swap a non-final content word to share onset with the first content word."""
        if len(content_idx) < 2:
            return None
        target_i = content_idx[0]
        swap_i = content_idx[1]
        if swap_i >= len(words) - 1:
            # Prefer non-final; fall back to earlier content
            for j in content_idx[1:]:
                if j < len(words) - 1:
                    swap_i = j
                    break
            else:
                return None
        onset = self._onset_of(words[target_i].lower().strip(".,!?;:"))
        if not onset:
            return None
        orig = words[swap_i].lower().strip(".,!?;:")
        alt = self._find_by_onset(
            onset,
            self._syllables(orig),
            exclude={orig, words[-1].lower().strip(".,!?;:")},
        )
        if not alt:
            return None
        out = list(words)
        out[swap_i] = alt
        return out

    def _rewrite_nucleus_match(
        self, words: List[str], content_idx: List[int]
    ) -> Optional[List[str]]:
        if len(content_idx) < 2:
            return None
        a = content_idx[0]
        b = next((j for j in content_idx[1:] if j < len(words) - 1), None)
        if b is None:
            return None
        with get_session() as session:
            pa = session.query(Phonetics).filter_by(
                lemma=words[a].lower().strip(".,!?;:")
            ).first()
            if not pa or not pa.nucleus:
                return None
            nucleus = pa.nucleus
            syll = self._syllables(words[b])
            rows = (
                session.query(WordRecord)
                .filter(WordRecord.syllable_count == syll)
                .limit(60)
                .all()
            )
            for rec in rows:
                if rec.lemma.lower() == words[b].lower().strip(".,!?;:"):
                    continue
                pb = session.query(Phonetics).filter_by(lemma=rec.lemma).first()
                if pb and pb.nucleus == nucleus:
                    out = list(words)
                    out[b] = rec.lemma
                    return out
        return None

    def _rewrite_coda_match(
        self, words: List[str], content_idx: List[int]
    ) -> Optional[List[str]]:
        if len(content_idx) < 2:
            return None
        a = content_idx[0]
        b = next((j for j in content_idx[1:] if j < len(words) - 1), None)
        if b is None:
            return None
        with get_session() as session:
            pa = session.query(Phonetics).filter_by(
                lemma=words[a].lower().strip(".,!?;:")
            ).first()
            if not pa or not pa.coda:
                return None
            coda = pa.coda
            syll = self._syllables(words[b])
            rows = (
                session.query(WordRecord)
                .filter(WordRecord.syllable_count == syll)
                .limit(60)
                .all()
            )
            for rec in rows:
                if rec.lemma.lower() == words[b].lower().strip(".,!?;:"):
                    continue
                pb = session.query(Phonetics).filter_by(lemma=rec.lemma).first()
                if pb and pb.coda == coda:
                    out = list(words)
                    out[b] = rec.lemma
                    return out
        return None

    def rates(self) -> Dict[str, float]:
        n = max(1, self.stats["lines"])
        return {
            "alliteration": self.stats["alliteration_hits"] / n,
            "assonance": self.stats["assonance_hits"] / n,
            "consonance": self.stats["consonance_hits"] / n,
            "internal_rhyme": self.stats["internal_rhyme_hits"] / n,
            "caesura": self.stats["caesura_hits"] / n,
            "enjambment": self.stats["enjambment_hits"] / n,
        }
