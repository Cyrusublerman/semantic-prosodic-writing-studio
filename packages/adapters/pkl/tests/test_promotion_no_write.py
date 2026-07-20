from spws_pkl_adapter.promotion.promotion import PromotionExporter


def test_promotion_export_does_not_mutate_library(spws_config, promotion_bundle, git_library):
    exporter = PromotionExporter(spws_config)
    before = exporter.snapshot_library_text()
    out_dir = exporter.export_bundle(promotion_bundle)
    after = exporter.snapshot_library_text()

    assert out_dir.is_dir()
    assert (out_dir / "bundle.json").is_file()
    assert (out_dir / "review.patch").is_file()
    assert exporter.assert_library_unmodified(before)
    assert before == after
    assert len(before["alpha.md"]) == 64  # sha256 hex fingerprint
    assert (git_library / "alpha.md").read_text(encoding="utf-8").startswith("---")
