"""
Main poem generation engine - ties all components together.
"""

from __future__ import annotations

import logging
import uuid
from typing import Dict, List, Optional, Tuple

from ..database import GenerationRun, WordRecord, get_session
from .annotator import PoemAnnotator
from .generation_spec import GenerationSpec
from .line_realizer import LineRealizer
from .scaffolding import Scaffolder
from .theme_selector import ThemeSelector

logger = logging.getLogger(__name__)


class GeneratedPoem:
    """Represents a generated poem with metadata."""

    def __init__(
        self,
        lines: List[str],
        spec: GenerationSpec,
        run_id: str,
        metrics: Dict = None,
        annotations: Dict = None,
    ):
        self.lines = lines
        self.spec = spec
        self.run_id = run_id
        self.metrics = metrics or {}
        self.annotations = annotations or {}

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    def __str__(self):
        return self.text

    def to_dict(self) -> Dict:
        return {
            "run_id": self.run_id,
            "text": self.text,
            "lines": self.lines,
            "spec": self.spec.to_dict(),
            "metrics": self.metrics,
            "annotations": self.annotations,
        }


class PoemGenerator:
    """Main poem generation engine."""

    def __init__(self):
        self.theme_selector = ThemeSelector()
        self.scaffolder = Scaffolder()
        self.annotator = PoemAnnotator()
        self._last_device_rates: Dict = {}
        self._last_motif_hit_rate: float = 0.0

    def generate(self, spec: GenerationSpec = None, **kwargs) -> GeneratedPoem:
        if spec is None:
            spec = GenerationSpec()

        for key, value in kwargs.items():
            if hasattr(spec, key):
                setattr(spec, key, value)

        errors = spec.validate()
        if errors:
            raise ValueError(f"Invalid generation spec: {errors}")

        attempts = max(1, int(getattr(spec, "optimize_attempts", 1) or 1))
        if attempts == 1:
            return self._generate_once(spec)

        # Multi-candidate optimization loop: keep the poem with the best
        # composite score (metrics total minus hard rhyme/identity penalties).
        best: Optional[GeneratedPoem] = None
        best_score = float("-inf")
        for i in range(attempts):
            candidate = self._generate_once(spec)
            score = self._optimization_score(candidate)
            logger.info(
                "Optimize attempt %s/%s score=%.3f run=%s",
                i + 1,
                attempts,
                score,
                candidate.run_id,
            )
            if score > best_score:
                best_score = score
                best = candidate
                # Early stop on a clean high-scoring candidate
                if score >= 0.75 and not self._has_rhyme_failures(candidate):
                    break
        assert best is not None
        best.annotations["optimize"] = {
            "attempts": attempts,
            "best_score": best_score,
        }
        return best

    def _generate_once(self, spec: GenerationSpec) -> GeneratedPoem:
        run_id = str(uuid.uuid4())[:8]
        logger.info("Starting generation run %s", run_id)
        logger.info(
            "Form: %s, Theme: %s, Rarity: %s, Policy: %s",
            spec.form,
            spec.theme,
            spec.rarity_bias,
            spec.steering_policy,
        )

        semantic_palette = self.theme_selector.build_semantic_palette(spec)
        # Track S: motif_density rides on the palette for device/global consumers
        semantic_palette["motif_density"] = spec.motif_density

        scaffold = self.scaffolder.build_scaffold(spec)

        # Merge form.device_profile_defaults then let spec override
        form = scaffold.form
        defaults = getattr(form, "device_profile_defaults", None) or {}
        if defaults:
            merged = dict(defaults)
            merged.update(spec.device_profile or {})
            spec.device_profile = merged

        # After scaffold: attach volta metadata when form declares a turn
        volta_rule = (getattr(form, "special_rules", None) or {}).get("volta") or {}
        volta_position = volta_rule.get("position")
        if volta_position is not None:
            semantic_palette["volta"] = dict(volta_rule)
            semantic_palette["volta_position"] = volta_position

        realizer = LineRealizer(spec, semantic_palette)
        lines = realizer.realize_poem(scaffold)

        if spec.device_profile:
            lines = self._apply_devices(lines, spec, semantic_palette)

        lines = self._global_pass(lines, spec, semantic_palette, realizer)
        # Track S call site: apply volta contrast from palette['volta_pool']
        # (Track D owns fuller _global_pass rewrite; keep shift as a helper).
        lines, volta_applied = self._apply_volta_shift(
            lines, semantic_palette, volta_position
        )

        annotations = self.annotator.annotate(
            lines,
            scaffold=scaffold,
            form_id=spec.form,
            rhyme_assignments=realizer.rhyme_assignments,
            line_traces=realizer.line_traces,
        )
        annotations["semantic_palette"] = {
            "theme_concepts": semantic_palette.get("theme_concepts", []),
            "motifs": semantic_palette.get("motifs", []),
            "bridges": semantic_palette.get("metaphor_bridges", []),
            "volta_pool": semantic_palette.get("volta_pool", []),
            "motif_density": semantic_palette.get("motif_density"),
            "volta": semantic_palette.get("volta"),
            "volta_position": semantic_palette.get("volta_position"),
        }
        if volta_position is not None:
            annotations["volta_position"] = volta_position
        annotations["volta_applied"] = volta_applied
        annotations["line_traces"] = realizer.line_traces
        annotations["device_rates"] = getattr(self, "_last_device_rates", {}) or {}
        annotations["motif_hit_rate"] = float(
            getattr(self, "_last_motif_hit_rate", 0.0) or 0.0
        )
        annotations["class_keys"] = dict(getattr(realizer, "class_keys", {}) or {})
        if getattr(scaffold, "rhyme_plan", None):
            annotations["rhyme_plan"] = {
                "source": scaffold.rhyme_plan.source,
                "match_mode": scaffold.rhyme_plan.match_mode,
                "line_codes": dict(scaffold.rhyme_plan.line_codes),
                "slot_count": len(scaffold.rhyme_plan.slots),
            }

        poem = GeneratedPoem(
            lines=lines,
            spec=spec,
            run_id=run_id,
            metrics=annotations.get("poem_metrics", {}),
            annotations=annotations,
        )

        if not spec.debug_mode:
            self._save_generation_run(poem)

        logger.info("Generation complete: %s", run_id)
        return poem

    def _apply_volta_shift(
        self,
        lines: List[str],
        semantic_palette: Dict,
        volta_position: Optional[int] = None,
    ) -> Tuple[List[str], bool]:
        """
        In-line volta contrast: substitute a non-final content token with volta_pool.
        Never append tokens (that breaks end rhyme).
        """
        if volta_position is None:
            volta_position = semantic_palette.get("volta_position")
            if volta_position is None:
                volta = semantic_palette.get("volta") or {}
                volta_position = volta.get("position")
        if volta_position is None or not lines:
            return lines, bool(semantic_palette.get("volta_switched"))

        # Palette switch during realize is preferred; mark applied if switched
        if semantic_palette.get("volta_switched"):
            return lines, True

        pool = semantic_palette.get("volta_pool") or []
        if not pool:
            return lines, False

        idx = int(volta_position) - 1
        if idx < 0 or idx >= len(lines):
            return lines, False
        if lines[idx].startswith("["):
            return lines, False

        seed = str(pool[0])
        if seed.lower() in lines[idx].lower():
            return lines, True

        out = list(lines)
        out[idx] = self._substitute_nonfinal(out[idx], seed)
        return out, True

    @staticmethod
    def _substitute_nonfinal(line: str, seed: str) -> str:
        """Replace a non-final content word with seed; preserve end token."""
        from ..forms.grammar_engine import resolve_articles

        words = line.split()
        if len(words) < 2:
            return line
        closed = {"the", "a", "an", "of", "in", "on", "to", "and", "or", "but"}
        # Prefer middle content index
        candidates = [
            i
            for i in range(0, len(words) - 1)
            if words[i].lower().strip(".,!?;:") not in closed
        ]
        if not candidates:
            return line
        i = candidates[len(candidates) // 2]
        words[i] = seed
        return " ".join(resolve_articles(words))

    @staticmethod
    def _has_rhyme_failures(poem: GeneratedPoem) -> bool:
        flags = poem.annotations.get("flags") or []
        return any(
            f.startswith("identical_rhyme") or f.startswith("false_rhyme")
            for f in flags
        )

    def _optimization_score(self, poem: GeneratedPoem) -> float:
        base = float((poem.metrics or {}).get("total") or 0.0)
        flags = poem.annotations.get("flags") or []
        failed_lines = sum(
            1 for ln in poem.lines if ln.startswith("[") and "generation failed" in ln
        )
        identical = sum(1 for f in flags if f.startswith("identical_rhyme"))
        false_rhyme = sum(1 for f in flags if f.startswith("false_rhyme"))
        meter_fails = sum(1 for f in flags if f.startswith("meter_fail"))
        devices = (poem.annotations.get("device_rates") or {})
        device_shortfall = 0.0
        profile = poem.spec.device_profile or {}
        for key, target in profile.items():
            if not key.endswith("_rate"):
                continue
            short = key.replace("_rate", "")
            got = float(devices.get(short, 0.0) or 0.0)
            device_shortfall += max(0.0, float(target or 0) - got)
        motif_density = float(getattr(poem.spec, "motif_density", 0) or 0)
        motif_hits = float((poem.annotations.get("motif_hit_rate") or 0.0))
        motif_shortfall = max(0.0, motif_density - motif_hits)
        return (
            base
            - 0.35 * failed_lines
            - 0.25 * identical
            - 0.30 * false_rhyme
            - 0.20 * meter_fails
            - 0.15 * motif_shortfall
            - 0.10 * device_shortfall
        )

    def _apply_devices(
        self, lines: List[str], spec: GenerationSpec, semantic_palette: Dict
    ) -> List[str]:
        """Enforce device_profile rates + ensure motif lemma presence."""
        from .devices import DeviceEnforcer

        motif_words = []
        for key in ("motif_words", "theme_words", "lemmas", "word_pools"):
            values = semantic_palette.get(key) if isinstance(semantic_palette, dict) else None
            if isinstance(values, dict):
                for v in values.values():
                    motif_words.extend(list(v)[:8])
            elif values:
                motif_words.extend(list(values)[:8])

        enforcer = DeviceEnforcer(spec.device_profile or {})
        out = enforcer.apply(lines, motif_lemmas=motif_words)
        self._last_device_rates = enforcer.rates()

        density = float(getattr(spec, "motif_density", 0) or 0)
        motif_words = [str(w) for w in motif_words if w]
        if motif_words and density > 0:
            def _hit_rate(lines_out: List[str]) -> float:
                joined = " ".join(lines_out).lower()
                hits = sum(1 for w in motif_words[:8] if w.lower() in joined)
                return min(1.0, hits / max(1, len(motif_words[:8])))

            self._last_motif_hit_rate = _hit_rate(out)
            # Inject motif lemmas until density target roughly met (non-final only)
            seed_i = 0
            guard = 0
            while self._last_motif_hit_rate < density * 0.5 and guard < len(out):
                seed = str(motif_words[seed_i % len(motif_words)])
                seed_i += 1
                placed = False
                for i in range(len(out) - 1, -1, -1):
                    if out[i].strip() and not out[i].startswith("["):
                        if seed.lower() not in out[i].lower():
                            out[i] = self._substitute_nonfinal(out[i], seed)
                            placed = True
                            break
                if not placed:
                    break
                self._last_motif_hit_rate = _hit_rate(out)
                guard += 1
        else:
            self._last_motif_hit_rate = 0.0
        return out

    def _global_pass(
        self,
        lines: List[str],
        spec: GenerationSpec,
        semantic_palette: Dict,
        realizer: LineRealizer,
    ) -> List[str]:
        """
        Global pass: class consistency, motif coverage (in-line), diversity cap.
        Never append paren seeds or alter end surfaces for motif.
        """
        from ..forms.grammar_engine import resolve_articles

        # Detect identical end lemmas across poem (any rhyme group)
        end_counts: Dict[str, List[int]] = {}
        for i, line in enumerate(lines):
            if line.startswith("["):
                continue
            parts = line.split()
            if not parts:
                continue
            end = parts[-1].lower().strip(".,!?;:")
            end_counts.setdefault(end, []).append(i)

        pool_words: List[str] = []
        pools = semantic_palette.get("word_pools") or []
        if isinstance(pools, dict):
            for words in pools.values():
                pool_words.extend(words)
        else:
            pool_words.extend(list(pools))
        for key in ("motif_words", "theme_words"):
            extra = semantic_palette.get(key) or []
            if isinstance(extra, (list, tuple)):
                pool_words.extend(list(extra))

        updated = list(lines)
        banned = set(end_counts.keys())
        for end, indices in end_counts.items():
            if len(indices) < 2:
                continue
            for idx in indices[1:]:
                parts = updated[idx].split()
                if not parts:
                    continue
                replacement = self._pick_substitute(
                    end, pool_words, realizer, exclude=banned
                )
                if replacement and replacement.lower() not in banned:
                    parts[-1] = replacement
                    updated[idx] = " ".join(resolve_articles(parts))
                    banned.add(replacement.lower())
                    logger.debug(
                        "Global pass: replaced identical end '%s' -> '%s' on line %s",
                        end,
                        replacement,
                        idx + 1,
                    )

        # Motif coverage via in-line (non-final) substitute — no paren seeds
        density = float(getattr(spec, "motif_density", 0) or 0)
        joined = " ".join(updated).lower()
        if pool_words and density > 0:
            motif = [str(w) for w in pool_words[:12]]
            hits = sum(1 for w in motif if w.lower() in joined)
            rate = hits / max(1, len(motif))
            if rate < density * 0.5:
                seed = motif[0]
                for i in range(len(updated)):
                    if updated[i].startswith("[") or not updated[i].strip():
                        continue
                    if seed.lower() not in updated[i].lower():
                        updated[i] = self._substitute_nonfinal(updated[i], seed)
                        break

        # Diversity cap: non-motif content repeats across poem
        motif_set = {w.lower() for w in pool_words}
        content_counts: Dict[str, List[Tuple[int, int]]] = {}
        closed = {"the", "a", "an", "of", "in", "on", "to", "and", "or", "but"}
        for i, line in enumerate(updated):
            if line.startswith("["):
                continue
            parts = line.split()
            for j, tok in enumerate(parts[:-1]):  # never touch final
                clean = tok.lower().strip(".,!?;:")
                if clean in closed or clean in motif_set:
                    continue
                content_counts.setdefault(clean, []).append((i, j))
        for lemma, locs in content_counts.items():
            if len(locs) < 3:
                continue
            for i, j in locs[2:]:
                parts = updated[i].split()
                if j >= len(parts) - 1:
                    continue
                alt = self._pick_substitute(
                    lemma, pool_words, realizer, exclude={lemma} | banned
                )
                if alt and alt.lower() != lemma:
                    parts[j] = alt
                    updated[i] = " ".join(resolve_articles(parts))

        return updated

    def _pick_substitute(
        self,
        original: str,
        pool_words: List[str],
        realizer: LineRealizer,
        exclude: set,
    ) -> Optional[str]:
        rhyme_key = realizer.sound_engine.get_rhyme_key(original)
        candidates = []
        with get_session() as session:
            query = session.query(WordRecord).filter(
                WordRecord.pos_primary == "noun",
                WordRecord.rarity_score >= realizer.spec.min_rarity,
                WordRecord.rarity_score <= realizer.spec.max_rarity,
            )
            if rhyme_key:
                query = query.filter(WordRecord.rhyme_key == rhyme_key)
            for rec in query.limit(40).all():
                if rec.lemma.lower() not in exclude and rec.lemma.lower() != original:
                    candidates.append(rec.lemma)
        if not candidates and pool_words:
            candidates = [w for w in pool_words if w.lower() not in exclude]
        if not candidates:
            return None
        return realizer.word_selector._select_with_temperature(
            realizer.word_selector._rank_candidates(candidates)
        )

    def _save_generation_run(self, poem: GeneratedPoem):
        try:
            with get_session() as session:
                run = GenerationRun(
                    run_id=poem.run_id,
                    input_spec=poem.spec.to_dict(),
                    form_id=poem.spec.form,
                    theme=poem.spec.theme,
                    parameter_snapshot=poem.spec.to_dict(),
                    poem_text=poem.text,
                    debug_annotations=poem.annotations,
                    metrics=poem.metrics,
                )
                session.add(run)
            logger.info("Saved generation run %s to database", poem.run_id)
        except Exception as e:
            logger.error("Failed to save generation run: %s", e)

    def generate_batch(self, spec: GenerationSpec, count: int = 5) -> List[GeneratedPoem]:
        poems = []
        for i in range(count):
            logger.info("Generating poem %s/%s", i + 1, count)
            try:
                poems.append(self.generate(spec))
            except Exception as e:
                logger.error("Failed to generate poem %s: %s", i + 1, e)
        return poems

    def list_forms(self) -> List[str]:
        return self.scaffolder.form_library.list_forms()

    def get_form_info(self, form_id: str) -> Dict:
        form = self.scaffolder.form_library.get_form(form_id)
        if not form:
            return {}
        return {
            "form_id": form.form_id,
            "name": form.name,
            "description": form.description,
            "total_lines": form.total_lines,
            "rhyme_pattern": form.rhyme_pattern,
            "meter_pattern": form.meter_pattern,
        }


def main():
    """CLI for poem generation."""
    import argparse

    parser = argparse.ArgumentParser(description="WordRare Poem Generator")
    parser.add_argument("--form", type=str, default="haiku")
    parser.add_argument("--theme", type=str)
    parser.add_argument("--rarity", type=float, default=0.5)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--list-forms", action="store_true")
    parser.add_argument(
        "--preset",
        choices=["melancholic_nature", "joyful_simple", "mysterious_archaic"],
    )
    parser.add_argument(
        "--policy",
        choices=["strict_sonnet", "loose_tercet", "free_verse"],
        default="loose_tercet",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print plain|phonetics|numbers columns and skip DB persist",
    )
    parser.add_argument(
        "--optimize",
        type=int,
        default=1,
        metavar="N",
        help="Generate N candidates and keep the best (rhyme-penalized score)",
    )
    parser.add_argument(
        "--rhyme-span",
        type=str,
        default=None,
        help="end:1|end:2|end:3|line",
    )
    parser.add_argument(
        "--rhyme-map",
        type=str,
        default=None,
        help="Path to JSON file with rhyme_map object",
    )
    parser.add_argument(
        "--rhyme-coalesce",
        action="store_true",
        help="Coalesce consecutive identical rhyme-map letters into spans",
    )
    parser.add_argument(
        "--rhyme-match",
        choices=["perfect", "slant", "assonance"],
        default=None,
    )
    parser.add_argument("--motif-density", type=float, default=None)
    parser.add_argument(
        "--devices",
        type=str,
        default=None,
        help="JSON object of device rates, e.g. '{\"alliteration_rate\":0.5}'",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    generator = PoemGenerator()

    if args.list_forms:
        print("\nAvailable Poetic Forms:")
        for form_id in generator.list_forms():
            info = generator.get_form_info(form_id)
            print(f"  {form_id}: {info.get('name', 'Unknown')}")
        return

    if args.preset == "melancholic_nature":
        spec = GenerationSpec.preset_melancholic_nature()
    elif args.preset == "joyful_simple":
        spec = GenerationSpec.preset_joyful_simple()
    elif args.preset == "mysterious_archaic":
        spec = GenerationSpec.preset_mysterious_archaic()
    else:
        spec = GenerationSpec(
            form=args.form, theme=args.theme, rarity_bias=args.rarity
        )

    spec.steering_policy = args.policy
    spec.optimize_attempts = max(1, int(args.optimize))
    if args.motif_density is not None:
        spec.motif_density = args.motif_density
    if args.rhyme_match:
        spec.rhyme_match_mode = args.rhyme_match
    if args.rhyme_coalesce:
        spec.rhyme_coalesce_runs = True
    if args.rhyme_span:
        raw = args.rhyme_span.strip().lower()
        if raw == "line":
            spec.rhyme_span = {"mode": "line", "match_mode": args.rhyme_match or "perfect"}
        elif raw.startswith("end:"):
            n = int(raw.split(":", 1)[1])
            spec.rhyme_span = {
                "mode": "end",
                "syllables": n,
                "match_mode": args.rhyme_match or "perfect",
            }
    if args.rhyme_map:
        import json
        from pathlib import Path

        data = json.loads(Path(args.rhyme_map).read_text())
        spec.rhyme_map = data.get("rhyme_map", data)
    if args.devices:
        import json

        spec.device_profile = json.loads(args.devices)
    if args.debug:
        spec.debug_mode = True
        spec.include_annotations = True

    if args.count == 1:
        poem = generator.generate(spec)
        print("\n" + "=" * 60)
        print(poem.text)
        print("=" * 60)
        print(f"\nRun ID: {poem.run_id}")
        print(f"Form: {spec.form}")
        print(f"Theme: {spec.theme}")
        print(f"Rarity: {spec.rarity_bias}")
        if poem.annotations.get("optimize"):
            opt = poem.annotations["optimize"]
            print(
                f"Optimize: attempts={opt.get('attempts')} "
                f"best_score={opt.get('best_score', 0):.3f}"
            )
        if args.debug or spec.include_annotations:
            print("\n" + "-" * 60)
            print("ANALYSIS  (plain text | phonetics | numbers)")
            print("-" * 60)
            print(generator.annotator.format_columns(poem.annotations))
    else:
        poems = generator.generate_batch(spec, count=args.count)
        for i, poem in enumerate(poems, 1):
            print(f"\n{'=' * 60}")
            print(f"Poem {i}/{args.count} (ID: {poem.run_id})")
            print("=" * 60)
            print(poem.text)
            if args.debug:
                print(generator.annotator.format_columns(poem.annotations))


if __name__ == "__main__":
    main()
