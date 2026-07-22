"""Full D007 EvaluationBundle builder for revision candidates."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from spws_contracts_core.domain import EvaluationBundle, EvaluationResult
from spws_domain.ids import new_id

ALL_CRITERIA = (
    "semantic_retention",
    "grammatical_acceptability",
    "pronunciation_confidence",
    "syllable_fit",
    "stress_metre_fit",
    "rhyme_fit",
    "register_voice",
    "repetition_motif",
    "source_grounding",
    "quotation_risk",
    "constraint_compliance",
    "human_preference",
)

_WORD_RE = re.compile(r"[A-Za-z']+")


def _label(value: float | None, measured: bool) -> str:
    if not measured:
        return "inferred"
    return "measured"


def _cosine_retention(orig: str, revised: str, config: Any) -> tuple[float, str]:
    if config is not None:
        try:
            from spws_semantics import MeaningGauge
            from spws_semantics.similarity import cosine

            gauge = MeaningGauge.from_config(config)
            a = gauge.embedder.encode(orig)
            b = gauge.embedder.encode(revised)
            return float(cosine(a, b)), "measured"
        except Exception:
            pass
    shared = len(set(orig.lower().split()) & set(revised.lower().split()))
    total = max(len(set(orig.lower().split()) | set(revised.lower().split())), 1)
    return shared / float(total), "inferred"


def _grammatical_acceptability(text: str) -> tuple[float, str]:
    tokens = text.split()
    if not tokens:
        return 0.0, "measured"
    alpha = sum(1 for t in tokens if any(c.isalpha() for c in t))
    punct_ok = not text.strip().startswith((",", ";", "."))
    doubles = any(tokens[i] == tokens[i + 1] for i in range(len(tokens) - 1))
    score = (alpha / float(len(tokens))) * (1.0 if punct_ok else 0.7) * (0.55 if doubles else 1.0)
    return float(max(0.0, min(1.0, score))), "measured"


def _pronunciation_confidence(text: str) -> tuple[float, str]:
    tokens = [t.strip(".,;:!?\"'").lower() for t in text.split() if t.strip()]
    if not tokens:
        return 0.0, "inferred"
    covered = 0
    known = 0
    try:
        from wordrare.database import WordRecord, get_session

        with get_session() as session:
            for token in tokens[:30]:
                row = session.query(WordRecord).filter(WordRecord.lemma == token).first()
                if row is None:
                    continue
                known += 1
                ipa = getattr(row, "ipa_us_cmu", None) or getattr(row, "ipa_dict", None)
                if ipa:
                    covered += 1
        if known == 0:
            return 0.35, "inferred"  # rule-only prior
        return max(0.2, min(0.98, covered / float(known))), "measured"
    except Exception:
        # Vowel-group heuristic coverage proxy
        groups = sum(1 for t in tokens if re.search(r"[aeiouy]", t))
        return max(0.25, min(0.6, groups / float(len(tokens)))), "inferred"


def _syllable_fit(orig: str, revised: str) -> tuple[float, str]:
    try:
        from spws_analysis import analyze_poem

        o = analyze_poem(orig)
        r = analyze_poem(revised)
        oc = o.lines[0].syllable_count if o.lines else len(orig.split())
        rc = r.lines[0].syllable_count if r.lines else len(revised.split())
        delta = abs(rc - oc)
        # 1.0 perfect fit; decays with delta
        score = max(0.0, 1.0 - 0.2 * delta)
        return float(score), "measured"
    except Exception:
        delta = abs(len(revised.split()) - len(orig.split()))
        return max(0.0, 1.0 - 0.25 * delta), "inferred"


def _stress_metre_fit(orig: str, revised: str) -> tuple[float, str]:
    try:
        from spws_analysis import analyze_poem

        o = analyze_poem(orig)
        r = analyze_poem(revised)
        if o.lines and r.lines and o.lines[0].foot_accuracy is not None:
            return float(r.lines[0].foot_accuracy or 0.0), "measured"
        os_ = (o.lines[0].stress_pattern or "") if o.lines else ""
        rs = (r.lines[0].stress_pattern or "") if r.lines else ""
        if not os_ or not rs:
            return 0.45, "inferred"
        match = sum(1 for a, b in zip(os_, rs) if a == b)
        return match / float(max(len(os_), len(rs), 1)), "measured"
    except Exception:
        return 0.4, "inferred"


def _rhyme_fit(orig: str, revised: str) -> tuple[float, str]:
    def tail(s: str) -> str:
        words = s.split()
        if not words:
            return ""
        w = words[-1].lower().strip(".,;:!?\"'")
        return w[-3:] if len(w) >= 3 else w

    ot, rt = tail(orig), tail(revised)
    if not ot or not rt:
        return 0.5, "inferred"
    if ot == rt:
        return 1.0, "measured"
    # partial coda overlap
    shared = len(set(ot) & set(rt)) / float(max(len(set(ot) | set(rt)), 1))
    return float(shared), "measured"


def _register_voice(orig: str, revised: str) -> tuple[float, str]:
    def avg_len(s: str) -> float:
        toks = [t for t in _WORD_RE.findall(s)]
        if not toks:
            return 0.0
        return sum(len(t) for t in toks) / float(len(toks))

    o, r = avg_len(orig), avg_len(revised)
    if o <= 0:
        return 0.5, "inferred"
    delta = abs(r - o) / o
    return float(max(0.0, 1.0 - delta)), "measured"


def _repetition_motif(orig: str, revised: str) -> tuple[float, str]:
    def ratio(s: str) -> float:
        toks = [m.group(0).lower() for m in _WORD_RE.finditer(s)]
        if len(toks) < 2:
            return 0.0
        from collections import Counter

        counts = Counter(toks)
        return sum(n - 1 for n in counts.values() if n > 1) / float(len(toks))

    # Higher score = better (less bad repetition introduced)
    o_r, r_r = ratio(orig), ratio(revised)
    score = max(0.0, min(1.0, 1.0 - r_r + 0.15 * max(0.0, o_r - r_r)))
    return float(score), "measured"


def _source_grounding(grounding_refs: list[Any] | None, candidate: str) -> tuple[float, str]:
    refs = grounding_refs or []
    if not refs:
        return 0.0, "inferred"
    hits = 0
    cand_tokens = set(t.lower() for t in candidate.split() if len(t) > 3)
    for ref in refs:
        if isinstance(ref, dict):
            text = str(ref.get("text") or ref.get("span_quote") or "")
        else:
            text = str(ref)
        ref_tokens = set(t.lower() for t in text.split() if len(t) > 3)
        if cand_tokens & ref_tokens:
            hits += 1
    return min(1.0, hits / float(max(len(refs), 1))), "measured"


def _quotation_risk(candidate: str, grounding_refs: list[Any] | None) -> tuple[float, str]:
    """High value = high risk. Long verbatim overlap with grounding."""
    refs = grounding_refs or []
    if not refs:
        return 0.0, "measured"
    cand = candidate.strip().lower()
    risk = 0.0
    for ref in refs:
        text = str(ref.get("text") if isinstance(ref, dict) else ref).strip().lower()
        if not text:
            continue
        if cand and cand in text:
            risk = max(risk, min(1.0, len(cand) / float(max(len(text), 1))))
        elif text and text in cand:
            risk = max(risk, 0.85)
    return float(risk), "measured"


def _constraint_compliance(
    orig: str,
    revised: str,
    work_plan: dict | None,
    config: Any,
) -> tuple[float, str]:
    checks: list[float] = []
    labels: list[str] = []
    try:
        from spws_planning.constraints import (
            check_length_bound,
            check_meter_delta,
            check_semantic_retention,
        )

        length = check_length_bound(orig, revised)
        checks.append(1.0 if length.get("ok") else 0.0)
        labels.append(str(length.get("inferred_label") or "measured"))

        try:
            from spws_analysis import analyze_poem

            o = analyze_poem(orig)
            r = analyze_poem(revised)
            oc = o.lines[0].syllable_count if o.lines else len(orig.split())
            rc = r.lines[0].syllable_count if r.lines else len(revised.split())
            meter = check_meter_delta(oc, rc)
            checks.append(1.0 if meter.get("ok") else 0.0)
            labels.append(str(meter.get("inferred_label") or "measured"))
        except Exception:
            pass

        if config is not None:
            try:
                from spws_semantics import MeaningGauge

                gauge = MeaningGauge.from_config(config)
                ret = check_semantic_retention(orig, revised, gauge)
                checks.append(1.0 if ret.get("ok") else float(ret.get("measured") or 0.0))
                labels.append(str(ret.get("inferred_label") or "inferred"))
            except Exception:
                pass
    except Exception:
        # Soft length heuristic
        ratio = len(revised) / float(max(len(orig), 1))
        checks.append(1.0 if ratio <= 1.3 and "\n" not in revised else 0.0)
        labels.append("inferred")

    _ = work_plan
    if not checks:
        return 0.5, "inferred"
    score = sum(checks) / float(len(checks))
    label = "measured" if any(x == "measured" for x in labels) else "inferred"
    return float(score), label


def _improve_degrade(results: dict[str, EvaluationResult]) -> tuple[list[str], list[str]]:
    improve: list[str] = []
    degrade: list[str] = []
    # Higher-is-better criteria
    higher = {
        "semantic_retention",
        "grammatical_acceptability",
        "pronunciation_confidence",
        "syllable_fit",
        "stress_metre_fit",
        "rhyme_fit",
        "register_voice",
        "repetition_motif",
        "source_grounding",
        "constraint_compliance",
    }
    # Lower-is-better
    lower = {"quotation_risk"}
    for name in higher:
        res = results.get(name)
        if res is None or res.measured_value is None:
            continue
        if res.measured_value >= 0.65:
            improve.append(name)
        elif res.measured_value <= 0.4:
            degrade.append(name)
    for name in lower:
        res = results.get(name)
        if res is None or res.measured_value is None:
            continue
        if res.measured_value <= 0.2:
            improve.append(name)
        elif res.measured_value >= 0.5:
            degrade.append(name)
    return improve, degrade


def build_evaluation_bundle(
    original_span: str,
    candidate: str,
    *,
    work_plan: dict | None = None,
    config: Any | None = None,
    grounding_refs: list[Any] | None = None,
    subject_id: str | None = None,
) -> tuple[EvaluationBundle, list[str], list[str]]:
    """Emit ALL D007 criteria with inferred_label measured|inferred|human_judged.

    human_preference is null until decide. Returns (bundle, improve, degrade).
    """
    subject = subject_id or new_id("cand")
    results_map: dict[str, EvaluationResult] = {}

    def add(criterion: str, value: float | None, label: str, evidence: list[str] | None = None) -> None:
        results_map[criterion] = EvaluationResult(
            evaluation_id=new_id("ev"),
            subject_id=subject,
            criterion=criterion,
            measured_value=value,
            inferred_label=label,
            evidence=evidence or [],
        )

    v, lab = _cosine_retention(original_span, candidate, config)
    add("semantic_retention", v, lab)

    v, lab = _grammatical_acceptability(candidate)
    add("grammatical_acceptability", v, lab)

    v, lab = _pronunciation_confidence(candidate)
    add("pronunciation_confidence", v, lab)

    v, lab = _syllable_fit(original_span, candidate)
    add("syllable_fit", v, lab)

    v, lab = _stress_metre_fit(original_span, candidate)
    add("stress_metre_fit", v, lab)

    v, lab = _rhyme_fit(original_span, candidate)
    add("rhyme_fit", v, lab)

    v, lab = _register_voice(original_span, candidate)
    add("register_voice", v, lab)

    v, lab = _repetition_motif(original_span, candidate)
    add("repetition_motif", v, lab)

    v, lab = _source_grounding(grounding_refs, candidate)
    add("source_grounding", v, lab)

    v, lab = _quotation_risk(candidate, grounding_refs)
    add("quotation_risk", v, lab)

    v, lab = _constraint_compliance(original_span, candidate, work_plan, config)
    add("constraint_compliance", v, lab)

    # Null until human decide
    add("human_preference", None, "human_judged", evidence=["pending_decision"])

    for name in ALL_CRITERIA:
        assert name in results_map, f"missing criterion {name}"

    improve, degrade = _improve_degrade(results_map)
    bundle = EvaluationBundle(
        bundle_id=new_id("eb"),
        subject_id=subject,
        results=[results_map[c] for c in ALL_CRITERIA],
        created_at=datetime.now(UTC),
    )
    return bundle, improve, degrade
