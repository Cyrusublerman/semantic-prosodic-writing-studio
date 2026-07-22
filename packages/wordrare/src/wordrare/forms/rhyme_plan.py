"""
RhymePlan: compile form/spec rhyme authoring into enforceable syllable slots.

Precedence: rhyme_spans > rhyme_map > (rhyme_pattern + rhyme_span).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple


NULL_CHARS = frozenset({"x", "-", "0", ".", "null", "none", ""})


@dataclass
class RhymeSlot:
    """One rhyme constraint on a line-level syllable span."""

    line: int  # 1-indexed
    syl_start: int  # inclusive
    syl_end: int  # exclusive
    class_id: str
    surface_ban: bool = True

    def __post_init__(self):
        if self.syl_end < self.syl_start:
            raise ValueError(f"bad span {self.syl_start}:{self.syl_end}")


@dataclass
class RhymePlan:
    """Compiled rhyme constraints for a poem."""

    slots: List[RhymeSlot] = field(default_factory=list)
    match_mode: str = "perfect"  # perfect | slant | assonance
    line_codes: Dict[int, str] = field(default_factory=dict)
    source: str = "legacy"  # legacy | map | spans | hybrid

    def slots_for_line(self, line: int) -> List[RhymeSlot]:
        return [s for s in self.slots if s.line == line]

    def classes(self) -> Dict[str, List[RhymeSlot]]:
        out: Dict[str, List[RhymeSlot]] = {}
        for s in self.slots:
            out.setdefault(s.class_id, []).append(s)
        return out


def _parse_span_cfg(raw: Optional[Dict]) -> Dict[str, Any]:
    raw = raw or {}
    mode = (raw.get("mode") or "end").lower()
    syllables = raw.get("syllables", 1)
    if syllables == "line" or mode == "line":
        mode = "line"
        syllables = None
    else:
        syllables = int(syllables or 1)
    match_mode = (raw.get("match_mode") or "perfect").lower()
    return {"mode": mode, "syllables": syllables, "match_mode": match_mode}


def _tokenize_code_line(line: str, null_char: str = "x") -> List[str]:
    line = (line or "").strip()
    if not line:
        return []
    if " " in line:
        return [t for t in line.split() if t]
    return list(line)


def _is_null(token: str, null_char: str) -> bool:
    t = token.lower()
    return t in NULL_CHARS or t == null_char.lower()


def compile_from_legacy(
    line_symbols: Sequence[Optional[str]],
    line_targets: Sequence[int],
    rhyme_span: Optional[Dict] = None,
    match_mode: Optional[str] = None,
) -> RhymePlan:
    """Compile one letter per line + end/line span into slots."""
    cfg = _parse_span_cfg(rhyme_span)
    if match_mode:
        cfg["match_mode"] = match_mode
    slots: List[RhymeSlot] = []
    codes: Dict[int, str] = {}
    for i, sym in enumerate(line_symbols):
        line_no = i + 1
        target = line_targets[i] if i < len(line_targets) else 10
        if sym is None or str(sym).lower() in NULL_CHARS:
            codes[line_no] = "x" * max(1, target)
            continue
        class_id = str(sym)
        if cfg["mode"] == "line":
            start, end = 0, max(1, target)
            code = class_id * max(1, target)
        else:
            n = max(1, min(int(cfg["syllables"] or 1), max(1, target)))
            start, end = max(0, target - n), target
            code = ("x" * start) + (class_id * (end - start))
            if len(code) < target:
                code = code + ("x" * (target - len(code)))
            code = code[:target]
        codes[line_no] = code
        slots.append(
            RhymeSlot(
                line=line_no,
                syl_start=start,
                syl_end=end,
                class_id=class_id,
                surface_ban=True,
            )
        )
    return RhymePlan(
        slots=slots,
        match_mode=cfg["match_mode"],
        line_codes=codes,
        source="legacy",
    )


def compile_from_map(
    rhyme_map: Dict[str, Any],
    line_targets: Sequence[int],
) -> RhymePlan:
    """Compile per-syllable code strings into slots."""
    null_char = str(rhyme_map.get("null_char") or "x")
    coalesce = bool(rhyme_map.get("coalesce_runs"))
    match_mode = str(rhyme_map.get("match_mode") or "perfect").lower()
    lines = rhyme_map.get("lines_tokens") or rhyme_map.get("lines") or []
    slots: List[RhymeSlot] = []
    codes: Dict[int, str] = {}

    for i, raw in enumerate(lines):
        line_no = i + 1
        target = line_targets[i] if i < len(line_targets) else 0
        if isinstance(raw, list):
            tokens = [str(t) for t in raw]
        else:
            tokens = _tokenize_code_line(str(raw), null_char)
        if target and len(tokens) != target:
            raise ValueError(
                f"rhyme_map line {line_no}: len {len(tokens)} != target_syllables {target}"
            )
        codes[line_no] = (
            " ".join(tokens) if any(len(t) > 1 for t in tokens) else "".join(tokens)
        )

        if coalesce:
            j = 0
            while j < len(tokens):
                tok = tokens[j]
                if _is_null(tok, null_char):
                    j += 1
                    continue
                k = j + 1
                while k < len(tokens) and tokens[k] == tok:
                    k += 1
                slots.append(
                    RhymeSlot(
                        line=line_no,
                        syl_start=j,
                        syl_end=k,
                        class_id=tok,
                        surface_ban=(k - j) > 1 or True,
                    )
                )
                j = k
        else:
            for j, tok in enumerate(tokens):
                if _is_null(tok, null_char):
                    continue
                slots.append(
                    RhymeSlot(
                        line=line_no,
                        syl_start=j,
                        syl_end=j + 1,
                        class_id=tok,
                        surface_ban=False,
                    )
                )

    return RhymePlan(
        slots=slots, match_mode=match_mode, line_codes=codes, source="map"
    )


def compile_from_explicit_spans(
    rhyme_spans: Sequence[Dict[str, Any]],
    match_mode: str = "perfect",
    line_targets: Optional[Sequence[int]] = None,
) -> RhymePlan:
    slots: List[RhymeSlot] = []
    codes: Dict[int, List[str]] = {}
    for sp in rhyme_spans:
        line = int(sp["line"])
        start = int(sp["syl_start"])
        end = int(sp["syl_end"])
        class_id = str(sp["class"])
        target = (
            line_targets[line - 1]
            if line_targets and 0 <= line - 1 < len(line_targets)
            else end
        )
        if line not in codes:
            codes[line] = ["x"] * max(target, end)
        for i in range(start, end):
            if i < len(codes[line]):
                codes[line][i] = class_id
        slots.append(
            RhymeSlot(
                line=line,
                syl_start=start,
                syl_end=end,
                class_id=class_id,
                surface_ban=True,
            )
        )
    line_codes = {ln: "".join(toks) for ln, toks in codes.items()}
    return RhymePlan(
        slots=slots,
        match_mode=match_mode,
        line_codes=line_codes,
        source="spans",
    )


def compile_rhyme_plan(
    *,
    line_symbols: Optional[Sequence[Optional[str]]] = None,
    line_targets: Optional[Sequence[int]] = None,
    rhyme_span: Optional[Dict] = None,
    rhyme_map: Optional[Dict] = None,
    rhyme_spans: Optional[Sequence[Dict]] = None,
    match_mode: Optional[str] = None,
    coalesce_runs: Optional[bool] = None,
) -> RhymePlan:
    """
    Compile with precedence: rhyme_spans > rhyme_map > legacy pattern+span.
    """
    targets = list(line_targets or [])
    if rhyme_spans:
        return compile_from_explicit_spans(
            rhyme_spans, match_mode=match_mode or "perfect", line_targets=targets
        )
    if rhyme_map:
        rm = dict(rhyme_map)
        if coalesce_runs is not None:
            rm["coalesce_runs"] = coalesce_runs
        if match_mode:
            rm["match_mode"] = match_mode
        return compile_from_map(rm, targets)
    return compile_from_legacy(
        line_symbols or [],
        targets,
        rhyme_span=rhyme_span,
        match_mode=match_mode,
    )
