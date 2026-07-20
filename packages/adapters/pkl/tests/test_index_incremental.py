import subprocess
import textwrap

from spws_pkl_adapter.indexer.indexer import open_catalogue
from spws_pkl_adapter.resolver.resolver import PKLResolver


def _write_doc(path, uid: str, body: str) -> None:
    path.write_text(
        textwrap.dedent(
            f"""\
            ---
            uid: "{uid}"
            title: "{uid}"
            object_type: note
            rights: public
            privacy: public
            ---

            {body}
            """
        ),
        encoding="utf-8",
    )


def test_incremental_index_updates_changed_file(spws_config, git_library, indexer):
    manifest = indexer.build_full()
    assert manifest.record_count >= 2

    resolver = PKLResolver(spws_config.index_root)
    alpha = resolver.resolve_uid("uid-alpha")
    assert alpha is not None
    original_digest = alpha.digest.value

    alpha_path = git_library / "alpha.md"
    _write_doc(alpha_path, "uid-alpha", "Alpha body about rivers and streams.")
    subprocess.run(["git", "add", "alpha.md"], cwd=git_library, check=True)
    subprocess.run(["git", "commit", "-m", "update alpha"], cwd=git_library, check=True)

    updated_manifest = indexer.update_incremental()
    assert updated_manifest.commit_sha != manifest.commit_sha

    alpha_after = resolver.resolve_uid("uid-alpha", commit=updated_manifest.commit_sha)
    assert alpha_after is not None
    assert alpha_after.digest.value != original_digest

    conn = open_catalogue(spws_config.index_root / "catalogue.sqlite")
    try:
        excluded = conn.execute("SELECT COUNT(*) FROM records WHERE excluded = 1").fetchone()[0]
        assert excluded >= 1
    finally:
        conn.close()
