import importlib


def test_import_abm_components():
    mods = [
        "abm.lf_components.audiobook.abm_chapter_loader",
        "abm.lf_components.audiobook.abm_block_schema_validator",
        "abm.lf_components.audiobook.abm_mixed_block_resolver",
        "abm.lf_components.audiobook.abm_span_classifier",
        "abm.lf_components.audiobook.abm_span_iterator",
        "abm.lf_components.audiobook.abm_artifact_orchestrator",
    ]
    for m in mods:
        importlib.import_module(m)


def test_component_classes_exist():
    from abm.lf_components.audiobook.abm_artifact_orchestrator import (
        ABMArtifactOrchestrator,
    )
    from abm.lf_components.audiobook.abm_block_schema_validator import (
        ABMBlockSchemaValidator,
    )
    from abm.lf_components.audiobook.abm_chapter_loader import ABMChapterLoader
    from abm.lf_components.audiobook.abm_mixed_block_resolver import (
        ABMMixedBlockResolver,
    )
    from abm.lf_components.audiobook.abm_span_classifier import ABMSpanClassifier
    from abm.lf_components.audiobook.abm_span_iterator import ABMSpanIterator

    # Minimal sanity: classes are defined and have a name attribute via LangFlow Component
    for cls in [
        ABMChapterLoader,
        ABMMixedBlockResolver,
        ABMSpanClassifier,
        ABMSpanIterator,
        ABMBlockSchemaValidator,
        ABMArtifactOrchestrator,
    ]:
        assert cls.__name__.startswith("ABM")

