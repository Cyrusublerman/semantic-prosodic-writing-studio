"""
Poem annotator — IPA, stress bits, meter/rhyme metrics, phonetic source flags.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ..database import Phonetics, WordRecord, get_session
from ..forms import MeterEngine, SoundEngine
from ..metrics import MetricsAnalyzer
from .scaffolding import PoemScaffold

logger = logging.getLogger(__name__)


class PoemAnnotator:
    """Build structured phonetic/prosodic annotations for a generated poem."""

    def __init__(self):
        self.meter_engine = MeterEngine()
        self.sound_engine = SoundEngine()
        self.metrics_analyzer = MetricsAnalyzer()

    def annotate(
        self,
        lines: List[str],
        scaffold: Optional[PoemScaffold] = None,
        form_id: Optional[str] = None,
        rhyme_assignments: Optional[Dict[str, str]] = None,
        line_traces: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Build debug_annotations payload.

        Returns dict with per_line, poem_metrics, flags.
        """
        rhyme_assignments = rhyme_assignments or {}
        line_traces = line_traces or []
        traces_by_line = {
            t.get("line_number"): t for t in line_traces if t.get("line_number")
        }
        per_line: List[Dict[str, Any]] = []
        flags: List[str] = []

        line_scaffolds = []
        if scaffold:
            for stanza in scaffold.stanzas:
                line_scaffolds.extend(stanza.lines)

        end_by_symbol: Dict[str, List[str]] = {}

        for i, text in enumerate(lines):
            line_number = i + 1
            sc = line_scaffolds[i] if i < len(line_scaffolds) else None
            meter_name = sc.meter_pattern if sc else "iambic_pentameter"
            target_syllables = sc.target_syllables if sc else None
            rhyme_symbol = sc.rhyme_symbol if sc else None
            is_placeholder = text.startswith("[") and "generation failed" in text
            is_refrain = bool(sc and sc.is_refrain)
            trace = traces_by_line.get(line_number) or {}
            expected_pos = (
                sc.syntactic_template.get_pos_sequence()
                if sc and sc.syntactic_template
                else list(trace.get("pos_sequence") or [])
            )
            word_traces = list(trace.get("words") or [])

            analysis = self.meter_engine.analyze_line(
                text, meter_name, target_syllables=target_syllables
            )
            expected_bits = self._expected_bits(meter_name, analysis.syllable_count, target_syllables)

            words_meta = []
            if not is_placeholder:
                tokens = text.split()
                for ti, token in enumerate(tokens):
                    lemma = token.lower().strip(".,!?;:\"'")
                    if not lemma:
                        continue
                    meta = self._word_phonetics(lemma)
                    wt = word_traces[ti] if ti < len(word_traces) else {}
                    meta["syllable_relaxed"] = bool(wt.get("syllable_relaxed", False))
                    meta["pos_expected"] = wt.get("pos_expected") or (
                        expected_pos[ti] if ti < len(expected_pos) else None
                    )
                    meta["pos_actual"] = self._lookup_pos(lemma)
                    words_meta.append(meta)
                    if meta["phonetic_source"] == "estimated":
                        flags.append(f"estimated_stress:L{line_number}:{lemma}")
                    if not meta.get("ipa"):
                        flags.append(f"missing_ipa:L{line_number}:{lemma}")
                    if (
                        meta.get("pos_expected")
                        and meta.get("pos_actual")
                        and meta["pos_expected"] != "any"
                        and meta["pos_actual"] != meta["pos_expected"]
                    ):
                        flags.append(
                            f"pos_mismatch:L{line_number}:{ti}:"
                            f"{meta['pos_expected']}/{meta['pos_actual']}"
                        )

            end_lemma = words_meta[-1]["lemma"] if words_meta else None
            end_key = words_meta[-1].get("rhyme_key") if words_meta else None

            # Identical rhyme: skip placeholders and intentional villanelle refrains
            if (
                rhyme_symbol
                and rhyme_symbol != "null"
                and end_lemma
                and not is_placeholder
                and not is_refrain
            ):
                end_by_symbol.setdefault(rhyme_symbol, []).append(end_lemma)

            rhyme_code = sc.rhyme_code if sc else None
            slot_keys = []
            if sc and getattr(sc, "rhyme_slots", None):
                for slot in sc.rhyme_slots:
                    slot_keys.append(
                        {
                            "class": slot.class_id,
                            "syl_start": slot.syl_start,
                            "syl_end": slot.syl_end,
                        }
                    )
            if not analysis.is_valid and target_syllables:
                flags.append(f"meter_fail:L{line_number}")

            per_line.append(
                {
                    "line_number": line_number,
                    "text": text,
                    "syllable_count": analysis.syllable_count,
                    "stress_bits": analysis.stress_pattern,
                    "expected_bits": expected_bits,
                    "foot_accuracy": analysis.foot_accuracy,
                    "meter_valid": analysis.is_valid,
                    "meter_pattern": meter_name,
                    "target_syllables": target_syllables,
                    "rhyme_symbol": rhyme_symbol,
                    "end_lemma": end_lemma,
                    "rhyme_key": end_key,
                    "rhyme_code": rhyme_code,
                    "slot_keys": slot_keys,
                    "words": words_meta,
                    "pos_sequence": expected_pos,
                    "template_id": (
                        sc.syntactic_template.template_id
                        if sc and sc.syntactic_template
                        else trace.get("template")
                    ),
                }
            )

        # Identical rhyme + false rhyme (ends in group do not share rhyme_key)
        for symbol, ends in end_by_symbol.items():
            seen = set()
            keys = []
            for lemma in ends:
                if lemma in seen:
                    flags.append(f"identical_rhyme:{symbol}:{lemma}")
                seen.add(lemma)
                key = self.sound_engine.get_rhyme_key(lemma) or ""
                keys.append((lemma, key))
            if len(keys) >= 2:
                anchor_lemma, anchor_key = keys[0]
                for lemma, key in keys[1:]:
                    if not anchor_key or not key or key != anchor_key:
                        match = self.sound_engine.check_rhyme(anchor_lemma, lemma)
                        slant_ok = bool(
                            match
                            and match.similarity
                            >= self.sound_engine.slant_rhyme_threshold
                        )
                        if not slant_ok:
                            flags.append(
                                f"false_rhyme:{symbol}:{anchor_lemma}/{lemma}"
                                f"(keys={anchor_key or '?'}≠{key or '?'})"
                            )

        form_spec = {}
        if scaffold and scaffold.form:
            form_spec = {
                "meter": scaffold.form.meter_pattern,
                "rhyme_pattern": scaffold.form.rhyme_pattern,
            }
        elif form_id:
            form_spec = {"meter": "iambic_pentameter", "rhyme_pattern": form_id}

        metrics = self.metrics_analyzer.analyze_poem(lines, form_spec or None)
        poem_metrics = {
            "R_meter": metrics.meter.score,
            "R_rhyme": metrics.rhyme.score,
            "R_semantic": metrics.semantic.score,
            "R_layers": metrics.layering.score,
            "total": metrics.total_score,
            "meter": {
                "foot_accuracy": metrics.meter.foot_accuracy,
                "stress_deviation": metrics.meter.stress_deviation,
                "stability": metrics.meter.stability,
            },
            "rhyme": {
                "density": metrics.rhyme.density,
                "strictness": metrics.rhyme.strictness,
            },
            "semantic": {
                "theme_coherence": metrics.semantic.theme_coherence,
                "depth": metrics.semantic.depth,
            },
        }

        # Deduplicate flags while preserving order
        seen_flags = set()
        unique_flags = []
        for f in flags:
            if f not in seen_flags:
                seen_flags.add(f)
                unique_flags.append(f)

        return {
            "per_line": per_line,
            "poem_metrics": poem_metrics,
            "flags": unique_flags,
            "rhyme_assignments": rhyme_assignments,
        }

    def _expected_bits(
        self,
        meter_name: str,
        syllable_count: int,
        target_syllables: Optional[int],
    ) -> str:
        if meter_name == "syllabic" or meter_name.startswith("syllabic"):
            n = target_syllables if target_syllables is not None else syllable_count
            return "x" * max(0, n)  # no stress target
        pattern = self.meter_engine.meter_patterns.get(meter_name)
        if not pattern or not pattern.foot_pattern:
            return ""
        n = target_syllables if target_syllables is not None else pattern.expected_syllables
        foot = pattern.foot_pattern
        return (foot * ((n // len(foot)) + 1))[:n]

    def _lookup_pos(self, lemma: str) -> Optional[str]:
        with get_session() as session:
            record = session.query(WordRecord).filter_by(lemma=lemma).first()
            return record.pos_primary if record else None

    def _word_phonetics(self, lemma: str) -> Dict[str, Any]:
        ipa = None
        stress = None
        syllables = None
        rhyme_key = None
        source = "estimated"

        with get_session() as session:
            phon = session.query(Phonetics).filter_by(lemma=lemma).first()
            record = session.query(WordRecord).filter_by(lemma=lemma).first()

            if phon:
                ipa = phon.ipa_us_cmu or phon.ipa_dict_us
                stress = phon.stress_pattern
                syllables = phon.syllable_count
                rhyme_key = phon.rhyme_key
                if ipa or stress:
                    source = "cmu"

            if record:
                if not ipa:
                    ipa = record.ipa_us
                if not stress:
                    stress = record.stress_pattern
                if syllables is None:
                    syllables = record.syllable_count
                if not rhyme_key:
                    rhyme_key = record.rhyme_key
                if source == "estimated" and (record.ipa_us or record.stress_pattern):
                    source = "record"

        if syllables is None:
            syllables = self.meter_engine.get_word_syllables(lemma)
        if not stress:
            stress = "0" * max(1, syllables)
            source = "estimated"

        # Try CMU via sound/meter path for IPA if still missing
        if not ipa:
            try:
                from ..phonetics.ipa_processor import IPAProcessor

                proc = IPAProcessor()
                phones = proc.get_cmu_phones(lemma)
                if phones:
                    ipa = proc.arpabet_to_ipa_convert(phones)
                    if source == "estimated":
                        source = "cmu"
                    if not rhyme_key:
                        rhyme_key = proc.extract_rhyme_key(phones)
                    stress_from_cmu = proc.extract_stress_pattern(phones)
                    if stress_from_cmu:
                        stress = "".join(
                            "1" if c == "1" else "0" for c in stress_from_cmu
                        )
                        source = "cmu"
            except Exception as exc:  # pragma: no cover - optional path
                logger.debug("IPAProcessor lookup failed for %s: %s", lemma, exc)

        return {
            "lemma": lemma,
            "ipa": ipa or "",
            "stress": stress,
            "syllables": syllables,
            "rhyme_key": rhyme_key or "",
            "phonetic_source": source,
        }

    def format_debug_strip(self, annotations: Dict[str, Any]) -> str:
        """Render three-row orthography / IPA / stress strips for CLI."""
        return self.format_columns(annotations)

    def format_columns(self, annotations: Dict[str, Any]) -> str:
        """
        Column analysis: plain text | phonetics | numbers (stress).

        One row per poem line; each cell holds the full line joined.
        """
        per_line = annotations.get("per_line") or []
        rows: List[tuple] = []  # (plain, ipa, nums)

        for line in per_line:
            text = (line.get("text") or "").strip()
            words = line.get("words") or []
            if not words:
                rows.append((text or "(empty)", "-", line.get("stress_bits") or "-"))
                continue

            ipa_parts = []
            stress_parts = []
            for w in words:
                ipa = w.get("ipa") or "?"
                if w.get("phonetic_source") == "estimated":
                    ipa = f"{ipa}*"
                ipa_parts.append(ipa)
                stress = w.get("stress") or "?"
                if w.get("syllable_relaxed"):
                    stress = f"{stress}~"
                stress_parts.append(stress)

            # Prefer concatenated line stress bits when present
            nums = line.get("stress_bits") or "".join(
                s.replace("~", "") for s in stress_parts if s != "?"
            )
            rows.append((text, " ".join(ipa_parts), nums))

        col_plain = max([len("plain text")] + [len(r[0]) for r in rows] + [1])
        col_ipa = max([len("phonetics")] + [len(r[1]) for r in rows] + [1])
        col_num = max([len("numbers")] + [len(r[2]) for r in rows] + [1])

        def row(plain: str, ipa: str, nums: str) -> str:
            return f"{plain:<{col_plain}} | {ipa:<{col_ipa}} | {nums:<{col_num}}"

        chunks: List[str] = [
            row("plain text", "phonetics", "numbers"),
            row("-" * col_plain, "-" * col_ipa, "-" * col_num),
        ]
        for plain, ipa, nums in rows:
            chunks.append(row(plain, ipa, nums))

        # Compact per-line rhyme/meter key (not split into word rows)
        if per_line:
            chunks.append("")
            chunks.append("LINE META (code symbol end key meter syll slots):")
            class_keys = annotations.get("class_keys") or {}
            for line in per_line:
                slots = line.get("slot_keys") or []
                slot_s = ";".join(
                    f"{s.get('class')}:{class_keys.get(s.get('class'), '?')}"
                    for s in slots
                ) or "-"
                chunks.append(
                    f"  L{line.get('line_number')}: "
                    f"code={line.get('rhyme_code') or '-'} "
                    f"{line.get('rhyme_symbol') or '-'} "
                    f"{line.get('end_lemma') or '-'} "
                    f"{line.get('rhyme_key') or '-'} "
                    f"{'OK' if line.get('meter_valid') else 'FAIL'} "
                    f"{line.get('syllable_count')}/{line.get('target_syllables')} "
                    f"slots={slot_s}"
                )

        flags = annotations.get("flags") or []
        if flags:
            chunks.append("")
            chunks.append("FLAGS:")
            for f in flags:
                chunks.append(f"  - {f}")

        metrics = annotations.get("poem_metrics") or {}
        if metrics:
            chunks.append("")
            chunks.append(
                f"METRICS: meter={metrics.get('R_meter', 0):.2f} "
                f"rhyme={metrics.get('R_rhyme', 0):.2f} "
                f"semantic={metrics.get('R_semantic', 0):.2f} "
                f"total={metrics.get('total', 0):.2f}"
            )

        return "\n".join(chunks)
