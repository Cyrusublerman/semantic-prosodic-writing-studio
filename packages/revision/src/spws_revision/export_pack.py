"""D014 export pack: clean text, annotated md/html, bundle, provenance, version diff."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from spws_contracts_core.domain import ManuscriptVersion, PublicationBundle, RevisionDecision
from spws_domain.ids import new_id


def _html_escape(value: str) -> str:
    return html.escape(value, quote=True)


def _as_dict(value: Any) -> dict | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    return None


def _criteria_names(evaluation_data: dict | None) -> list[str]:
    if not evaluation_data:
        return []
    named = evaluation_data.get("evaluation_criteria") or evaluation_data.get("criteria") or []
    if named:
        return [str(c) for c in named if c]
    results = evaluation_data.get("results") or []
    return list(
        dict.fromkeys(str(item.get("criterion")) for item in results if item.get("criterion"))
    )


def build_export_pack(
    manuscript: ManuscriptVersion | dict,
    diagnosis: Any,
    decision: RevisionDecision | dict | None,
    run_manifest: dict | None,
    *,
    out_dir: Path | str,
    evaluation: Any | None = None,
) -> dict:
    """Write export files under ``out_dir`` and return a summary dict.

    ``diagnosis`` and ``evaluation`` are accepted separately so annotated.html can
    render both problem diagnosis and D007 evaluation criteria when present.
    """
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)

    if isinstance(manuscript, dict):
        ms = ManuscriptVersion.model_validate_json(json.dumps(manuscript))
    else:
        ms = manuscript

    if decision is not None and hasattr(decision, "model_dump"):
        decision_data = decision.model_dump(mode="json")
    else:
        decision_data = decision

    diagnosis_data = diagnosis if isinstance(diagnosis, dict) else _as_dict(diagnosis)
    evaluation_data = _as_dict(evaluation)
    # Backward compat: older callers passed a combined analysis dict with results.
    if evaluation_data is None and isinstance(diagnosis_data, dict) and "results" in diagnosis_data:
        evaluation_data = diagnosis_data
        if "problem_type" not in diagnosis_data:
            diagnosis_data = None

    clean_txt = root / "clean.txt"
    clean_md = root / "clean.md"
    annotated_md = root / "annotated.md"
    annotated_html = root / "annotated.html"
    bundle_json = root / "bundle.json"
    provenance_md = root / "provenance.md"
    version_diff_md = root / "version_diff.md"

    clean_txt.write_text(ms.text + ("\n" if not ms.text.endswith("\n") else ""), encoding="utf-8")
    clean_md.write_text(f"# Manuscript {ms.version_id}\n\n{ms.text}\n", encoding="utf-8")

    ann_lines = [f"# Annotated manuscript `{ms.version_id}`", ""]
    html_blocks: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en-AU">',
        "<head>",
        '<meta charset="utf-8"/>',
        f"<title>Annotated manuscript {ms.version_id}</title>",
        "</head>",
        "<body>",
        f"<header><h1>Annotated manuscript <code>{ms.version_id}</code></h1></header>",
    ]

    if isinstance(diagnosis_data, dict) and "problem_type" in diagnosis_data:
        ann_lines.append(f"- Diagnosis: `{diagnosis_data.get('problem_type')}`")
        ann_lines.append(f"- Target line: `{diagnosis_data.get('target_line_index')}`")
        ann_lines.append(f"- Brief: {diagnosis_data.get('suggested_brief')}")
        ann_lines.append("")
        html_blocks.append('<section aria-label="diagnosis">')
        html_blocks.append("<h2>Diagnosis</h2>")
        html_blocks.append("<dl>")
        html_blocks.append(
            f"<dt>problem_type</dt><dd><code>{diagnosis_data.get('problem_type')}</code></dd>"
        )
        html_blocks.append(
            f"<dt>target_line_index</dt><dd><code>{diagnosis_data.get('target_line_index')}</code></dd>"
        )
        brief = diagnosis_data.get("suggested_brief") or ""
        html_blocks.append(f"<dt>brief</dt><dd>{_html_escape(str(brief))}</dd>")
        html_blocks.append("</dl></section>")

    criteria = _criteria_names(evaluation_data)
    if criteria:
        ann_lines.append("## Evaluation criteria")
        html_blocks.append('<section aria-label="evaluation-criteria">')
        html_blocks.append("<h2>Evaluation criteria</h2><ul>")
        for name in criteria:
            ann_lines.append(f"- {name}")
            html_blocks.append(f"<li>{_html_escape(name)}</li>")
        ann_lines.append("")
        html_blocks.append("</ul></section>")

    if isinstance(evaluation_data, dict) and evaluation_data.get("results"):
        ann_lines.append("## Evaluation")
        html_blocks.append('<section aria-label="evaluation">')
        html_blocks.append("<h2>Evaluation</h2><ul>")
        for item in evaluation_data.get("results") or []:
            ann_lines.append(
                f"- {item.get('criterion')}: {item.get('measured_value')} "
                f"({item.get('inferred_label')})"
            )
            html_blocks.append(
                "<li><strong>"
                f"{_html_escape(str(item.get('criterion')))}"
                "</strong>: "
                f"{_html_escape(str(item.get('measured_value')))} "
                f"(<em>{_html_escape(str(item.get('inferred_label')))}</em>)</li>"
            )
        ann_lines.append("")
        html_blocks.append("</ul></section>")

    ann_lines.append("## Text")
    ann_lines.append("")
    html_blocks.append('<section aria-label="text"><h2>Text</h2><ol class="lines">')
    for index, line in enumerate(ms.text.splitlines() or [ms.text]):
        ann_lines.append(f"{index}: {line}")
        html_blocks.append(f'<li value="{index}">{_html_escape(line)}</li>')
    html_blocks.append("</ol></section></body></html>")
    annotated_md.write_text("\n".join(ann_lines) + "\n", encoding="utf-8")
    annotated_html.write_text("\n".join(html_blocks) + "\n", encoding="utf-8")

    bundle = {
        "manuscript": ms.model_dump(mode="json"),
        "diagnosis": diagnosis_data,
        "evaluation": evaluation_data,
        "decision": decision_data,
        "run_manifest": run_manifest or {},
    }
    bundle_json.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    prov = [
        f"# Provenance — {ms.version_id}",
        "",
        f"- manuscript_id: `{ms.manuscript_id}`",
        f"- version_id: `{ms.version_id}`",
        f"- parents: {', '.join(ms.parent_version_ids) or '(root)'}",
        f"- accepted_change_ids: {', '.join(ms.accepted_change_ids) or '(none)'}",
        f"- created_at: {ms.created_at}",
        "",
        "## Provenance map",
        "",
        "```json",
        json.dumps(ms.provenance_map, indent=2),
        "```",
        "",
    ]
    if run_manifest:
        prov.extend(["## Run manifest", "", "```json", json.dumps(run_manifest, indent=2), "```", ""])
    provenance_md.write_text("\n".join(prov), encoding="utf-8")

    parent_note = ms.parent_version_ids[0] if ms.parent_version_ids else None
    diff_lines = [
        f"# Version diff — {ms.version_id}",
        "",
        f"Parent: `{parent_note or 'none'}`",
        "",
        "## Current text",
        "",
        "```",
        ms.text,
        "```",
        "",
    ]
    if decision_data and decision_data.get("resulting_text") and decision_data.get("resulting_text") != ms.text:
        diff_lines.extend(
            [
                "## Decision resulting_text",
                "",
                "```",
                str(decision_data.get("resulting_text")),
                "```",
                "",
            ]
        )
    version_diff_md.write_text("\n".join(diff_lines), encoding="utf-8")

    files = {
        "clean.txt": str(clean_txt),
        "clean.md": str(clean_md),
        "annotated.md": str(annotated_md),
        "annotated.html": str(annotated_html),
        "bundle.json": str(bundle_json),
        "provenance.md": str(provenance_md),
        "version_diff.md": str(version_diff_md),
    }

    publication = PublicationBundle(
        bundle_id=new_id("pub"),
        manuscript_id=ms.manuscript_id,
        version_id=ms.version_id,
        clean_text=ms.text,
        export_files=files,
        decision_id=(decision_data or {}).get("decision_id") if isinstance(decision_data, dict) else None,
        run_id=(run_manifest or {}).get("run_id") if run_manifest else None,
        created_at=datetime.now(UTC),
    )
    publication_data = publication.model_dump(mode="json")
    (root / "publication_bundle.json").write_text(
        json.dumps(publication_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    files["publication_bundle.json"] = str(root / "publication_bundle.json")

    return {
        "out_dir": str(root),
        "files": files,
        "manuscript_id": ms.manuscript_id,
        "version_id": ms.version_id,
        "publication_bundle": publication_data,
    }
