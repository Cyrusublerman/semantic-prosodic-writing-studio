"""
Line realization - fills scaffolds with actual words.

Selects words based on constraints: rhyme, meter, semantics, POS, rarity.
Hard rule: never reuse the same end-lemma within a rhyme group (no identical rhyme).
"""

from __future__ import annotations

import logging
import math
import random
from typing import Dict, List, Optional, Set, Tuple

from ..constraints.constraint_model import ConstraintModel, SteeringPolicy
from ..constraints.repair import ConflictDetector, LineRepairer
from ..database import ConceptNode, WordRecord, get_session
from ..forms import MeterEngine, SoundEngine
from ..forms.grammar_engine import resolve_articles
from ..forms.meter_engine import expected_stress_bits, stress_fit_score
from ..forms.rhyme_plan import RhymeSlot
from .generation_spec import GenerationSpec
from .scaffolding import LineScaffold, PoemScaffold

logger = logging.getLogger(__name__)

RHYME_CAPABLE_POS = frozenset({"noun", "adjective", "verb"})
_FUNCTION_POS = frozenset({"article", "preposition", "conjunction", "pronoun"})
_FUNCTION_LEMMAS = frozenset({
    "the", "a", "an", "of", "to", "in", "on", "at", "for", "and", "or", "but", "with",
})
W_RARITY = 0.55
W_EMB = 0.35
W_PALETTE = 0.10
# Soft weight: subtract from rank cost when constraints include expected_stress
_W_STRESS = 0.20


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return max(-1.0, min(1.0, dot / (na * nb)))


class WordSelector:
    """Selects words based on multiple constraints."""

    def __init__(self, spec: GenerationSpec, semantic_palette: Dict):
        self.spec = spec
        self.semantic_palette = semantic_palette
        self.sound_engine = SoundEngine()
        self.meter_engine = MeterEngine()
        self._word_cache: Dict = {}
        self._palette_lemmas = self._flatten_palette()
        self._motif_centroid = self._load_motif_centroid()
        self._last_trace: Dict = {}
        self.force_motif_prob = float(
            semantic_palette.get("motif_density")
            if semantic_palette.get("motif_density") is not None
            else getattr(spec, "motif_density", 0.0)
            or 0.0
        )
        self._required_syl_keys: Dict[int, str] = {}  # word-syl offset → key
        self._cohort_cache: Dict[Tuple[str, int], int] = {}
        self.prefer_large_cohorts: bool = False
        self._large_cohort_lemmas: Optional[Set[str]] = None
        self.match_mode: str = "perfect"

    def _flatten_palette(self) -> Set[str]:
        # Track S: word_pools is a flat lemma list; accept legacy {motif: [words]} too.
        pools = self.semantic_palette.get("word_pools") or []
        lemmas: Set[str] = set()
        if isinstance(pools, dict):
            for words in pools.values():
                lemmas.update(words)
        else:
            lemmas.update(pools)
        for key in ("motif_words", "theme_words"):
            extra = self.semantic_palette.get(key) or []
            if isinstance(extra, (list, tuple, set)):
                lemmas.update(extra)
        return lemmas

    def _load_motif_centroid(self) -> Optional[List[float]]:
        """Average motif/concept centroids from the palette when present."""
        cached = self.semantic_palette.get("motif_centroid")
        if cached:
            return list(cached)

        motif_ids = list(self.semantic_palette.get("motifs") or [])
        theme_ids = list(self.semantic_palette.get("theme_concepts") or [])
        node_ids = motif_ids or theme_ids
        if not node_ids:
            return None

        vectors: List[List[float]] = []
        with get_session() as session:
            for nid in node_ids:
                node = session.query(ConceptNode).filter_by(id=nid).first()
                if node and node.centroid_embedding:
                    vectors.append(list(node.centroid_embedding))
        if not vectors:
            return None

        dim = len(vectors[0])
        centroid = [0.0] * dim
        for vec in vectors:
            if len(vec) != dim:
                continue
            for i, v in enumerate(vec):
                centroid[i] += float(v)
        n = float(len(vectors))
        return [c / n for c in centroid]

    def select_word(
        self,
        pos: str,
        constraints: Dict,
        rhyme_word: Optional[str] = None,
        exclude_lemmas: Optional[Set[str]] = None,
        end_n: int = 1,
        required_syl_keys: Optional[List[Optional[str]]] = None,
    ) -> Optional[str]:
        """Select a word matching POS and constraints."""
        exclude_lemmas = exclude_lemmas or set()
        self._last_trace = {"syllable_relaxed": False, "pos": pos}
        # Motif density: fraction of content slots hard-drawn from motif pools
        require_palette = False
        if (
            self.force_motif_prob > 0
            and pos in RHYME_CAPABLE_POS
            and self._palette_lemmas
            and random.random() < self.force_motif_prob
        ):
            require_palette = True
            constraints = dict(constraints)
            constraints["force_palette"] = True

        candidates = self._query_candidates(
            pos,
            constraints,
            rhyme_word,
            exclude_lemmas,
            end_n=end_n,
            require_palette=require_palette,
        )
        if not candidates and "syllables" in constraints:
            loose = {k: v for k, v in constraints.items() if k != "syllables"}
            candidates = self._query_candidates(
                pos,
                loose,
                rhyme_word,
                exclude_lemmas,
                end_n=end_n,
                require_palette=require_palette,
            )
            self._last_trace["syllable_relaxed"] = bool(candidates)

        # Fallback order: (1) drop palette, (2) widen rarity toward [0,1]
        if not candidates and (require_palette or self._palette_lemmas):
            candidates = self._query_candidates(
                pos,
                constraints,
                rhyme_word,
                exclude_lemmas,
                end_n=end_n,
                require_palette=False,
            )
            if not candidates and "syllables" in constraints:
                loose = {k: v for k, v in constraints.items() if k != "syllables"}
                candidates = self._query_candidates(
                    pos,
                    loose,
                    rhyme_word,
                    exclude_lemmas,
                    end_n=end_n,
                    require_palette=False,
                )
                self._last_trace["syllable_relaxed"] = bool(candidates)
            self._last_trace["palette_dropped"] = bool(candidates)
            logger.debug("select_word palette_dropped pos=%s", pos)

        if not candidates:
            old_min, old_max = self.spec.min_rarity, self.spec.max_rarity
            self.spec.min_rarity, self.spec.max_rarity = 0.0, 1.0
            try:
                candidates = self._query_candidates(
                    pos,
                    constraints,
                    rhyme_word,
                    exclude_lemmas,
                    end_n=end_n,
                    require_palette=False,
                )
                if not candidates and "syllables" in constraints:
                    loose = {k: v for k, v in constraints.items() if k != "syllables"}
                    candidates = self._query_candidates(
                        pos,
                        loose,
                        rhyme_word,
                        exclude_lemmas,
                        end_n=end_n,
                        require_palette=False,
                    )
            finally:
                self.spec.min_rarity, self.spec.max_rarity = old_min, old_max
            self._last_trace["rarity_widened"] = bool(candidates)
            if candidates:
                logger.debug("select_word rarity_widened pos=%s", pos)

        if candidates and required_syl_keys and any(required_syl_keys):
            filtered = [
                c
                for c in candidates
                if self._matches_syl_keys(c, required_syl_keys)
            ]
            if filtered:
                candidates = filtered
            else:
                # Direct rhyme_key lookup for monosyllable bound slots
                need = next((k for k in required_syl_keys if k), None)
                if need and len(required_syl_keys) == 1:
                    direct: List[str] = []
                    mode = self.match_mode or "perfect"
                    if mode == "perfect":
                        with get_session() as session:
                            for pos_try in (pos, "noun", "adjective", "verb"):
                                if pos_try != pos and pos not in RHYME_CAPABLE_POS:
                                    break
                                q = session.query(WordRecord).filter(
                                    WordRecord.pos_primary == pos_try,
                                    WordRecord.rhyme_key == need,
                                    WordRecord.syllable_count == 1,
                                )
                                direct = [
                                    r.lemma
                                    for r in q.limit(40).all()
                                    if r.lemma not in exclude_lemmas
                                    and (
                                        not rhyme_word
                                        or r.lemma.lower() != rhyme_word.lower()
                                    )
                                ]
                                if direct:
                                    break
                            if not direct and pos in RHYME_CAPABLE_POS:
                                q = session.query(WordRecord).filter(
                                    WordRecord.rhyme_key == need,
                                    WordRecord.syllable_count == 1,
                                )
                                direct = [
                                    r.lemma
                                    for r in q.limit(40).all()
                                    if r.lemma not in exclude_lemmas
                                    and r.lemma.lower() not in _FUNCTION_LEMMAS
                                ]
                    else:
                        # Assonance/slant: scan 1-syl content and key-match
                        with get_session() as session:
                            pool = [
                                r.lemma
                                for r in session.query(WordRecord)
                                .filter(
                                    WordRecord.syllable_count == 1,
                                    WordRecord.pos_primary.in_(
                                        list(RHYME_CAPABLE_POS)
                                    ),
                                )
                                .limit(200)
                                .all()
                                if r.lemma not in exclude_lemmas
                            ]
                        direct = [
                            c
                            for c in pool
                            if self._matches_syl_keys(c, required_syl_keys)
                        ][:40]
                    if direct:
                        candidates = direct
                        self._last_trace["syl_key_direct"] = True
                    else:
                        candidates = []
                else:
                    candidates = []

        if not candidates:
            logger.debug(
                "No candidates for pos=%s constraints=%s rhyme=%s exclude=%s end_n=%s",
                pos,
                constraints,
                rhyme_word,
                exclude_lemmas,
                end_n,
            )
            return None

        if self.prefer_large_cohorts and pos in RHYME_CAPABLE_POS:
            large = self._ensure_large_cohort_lemmas(3)
            preferred = [c for c in candidates if c in large]
            if preferred:
                candidates = preferred

        ranked = self._rank_candidates(candidates, constraints)
        return self._select_with_temperature(ranked)

    def _rhyme_cohort_size(self, rhyme_key: str, syllable_count: int = 1) -> int:
        if not rhyme_key:
            return 0
        ck = (rhyme_key, syllable_count)
        if ck in self._cohort_cache:
            return self._cohort_cache[ck]
        with get_session() as session:
            n = (
                session.query(WordRecord)
                .filter(
                    WordRecord.rhyme_key == rhyme_key,
                    WordRecord.syllable_count == syllable_count,
                    WordRecord.pos_primary.in_(list(RHYME_CAPABLE_POS)),
                )
                .count()
            )
        self._cohort_cache[ck] = n
        return n

    def _ensure_large_cohort_lemmas(self, min_cohort: int = 3) -> Set[str]:
        # Cache by min_cohort threshold in the set itself; rebuild if tighter.
        cached_min = getattr(self, "_large_cohort_min", None)
        if self._large_cohort_lemmas is not None and cached_min == min_cohort:
            return self._large_cohort_lemmas
        from collections import defaultdict

        by_key: Dict[str, List[str]] = defaultdict(list)
        with get_session() as session:
            rows = (
                session.query(WordRecord.lemma, WordRecord.rhyme_key)
                .filter(
                    WordRecord.pos_primary.in_(list(RHYME_CAPABLE_POS)),
                    WordRecord.rhyme_key.isnot(None),
                )
                .all()
            )
            for lemma, key in rows:
                by_key[key].append(lemma)
        out: Set[str] = set()
        for key, lemmas in by_key.items():
            n = len(lemmas)
            self._cohort_cache[(key, 1)] = n
            if n >= min_cohort:
                out.update(lemmas)
        self._large_cohort_lemmas = out
        self._large_cohort_min = min_cohort
        return out

    def _matches_syl_keys(
        self, lemma: str, required_syl_keys: List[Optional[str]]
    ) -> bool:
        """True if lemma syllables match required keys (None = unbound)."""
        if not required_syl_keys or not any(required_syl_keys):
            return True
        syls = self.sound_engine.get_word_syllables_phones(lemma)
        if len(syls) != len(required_syl_keys):
            # Allow if required list is padded/truncated to word length
            if len(syls) < len(required_syl_keys):
                return False
            required_syl_keys = required_syl_keys[: len(syls)]
        mode = self.match_mode or "perfect"
        for i, need in enumerate(required_syl_keys):
            if not need:
                continue
            got = (
                self.sound_engine._ipa.syllable_rhyme_key(syls[i], mode=mode)
                if syls[i]
                else ""
            )
            if got == need:
                continue
            if got and self.sound_engine.compare_span(need, got, mode=mode) >= 0.99:
                continue
            if mode == "perfect" and got:
                if self.sound_engine.compare_span(
                    need, got, mode="perfect"
                ) >= self.sound_engine.slant_rhyme_threshold:
                    continue
                if self.sound_engine.compare_span(need, got, mode="assonance") >= 0.99:
                    continue
            return False
        return True

    def _apply_end_rhyme_filter(self, query, rhyme_word: str, end_n: int):
        """Filter query by end-N rhyme key (DB column or defer to runtime)."""
        if end_n <= 1:
            rhyme_key = self.sound_engine.get_rhyme_key(rhyme_word)
            if rhyme_key:
                return query.filter(WordRecord.rhyme_key == rhyme_key), None
            return query, None

        target_key = self.sound_engine.get_end_span_key(rhyme_word, n=end_n)
        if not target_key:
            return query, None

        if end_n == 2 and hasattr(WordRecord, "end_key_2"):
            return query.filter(WordRecord.end_key_2 == target_key), target_key
        if end_n == 3 and hasattr(WordRecord, "end_key_3"):
            return query.filter(WordRecord.end_key_3 == target_key), target_key
        return query, target_key

    def _runtime_end_key_match(self, lemma: str, target_key: str, end_n: int) -> bool:
        if not target_key:
            return True
        return self.sound_engine.get_end_span_key(lemma, n=end_n) == target_key

    def _query_candidates(
        self,
        pos: str,
        constraints: Dict,
        rhyme_word: Optional[str] = None,
        exclude_lemmas: Optional[Set[str]] = None,
        end_n: int = 1,
        require_palette: bool = False,
    ) -> List[str]:
        """Query database for candidate words."""
        exclude_lemmas = exclude_lemmas or set()
        runtime_key: Optional[str] = None
        force_palette = require_palette or bool(constraints.get("force_palette"))

        with get_session() as session:
            query = session.query(WordRecord)

            if pos and pos != "any":
                query = query.filter(WordRecord.pos_primary == pos)

            query = query.filter(
                WordRecord.rarity_score >= self.spec.min_rarity,
                WordRecord.rarity_score <= self.spec.max_rarity,
            )

            if "syllables" in constraints:
                query = query.filter(
                    WordRecord.syllable_count == constraints["syllables"]
                )

            if rhyme_word:
                query, runtime_key = self._apply_end_rhyme_filter(
                    query, rhyme_word, end_n
                )

            if force_palette and self._palette_lemmas:
                query = query.filter(WordRecord.lemma.in_(list(self._palette_lemmas)))

            fetch_limit = 400 if (rhyme_word and end_n > 1) else 150
            results = query.limit(fetch_limit).all()

            def _base_query(apply_end_col: bool = True, palette: bool = False):
                q = session.query(WordRecord)
                if pos and pos != "any":
                    q = q.filter(WordRecord.pos_primary == pos)
                q = q.filter(
                    WordRecord.rarity_score >= self.spec.min_rarity,
                    WordRecord.rarity_score <= self.spec.max_rarity,
                )
                if "syllables" in constraints:
                    q = q.filter(
                        WordRecord.syllable_count == constraints["syllables"]
                    )
                rk = None
                if rhyme_word and apply_end_col:
                    q, rk = self._apply_end_rhyme_filter(q, rhyme_word, end_n)
                if palette and self._palette_lemmas:
                    q = q.filter(WordRecord.lemma.in_(list(self._palette_lemmas)))
                return q, rk

            # Column miss: drop end-key SQL filter and runtime-match
            if rhyme_word and end_n > 1 and not results:
                runtime_key = runtime_key or self.sound_engine.get_end_span_key(
                    rhyme_word, n=end_n
                )
                query, _ = _base_query(
                    apply_end_col=False, palette=force_palette
                )
                results = query.limit(fetch_limit).all()

            if not results and force_palette and self._palette_lemmas:
                query, rk = _base_query(apply_end_col=(end_n <= 1), palette=False)
                if rk:
                    runtime_key = rk
                results = query.limit(fetch_limit).all()
                if rhyme_word and end_n > 1 and not results:
                    query, _ = _base_query(apply_end_col=False, palette=False)
                    results = query.limit(fetch_limit).all()

            # Runtime end-N filter when DB columns absent/empty
            if rhyme_word and end_n > 1:
                target = runtime_key or self.sound_engine.get_end_span_key(
                    rhyme_word, n=end_n
                )
                if target:
                    col_hit = []
                    if end_n == 2:
                        col_hit = [
                            r for r in results if getattr(r, "end_key_2", None) == target
                        ]
                    elif end_n == 3:
                        col_hit = [
                            r for r in results if getattr(r, "end_key_3", None) == target
                        ]
                    if col_hit:
                        results = col_hit
                    else:
                        results = [
                            r
                            for r in results
                            if self._runtime_end_key_match(r.lemma, target, end_n)
                        ]

            def _passes_hard_tags(word_record) -> bool:
                if self.spec.domain_tags:
                    if not word_record.domain_tags:
                        return False
                    if not any(
                        tag in word_record.domain_tags for tag in self.spec.domain_tags
                    ):
                        return False
                if getattr(self.spec, "imagery_tags", None):
                    if not word_record.imagery_tags:
                        return False
                    if not any(
                        tag in word_record.imagery_tags
                        for tag in self.spec.imagery_tags
                    ):
                        return False
                if self.spec.affect_profile:
                    if not word_record.affect_tags:
                        return False
                    if self.spec.affect_profile not in word_record.affect_tags:
                        return False
                return True

            tagged = []
            for word_record in results:
                if word_record.lemma in exclude_lemmas:
                    continue
                if rhyme_word and word_record.lemma.lower() == rhyme_word.lower():
                    continue
                if _passes_hard_tags(word_record):
                    tagged.append(word_record)

            if tagged:
                return [r.lemma for r in tagged]

            # Soft tag fallback: keep rarity/POS/rhyme, drop tag filters
            soft = [
                r.lemma
                for r in results
                if r.lemma not in exclude_lemmas
                and (not rhyme_word or r.lemma.lower() != rhyme_word.lower())
            ][:50]
            if soft and (
                self.spec.domain_tags
                or getattr(self.spec, "imagery_tags", None)
                or self.spec.affect_profile
            ):
                logger.debug(
                    "tag_filter soft-fallback pos=%s n=%s", pos, len(soft)
                )
                self._last_trace["tag_soft_fallback"] = True
            return soft

    def _rank_candidates(
        self,
        candidates: List[str],
        constraints: Optional[Dict] = None,
    ) -> List[str]:
        """
        Rank by rarity_bias proximity and embedding cosine to motif centroid.

        score = W_RARITY * |rarity - bias| + W_EMB * (1 - cosine) + palette penalty
        Lower is better. When embeddings missing, emb term is 0.5 (neutral).

        Optional: if constraints contain ``expected_stress`` (bit string), boost
        candidates whose stress_pattern matches that prefix.
        """
        if not candidates:
            return []

        bias = self.spec.rarity_bias
        expected = (constraints or {}).get("expected_stress") or ""
        scored: List[Tuple[str, float]] = []
        with get_session() as session:
            for lemma in candidates:
                record = session.query(WordRecord).filter_by(lemma=lemma).first()
                rarity = (
                    record.rarity_score
                    if record and record.rarity_score is not None
                    else 0.5
                )
                rarity_term = abs(rarity - bias)
                emb_term = 0.5
                if self._motif_centroid and record and record.embedding:
                    cos = _cosine(list(record.embedding), self._motif_centroid)
                    emb_term = 1.0 - max(0.0, cos)
                palette_term = 0.0 if lemma in self._palette_lemmas else 1.0
                score = (
                    W_RARITY * rarity_term
                    + W_EMB * emb_term
                    + W_PALETTE * palette_term
                )
                if expected and record and record.stress_pattern:
                    bits = "".join(
                        "1" if c == "1" else "0" for c in record.stress_pattern
                        if c in "012"
                    )
                    if bits and str(expected).startswith(bits):
                        score -= _W_STRESS
                    elif bits:
                        score -= _W_STRESS * stress_fit_score(
                            bits, str(expected)[: len(bits)]
                        )
                scored.append((lemma, score))

        scored.sort(key=lambda x: x[1])
        return [lemma for lemma, _ in scored]

    def _select_with_temperature(self, candidates: List[str]) -> Optional[str]:
        if not candidates:
            return None
        if self.spec.temperature == 0.0:
            return candidates[0]
        if self.spec.temperature >= 1.0:
            return random.choice(candidates)
        n = len(candidates)
        weights = [(1.0 - i / n) ** (1.0 / max(self.spec.temperature, 0.01)) for i in range(n)]
        return random.choices(candidates, weights=weights)[0]

    def find_rhyming_words(
        self,
        rhyme_symbol: str,
        existing_rhymes: Dict[str, str],
        pos: str = None,
        syllables: int = None,
        exclude_lemmas: Optional[Set[str]] = None,
    ) -> List[str]:
        """Find words that rhyme with the anchor for a rhyme symbol."""
        exclude_lemmas = exclude_lemmas or set()
        anchor_word = existing_rhymes.get(rhyme_symbol)
        constraints = {}
        if syllables:
            constraints["syllables"] = syllables

        if not anchor_word:
            return self._rank_candidates(
                self._query_candidates(pos or "noun", constraints, None, exclude_lemmas)
            )

        return self._rank_candidates(
            self._query_candidates(pos or "noun", constraints, anchor_word, exclude_lemmas)
        )


class LineRealizer:
    """Realizes lines from scaffolds."""

    def __init__(
        self,
        spec: GenerationSpec,
        semantic_palette: Dict,
        policy: Optional[SteeringPolicy] = None,
    ):
        self.spec = spec
        self.semantic_palette = semantic_palette
        self.word_selector = WordSelector(spec, semantic_palette)
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()
        self.constraint_model = ConstraintModel(spec.constraint_weights)
        self.policy = policy or self._policy_from_spec(spec)
        self.repairer = LineRepairer(self.policy)
        self.detector = ConflictDetector()

        self.rhyme_assignments: Dict[str, str] = {}
        self.used_end_lemmas: Dict[str, Set[str]] = {}  # symbol -> used end lemmas
        self.all_end_lemmas: Set[str] = set()  # poem-wide end ban (no self-rhyme reuse)
        self.class_keys: Dict[str, str] = {}  # rhyme class_id -> span key
        self.class_anchors: Dict[str, str] = {}  # class_id -> first surface span
        self.rhyme_match_mode: str = "perfect"
        self.line_traces: List[Dict] = []
        self._last_word_traces: List[Dict] = []
        self._poem_scaffold = None  # set in realize_poem

    @staticmethod
    def _policy_from_spec(spec: GenerationSpec) -> SteeringPolicy:
        name = getattr(spec, "steering_policy", None) or "loose_tercet"
        factories = {
            "strict_sonnet": SteeringPolicy.strict_sonnet,
            "loose_tercet": SteeringPolicy.loose_tercet,
            "free_verse": SteeringPolicy.free_verse,
        }
        return factories.get(name, SteeringPolicy.loose_tercet)()

    def realize_line(self, scaffold: LineScaffold, max_iterations: int = None) -> Optional[str]:
        if scaffold.is_refrain and scaffold.refrain_text:
            self._last_word_traces = []
            return scaffold.refrain_text

        template = scaffold.syntactic_template
        if not template:
            logger.warning("No template for line %s", scaffold.line_number)
            self._last_word_traces = []
            return None
        # Dense positional maps: enforce mono-chain length == target
        slots = getattr(scaffold, "rhyme_slots", None) or []
        dense = bool(slots and len(slots) >= scaffold.target_syllables)
        if dense:
            from ..forms.grammar_engine import mono_chain_template

            template = mono_chain_template(scaffold.target_syllables)
            self.word_selector.prefer_large_cohorts = True
        else:
            self.word_selector.prefer_large_cohorts = False

        iterations = max_iterations or self.spec.max_iterations
        if dense:
            iterations = max(iterations, int(iterations * 1.5))
        best_line = None
        best_score = -1.0
        best_traces: List[Dict] = []
        best_pivot = None
        symbol = scaffold.rhyme_symbol
        # Ban ends already used in this rhyme group AND poem-wide (prevents
        # petrichor…petrichor across different symbols / within a line).
        class_exclude: Set[str] = set()
        if symbol and symbol != "null":
            class_exclude |= set(self.used_end_lemmas.get(symbol, set()))
        for slot in getattr(scaffold, "rhyme_slots", None) or []:
            if slot.surface_ban:
                class_exclude |= set(self.used_end_lemmas.get(slot.class_id, set()))
                anchor = self.rhyme_assignments.get(slot.class_id)
                if anchor:
                    class_exclude.add(anchor.lower().split()[-1])
        # Strict: poem-wide unique ends. Loose/free: class-level ban only (fill rate).
        if self.policy.name == "strict_sonnet":
            hard_exclude = set(self.all_end_lemmas) | class_exclude
        else:
            hard_exclude = set(class_exclude)

        for attempt in range(iterations):
            # Soften poem-wide identical ban after half budget under strict
            if (
                self.policy.name == "strict_sonnet"
                and attempt >= max(3, iterations // 2)
            ):
                exclude = set(class_exclude)
            else:
                exclude = set(hard_exclude)

            line, traces = self._generate_candidate_line(
                scaffold, template, exclude, allow_backtrack=True
            )
            if not line:
                continue

            tokens = [t.lower().strip(".,!?;:") for t in line.split()]
            end = tokens[-1] if tokens else ""
            if end in exclude:
                continue
            # Ban end lemma repeating earlier in the same line
            if end and end in tokens[:-1]:
                continue
            if not self._rhyme_ok(line, scaffold):
                continue

            line = self._maybe_repair(line, scaffold)
            pending_pivot = getattr(self.repairer, "last_pivot", None)
            self.repairer.last_pivot = None
            tokens = [t.lower().strip(".,!?;:") for t in line.split()]
            end = tokens[-1] if tokens else ""
            if end in exclude or (end and end in tokens[:-1]):
                continue
            if not self._rhyme_ok(line, scaffold):
                continue

            # Stress gate for non-syllabic under strict policy
            if (
                scaffold.meter_pattern != "syllabic"
                and self.policy.name == "strict_sonnet"
            ):
                analysis = self.meter_engine.analyze_line(
                    line,
                    scaffold.meter_pattern,
                    target_syllables=scaffold.target_syllables,
                )
                min_acc = float(getattr(self.spec, "min_foot_accuracy", 0.55) or 0.55)
                if not self.meter_engine.meets_stress_gate(analysis, min_acc):
                    continue

            # Establishing a rhyme class: require a matchable cohort
            end_tok = line.split()[-1].lower().strip(".,!?;:") if line.split() else ""
            if (
                symbol
                and symbol != "null"
                and symbol not in self.rhyme_assignments
                and end_tok
            ):
                large = self.word_selector._ensure_large_cohort_lemmas(2)
                if end_tok not in large:
                    continue

            score = self._score_line(line, scaffold)
            if score > best_score:
                best_score = score
                best_line = line
                best_traces = traces
                best_pivot = pending_pivot
            if score > 0.8:
                break

        self._last_word_traces = best_traces
        if best_line:
            end = best_line.split()[-1].lower().strip(".,!?;:")
            self.all_end_lemmas.add(end)
            if symbol and symbol != "null":
                self.used_end_lemmas.setdefault(symbol, set()).add(end)
                if symbol not in self.rhyme_assignments:
                    self.rhyme_assignments[symbol] = end
            # Apply pivot only for the accepted line
            if best_pivot:
                cid, new_key, surface = best_pivot
                self.class_keys[cid] = new_key
                if surface:
                    self.class_anchors[cid] = surface
            self._bind_plan_keys(best_line, scaffold)
            logger.debug(
                "Line %s: %s (score=%.2f)",
                scaffold.line_number,
                best_line,
                best_score,
            )

        return best_line

    def _plan_ok(self, line: str, scaffold: LineScaffold) -> bool:
        """Validate line against rhyme_slots / class_keys registry."""
        slots = getattr(scaffold, "rhyme_slots", None) or []
        if not slots:
            return True
        tokens = line.split()
        mode = self.rhyme_match_mode
        aligned = self.sound_engine.align_line_syllables(tokens, mode=mode)
        for slot in slots:
            key = self.sound_engine.line_span_key(
                tokens, slot.syl_start, slot.syl_end, mode=mode
            )
            if not key:
                return False
            surface = " ".join(
                a.lemma
                for a in aligned
                if slot.syl_start <= a.line_syl_i < slot.syl_end
            )
            surface_lemma = surface.split()[-1] if surface else ""
            # Function-word spans: loose policy skips hard match (uncontrollable)
            if (
                surface_lemma in _FUNCTION_LEMMAS
                and self.policy.name != "strict_sonnet"
            ):
                continue
            established = self.class_keys.get(slot.class_id)
            if established is None:
                continue  # will bind on accept
            if key == established:
                if slot.surface_ban and surface:
                    anchor = self.class_anchors.get(slot.class_id, "")
                    if anchor and surface == anchor:
                        return False
                continue
            # mismatch — exact required unless slant/assonance policy applies
            is_end1 = (
                (slot.syl_end - slot.syl_start) == 1
                and slot.syl_end == scaffold.target_syllables
            )
            if mode in ("slant",) or (
                self.policy.allow_slant
                and mode == "perfect"
                and (is_end1 or self.policy.name != "strict_sonnet")
            ):
                sim = self.sound_engine.compare_span(established, key, mode="perfect")
                if sim >= self.sound_engine.slant_rhyme_threshold:
                    continue
                sim_a = self.sound_engine.compare_span(established, key, mode="assonance")
                if sim_a >= 0.99:
                    continue
            if mode == "assonance":
                sim = self.sound_engine.compare_span(established, key, mode="assonance")
                if sim >= 0.99:
                    continue
            return False
        return True

    def _bind_plan_keys(self, line: str, scaffold: LineScaffold) -> None:
        slots = getattr(scaffold, "rhyme_slots", None) or []
        if not slots:
            return
        tokens = line.split()
        mode = self.rhyme_match_mode
        aligned = self.sound_engine.align_line_syllables(tokens, mode=mode)
        for slot in slots:
            surface = " ".join(
                a.lemma
                for a in aligned
                if slot.syl_start <= a.line_syl_i < slot.syl_end
            )
            lemma = surface.split()[-1] if surface else ""
            if slot.surface_ban and lemma:
                self.used_end_lemmas.setdefault(slot.class_id, set()).add(lemma)
            if slot.class_id in self.class_keys:
                continue
            # Do not establish rhyme classes from function words
            if lemma in _FUNCTION_LEMMAS:
                continue
            key = self.sound_engine.line_span_key(
                tokens, slot.syl_start, slot.syl_end, mode=mode
            )
            if not key:
                continue
            # Prefer keys with a usable 1-syl cohort; skip sparse keys so a
            # later content slot can establish a matchable class.
            if self.word_selector._rhyme_cohort_size(key, 1) < 2:
                continue
            self.class_keys[slot.class_id] = key
            self.class_anchors[slot.class_id] = surface
            # Compat: class_id → anchor lemma for annotator
            if slot.class_id not in self.rhyme_assignments and lemma:
                self.rhyme_assignments[slot.class_id] = lemma

    def _rhyme_ok(self, line: str, scaffold: LineScaffold) -> bool:
        """True if plan slots / end rhyme match registry."""
        slots = getattr(scaffold, "rhyme_slots", None) or []
        if slots:
            return self._plan_ok(line, scaffold)

        symbol = scaffold.rhyme_symbol
        if not symbol or symbol == "null":
            return True
        anchor = self.rhyme_assignments.get(symbol)
        if not anchor:
            return True  # first line in group establishes anchor
        words = line.split()
        if not words:
            return False
        idx = self._rhyme_slot_index(scaffold.syntactic_template) if scaffold.syntactic_template else None
        token = words[idx] if idx is not None and idx < len(words) else words[-1]
        token = token.lower().strip(".,!?;:")
        if token == anchor.lower():
            return False
        a_key = self.sound_engine.get_rhyme_key(anchor)
        b_key = self.sound_engine.get_rhyme_key(token)
        if a_key and b_key and a_key == b_key:
            return True
        if self.policy.allow_slant:
            match = self.sound_engine.check_rhyme(anchor, token)
            return bool(match and match.similarity >= self.sound_engine.slant_rhyme_threshold)
        return False

    def _maybe_repair(self, line: str, scaffold: LineScaffold) -> str:
        # Dense positional maps: repair often corrupts mid-slot keys — skip
        slots = getattr(scaffold, "rhyme_slots", None) or []
        if slots and len(slots) >= scaffold.target_syllables:
            return line
        target = {
            "meter": scaffold.meter_pattern,
            "target_syllables": scaffold.target_syllables,
            "rhyme_slots": slots,
            "class_keys": dict(self.class_keys),
            "palette_lemmas": list(self.word_selector._palette_lemmas),
            "allow_breaks": self.policy.allow_breaks,
            "template": scaffold.syntactic_template,
        }
        if scaffold.rhyme_symbol and scaffold.rhyme_symbol in self.rhyme_assignments:
            target["rhyme_word"] = self.rhyme_assignments[scaffold.rhyme_symbol]
        for slot in getattr(scaffold, "rhyme_slots", None) or []:
            if slot.class_id in self.rhyme_assignments:
                target["rhyme_word"] = self.rhyme_assignments[slot.class_id]
                target["rhyme_class"] = slot.class_id
                break

        constraints = self.constraint_model.evaluate_line(line, target)
        utility = self.constraint_model.compute_utility(list(constraints.values()))
        if utility >= 0.7:
            return line

        conflict = self.detector.detect_conflict(line, target)
        if not conflict:
            return line

        repaired = self.repairer.repair_line(line, target, conflict)
        if not repaired:
            return line

        repaired = " ".join(resolve_articles(repaired.split()))
        # Never accept a repair that breaks the rhyme plan (pivot only if still ok)
        if not self._plan_ok(repaired, scaffold):
            self.repairer.last_pivot = None
            return line

        # Reject identical rhyme after repair (used ends + current anchor)
        end = repaired.split()[-1].lower().strip(".,!?;:")
        used = set(self.used_end_lemmas.get(scaffold.rhyme_symbol or "", set()))
        anchor = self.rhyme_assignments.get(scaffold.rhyme_symbol or "")
        if anchor:
            used.add(anchor.lower())
        if scaffold.rhyme_symbol and scaffold.rhyme_symbol != "null" and end in used:
            return line
        return repaired

    def _rhyme_slot_index(self, template) -> Optional[int]:
        """Index of last rhyme-capable content slot (noun/adj/verb)."""
        for i in range(len(template.pattern) - 1, -1, -1):
            if template.pattern[i].pos in RHYME_CAPABLE_POS:
                return i
        return None

    def _end_rhyme_slot(self, scaffold: LineScaffold) -> Optional[RhymeSlot]:
        """Single end-aligned rhyme slot for legacy WordSelector filtering."""
        slots = list(getattr(scaffold, "rhyme_slots", None) or [])
        end_slots = [s for s in slots if s.syl_end == scaffold.target_syllables]
        if len(end_slots) == 1:
            return end_slots[0]
        return None

    def _required_syl_keys_for_span(
        self, scaffold: LineScaffold, syl_start: int, n_syl: int
    ) -> List[Optional[str]]:
        """Per-word-syllable required keys from bound rhyme classes."""
        keys: List[Optional[str]] = [None] * max(1, n_syl)
        for slot in getattr(scaffold, "rhyme_slots", None) or []:
            established = self.class_keys.get(slot.class_id)
            if not established:
                continue
            # Single-syl class membership
            if slot.syl_end - slot.syl_start == 1:
                si = slot.syl_start
                if syl_start <= si < syl_start + n_syl:
                    keys[si - syl_start] = established
            # Multi-syl span exactly covering this word
            elif slot.syl_start == syl_start and slot.syl_end == syl_start + n_syl:
                # Encode as requiring first key component match via joined key later
                keys[0] = established.split(" | ")[0] if " | " in established else established
                if n_syl > 1 and " | " in established:
                    parts = established.split(" | ")
                    for j in range(min(n_syl, len(parts))):
                        keys[j] = parts[j]
        return keys

    def _generate_candidate_line(
        self,
        scaffold: LineScaffold,
        template,
        exclude_end_lemmas: Set[str],
        allow_backtrack: bool = False,
    ) -> Tuple[Optional[str], List[Dict]]:
        words: List[str] = []
        traces: List[Dict] = []
        end_slot = self._end_rhyme_slot(scaffold)
        end_n = 1
        if end_slot is not None:
            # Cap multi-syl end spans; full-line mode is handled via plan keys
            end_n = max(1, min(3, end_slot.syl_end - end_slot.syl_start))
        rhyme_idx = None
        if scaffold.rhyme_symbol or end_slot is not None:
            rhyme_idx = self._rhyme_slot_index(template)

        line_expected = expected_stress_bits(
            scaffold.meter_pattern, scaffold.target_syllables
        )
        stress_cursor = 0
        # Snapshots for bounded content-word backtrack on plan miss
        checkpoints: List[Tuple[List[str], List[Dict], int, int]] = []
        backtracks_left = 3 if allow_backtrack else 0
        slot_excludes: Dict[int, Set[str]] = {}
        i = 0
        pattern = template.pattern

        while i < len(pattern):
            slot = pattern[i]
            constraints = slot.constraints.copy()
            remaining_syllables = scaffold.target_syllables - sum(
                self.meter_engine.get_word_syllables(w) for w in words
            )
            remaining_slots = len(pattern) - len(words)
            if remaining_slots > 0:
                constraints["syllables"] = max(1, round(remaining_syllables / remaining_slots))

            # Pass expected stress slice for this slot (Track M ranking hook)
            if line_expected:
                n_syl = int(constraints.get("syllables") or 1)
                slice_bits = line_expected[stress_cursor : stress_cursor + n_syl]
                if slice_bits:
                    constraints["expected_stress"] = slice_bits

            dense_map = bool(
                getattr(scaffold, "rhyme_slots", None)
                and len(scaffold.rhyme_slots) >= max(3, scaffold.target_syllables)
            )
            rhyme_word = None
            exclude: Set[str] = set(slot_excludes.get(i, set()))
            use_end_n = 1
            establishing_rhyme = False
            if rhyme_idx is not None and i == rhyme_idx and not dense_map:
                # Legacy end-rhyme: use lemma anchor. Dense positional maps use
                # required_syl_keys / class_keys instead (lemma anchors can drift).
                exclude |= set(exclude_end_lemmas)
                if end_slot is not None:
                    use_end_n = end_n
                    rhyme_word = self.rhyme_assignments.get(end_slot.class_id)
                    if not rhyme_word and scaffold.rhyme_symbol:
                        rhyme_word = self.rhyme_assignments.get(scaffold.rhyme_symbol)
                else:
                    rhyme_word = self.rhyme_assignments.get(scaffold.rhyme_symbol)
                establishing_rhyme = not rhyme_word
            elif rhyme_idx is not None and i == rhyme_idx and dense_map:
                exclude |= set(exclude_end_lemmas)
                establishing_rhyme = end_slot is not None and (
                    end_slot.class_id not in self.class_keys
                )
            prev_prefer = self.word_selector.prefer_large_cohorts
            if establishing_rhyme or dense_map:
                self.word_selector.prefer_large_cohorts = True

            syllable_relaxed = False
            # Dense positional maps: force monosyllables so syl-keys can align
            if dense_map or any(
                self.class_keys.get(s.class_id)
                for s in (getattr(scaffold, "rhyme_slots", None) or [])
                if s.syl_start <= stress_cursor < s.syl_end
                or stress_cursor <= s.syl_start < stress_cursor + 2
            ):
                constraints["syllables"] = 1
            n_syl_est = int(constraints.get("syllables") or 1)
            req_keys = self._required_syl_keys_for_span(scaffold, stress_cursor, n_syl_est)
            # Articles: never pick a/an from the DB (that ignores onset).
            # Use "the" or placeholder "a"; resolve_articles fixes a/an later.
            if slot.pos == "article":
                need = next((k for k in (req_keys or []) if k), None)
                if need:
                    # Prefer closed-class match to bound mid-slot key
                    for cand in ("the", "a", "an"):
                        if self.sound_engine.get_rhyme_key(cand) == need:
                            word = cand
                            break
                    else:
                        word = "the" if random.random() < 0.4 else "a"
                else:
                    word = "the" if random.random() < 0.4 else "a"
            else:
                word = self.word_selector.select_word(
                    slot.pos,
                    constraints,
                    rhyme_word=rhyme_word,
                    exclude_lemmas=exclude,
                    end_n=use_end_n,
                    required_syl_keys=req_keys,
                )
                syllable_relaxed = bool(self.word_selector._last_trace.get("syllable_relaxed"))
                if not word and slot.required and "syllables" in constraints:
                    # Soft syllable only — never drop rhyme_key for a rhymed slot
                    loose = {k: v for k, v in constraints.items() if k != "syllables"}
                    word = self.word_selector.select_word(
                        slot.pos,
                        loose,
                        rhyme_word=rhyme_word,
                        exclude_lemmas=exclude,
                        end_n=use_end_n,
                        required_syl_keys=req_keys,
                    )
                    syllable_relaxed = bool(word) or syllable_relaxed
                allow_slant_pick = (
                    rhyme_word
                    and slot.required
                    and (
                        self.rhyme_match_mode in ("slant",)
                        or (
                            self.policy.allow_slant
                            and self.rhyme_match_mode == "perfect"
                            and use_end_n == 1
                        )
                    )
                )
                if not word and allow_slant_pick:
                    # Slant: candidates without exact key, filtered by SoundEngine
                    loose = {k: v for k, v in constraints.items() if k != "syllables"}
                    pool = self.word_selector._query_candidates(
                        slot.pos, loose, rhyme_word=None, exclude_lemmas=exclude
                    )
                    for cand in self.word_selector._rank_candidates(pool, loose):
                        if cand.lower() == rhyme_word.lower():
                            continue
                        match = self.sound_engine.check_rhyme(rhyme_word, cand)
                        if match and match.similarity >= self.sound_engine.slant_rhyme_threshold:
                            word = cand
                            break
                if not word and slot.required and not rhyme_word:
                    loose = {k: v for k, v in constraints.items() if k != "syllables"}
                    word = self.word_selector.select_word(
                        slot.pos,
                        loose,
                        rhyme_word=None,
                        exclude_lemmas=exclude,
                        required_syl_keys=req_keys,
                    )
                    syllable_relaxed = True if word else syllable_relaxed
                # Mid-line bound keys with tiny cohorts: allow lemma reuse
                if (
                    not word
                    and slot.required
                    and any(req_keys or [])
                    and dense_map
                    and i != rhyme_idx
                ):
                    word = self.word_selector.select_word(
                        slot.pos,
                        {"syllables": 1},
                        rhyme_word=None,
                        exclude_lemmas=set(),
                        required_syl_keys=req_keys,
                    )
            if establishing_rhyme or dense_map:
                self.word_selector.prefer_large_cohorts = prev_prefer
            if not word:
                if slot.required:
                    if backtracks_left > 0 and checkpoints:
                        words, traces, stress_cursor, i = checkpoints.pop()
                        backtracks_left -= 1
                        continue
                    return None, []
                i += 1
                continue
            # Never reuse a lemma already in this line for the rhyme slot
            if rhyme_idx is not None and i == rhyme_idx and word.lower() in {
                w.lower() for w in words
            }:
                slot_excludes.setdefault(i, set()).add(word.lower())
                if backtracks_left > 0 and checkpoints:
                    words, traces, stress_cursor, i = checkpoints.pop()
                    backtracks_left -= 1
                    continue
                return None, []
            if slot.pos in RHYME_CAPABLE_POS:
                checkpoints.append(
                    (list(words), list(traces), stress_cursor, i)
                )
                if len(checkpoints) > 4:
                    checkpoints.pop(0)
            words.append(word)
            stress_cursor += self.meter_engine.get_word_syllables(word)
            traces.append(
                {
                    "lemma": word,
                    "pos_expected": slot.pos,
                    "syllable_relaxed": syllable_relaxed,
                }
            )
            # Mid-line plan check: reject early if partial line already breaks
            if (
                allow_backtrack
                and getattr(scaffold, "rhyme_slots", None)
                and slot.pos in RHYME_CAPABLE_POS
            ):
                partial = " ".join(resolve_articles(list(words)))
                covered_ok = True
                for rslot in scaffold.rhyme_slots:
                    if rslot.syl_end > stress_cursor:
                        continue
                    key = self.sound_engine.line_span_key(
                        partial.split(),
                        rslot.syl_start,
                        rslot.syl_end,
                        mode=self.rhyme_match_mode,
                    )
                    # Surface lemma for this slot
                    aligned = self.sound_engine.align_line_syllables(
                        partial.split(), mode=self.rhyme_match_mode
                    )
                    surf = " ".join(
                        a.lemma
                        for a in aligned
                        if rslot.syl_start <= a.line_syl_i < rslot.syl_end
                    )
                    if surf.split() and surf.split()[-1] in _FUNCTION_LEMMAS:
                        continue
                    established = self.class_keys.get(rslot.class_id)
                    if not established or not key:
                        continue
                    if key == established:
                        continue
                    sim = self.sound_engine.compare_span(
                        established, key, mode="perfect"
                    )
                    if (
                        self.policy.allow_slant
                        and sim >= self.sound_engine.slant_rhyme_threshold
                    ):
                        continue
                    if (
                        self.sound_engine.compare_span(
                            established, key, mode="assonance"
                        )
                        >= 0.99
                    ):
                        continue
                    covered_ok = False
                    break
                if not covered_ok:
                    bad = word.lower()
                    words.pop()
                    traces.pop()
                    stress_cursor -= self.meter_engine.get_word_syllables(word)
                    slot_excludes.setdefault(i, set()).add(bad)
                    if backtracks_left > 0 and checkpoints:
                        words, traces, stress_cursor, i = checkpoints.pop()
                        backtracks_left -= 1
                        continue
                    return None, []
            i += 1

        if not words:
            return None, []

        # a/an must match the following word's vowel onset
        words = resolve_articles(words)
        for t, w in zip(traces, words):
            t["lemma"] = w

        # Final identical-rhyme / poem-wide end guard on the rhyme token
        if (scaffold.rhyme_symbol and scaffold.rhyme_symbol != "null") or end_slot:
            idx = rhyme_idx if rhyme_idx is not None else len(words) - 1
            end = words[idx].lower() if 0 <= idx < len(words) else words[-1].lower()
            if end in exclude_end_lemmas:
                return None, []

        line = " ".join(words)
        if allow_backtrack and not self._plan_ok(line, scaffold):
            return None, []
        return line, traces

    def _score_line(self, line: str, scaffold: LineScaffold) -> float:
        scores = []

        analysis = self.meter_engine.analyze_line(
            line,
            scaffold.meter_pattern,
            target_syllables=scaffold.target_syllables,
        )
        if scaffold.meter_pattern == "syllabic":
            meter_score = 1.0 if analysis.is_valid else max(0.0, 1.0 - analysis.syllable_deviation / 3.0)
        else:
            meter_score = 1.0 - analysis.stress_deviation
        scores.append(("meter", meter_score, self.spec.constraint_weights.get("meter", 0.25)))

        syll_deviation = abs(analysis.syllable_count - scaffold.target_syllables)
        syll_score = max(0.0, 1.0 - syll_deviation / 3.0)
        scores.append(("syllables", syll_score, 0.1))

        words = line.split()
        if scaffold.rhyme_symbol and scaffold.rhyme_symbol in self.rhyme_assignments and words:
            anchor = self.rhyme_assignments[scaffold.rhyme_symbol]
            # Score rhyme on last content-capable token when possible
            rhyme_token = words[-1]
            if scaffold.syntactic_template:
                idx = self._rhyme_slot_index(scaffold.syntactic_template)
                if idx is not None and idx < len(words):
                    rhyme_token = words[idx]
            if rhyme_token.lower() == anchor.lower():
                rhyme_score = 0.0  # identical rhyme = fail
            else:
                match = self.sound_engine.check_rhyme(anchor, rhyme_token)
                rhyme_score = match.similarity if match else 0.0
            scores.append(("rhyme", rhyme_score, self.spec.constraint_weights.get("rhyme", 0.25)))

        # Semantic: share of tokens in palette pools
        palette = self.word_selector._palette_lemmas
        if palette and words:
            hit = sum(1 for w in words if w.lower() in palette) / len(words)
            scores.append(("semantics", hit, self.spec.constraint_weights.get("semantics", 0.2)))

        # Affect: fraction of content words matching affect tag
        if self.spec.affect_profile:
            with get_session() as session:
                hits = 0
                checked = 0
                for w in words:
                    rec = session.query(WordRecord).filter_by(lemma=w.lower()).first()
                    if not rec or not rec.affect_tags:
                        continue
                    checked += 1
                    if self.spec.affect_profile in rec.affect_tags:
                        hits += 1
                affect_score = hits / checked if checked else 0.5
            scores.append(("affect", affect_score, self.spec.constraint_weights.get("affect", 0.15)))

        total_weight = sum(weight for _, _, weight in scores)
        if total_weight == 0:
            return 0.0
        return sum(score * weight for _, score, weight in scores) / total_weight

    def _emergency_line(self, scaffold: LineScaffold) -> Optional[str]:
        """Fast fill: monosyllable content chain hitting rhyme class if bound."""
        from ..forms.grammar_engine import mono_chain_template

        n = max(1, int(scaffold.target_syllables or 10))
        # Prefer shorter emergency lines for speed on long meters
        n = min(n, 10)
        template = mono_chain_template(n)
        old_prefer = self.word_selector.prefer_large_cohorts
        self.word_selector.prefer_large_cohorts = True
        try:
            for _ in range(12):
                line, _ = self._generate_candidate_line(
                    scaffold, template, set(), allow_backtrack=False
                )
                if not line:
                    continue
                if self._rhyme_ok(line, scaffold):
                    end = line.split()[-1].lower().strip(".,!?;:")
                    symbol = scaffold.rhyme_symbol
                    self.all_end_lemmas.add(end)
                    if symbol and symbol != "null":
                        self.used_end_lemmas.setdefault(symbol, set()).add(end)
                        if symbol not in self.rhyme_assignments:
                            self.rhyme_assignments[symbol] = end
                    self._bind_plan_keys(line, scaffold)
                    return line
        finally:
            self.word_selector.prefer_large_cohorts = old_prefer
        return None

    def realize_poem(self, scaffold: PoemScaffold) -> List[str]:
        lines: List[str] = []
        self.line_traces = []
        self._poem_scaffold = scaffold
        self.class_keys.clear()
        self.class_anchors.clear()
        plan = getattr(scaffold, "rhyme_plan", None)
        if plan and plan.match_mode:
            self.rhyme_match_mode = plan.match_mode
        elif getattr(self.spec, "rhyme_match_mode", None):
            self.rhyme_match_mode = self.spec.rhyme_match_mode
        self.word_selector.match_mode = self.rhyme_match_mode

        volta_pos = self.semantic_palette.get("volta_position")
        base_pools = set(self.word_selector._palette_lemmas)
        volta_pool = set(self.semantic_palette.get("volta_pool") or [])

        for stanza in scaffold.stanzas:
            for line_scaffold in stanza.lines:
                # Volta palette switch during realization (no post-hoc append)
                if volta_pos and line_scaffold.line_number >= int(volta_pos) and volta_pool:
                    self.word_selector._palette_lemmas = set(volta_pool) | base_pools
                    self.semantic_palette["volta_switched"] = True
                symbol = line_scaffold.rhyme_symbol
                # Anchor is set from the first successfully realized line in the group
                # (do not pre-assign — that caused identical-rhyme leaks).

                line_text = self.realize_line(line_scaffold)
                if not line_text:
                    line_text = self._emergency_line(line_scaffold)
                if not line_text:
                    line_text = f"[Line {line_scaffold.line_number} - generation failed]"

                if line_scaffold.is_refrain and not line_scaffold.refrain_text:
                    line_scaffold.refrain_text = line_text

                self.line_traces.append(
                    {
                        "line_number": line_scaffold.line_number,
                        "rhyme_symbol": symbol,
                        "template": (
                            line_scaffold.syntactic_template.template_id
                            if line_scaffold.syntactic_template
                            else None
                        ),
                        "pos_sequence": (
                            line_scaffold.syntactic_template.get_pos_sequence()
                            if line_scaffold.syntactic_template
                            else []
                        ),
                        "words": list(self._last_word_traces),
                    }
                )
                lines.append(line_text)

        return lines


def main():
    """CLI for line realization testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Line realization utilities")
    parser.add_argument("--form", type=str, default="haiku")
    parser.add_argument("--theme", type=str, default="nature")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    from .generation_spec import create_default_spec
    from .scaffolding import Scaffolder
    from .theme_selector import ThemeSelector

    spec = create_default_spec(form=args.form, theme=args.theme)
    palette = ThemeSelector().build_semantic_palette(spec)
    scaffold = Scaffolder().build_scaffold(spec)
    lines = LineRealizer(spec, palette).realize_poem(scaffold)

    print(f"\nGenerated {args.form}:")
    print("=" * 50)
    for line in lines:
        print(line)
    print("=" * 50)


if __name__ == "__main__":
    main()
