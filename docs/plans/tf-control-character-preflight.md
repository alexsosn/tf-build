# Plan: fail-closed CR preflight for TF values

Issue #37

1. RED-first real Text-Fabric oracle: generate a tiny word/slot dataset with consecutive distinct node values, one containing literal U+000D, and a valued-edge string with literal U+000D. Verify actual serialized bytes/real loader show lost data or misattribution; do not only assert slot counts.
2. RED-first APIs: node string with CR fails with feature and node context but no raw content; valued edge with CR fails with feature, source and target context; LF, TAB, backslash, Unicode and int/None pass unmodified; unvalued edge sets are skipped. Include no-mutation assertions.
3. Implement the minimal pure tf_build.tf_strings module containing require_tf_safe_string (also usable per value from CV.walk) and preflight_tf_save_values over ordinary Fabric.save dictionaries. No corpus ontology or custom writer.
4. Document call sequence: source parse, optional consumer-specific lossless codec, preflight, TF writer, real roundtrip comparison. Include concrete ORAEC CR misattribution reference.
5. Exact-head Ruff, strict mypy and real Fabric.save/Fabric.load tests on Python 3.11-3.14, then genuinely independent adversarial review based on actual raw values and upstream serializer.
