# Plan: strict, bounded release manifest package identity (#72)

1. Add synthetic real-file fixtures using `zipfile.ZipFile` and `tarfile.open` for duplicate identity headers in both wheel and sdist, missing required `Metadata-Version`/`Name`/`Version`, malformed metadata headers and a >1MiB compressed wheel METADATA. Commit regression tests **alone** and record observed RED CI on actual current code (while lint/type checking remains green).
2. Add private `_validate_package_metadata(raw, name, version, source)` helper that parses `BytesParser`, rejects `.defects` and requires exactly one nonempty `Metadata-Version`, `Name`, `Version`; existing strict comparison to expected package and version remains.
3. Add a bounded ZIP metadata read to the wheel branch using `getinfo().file_size` and `open(...).read(_MAX_METADATA_BYTES + 1)`; preserve `WheelManifestError` for oversized/invalid content. Keep existing bounded tar PKG-INFO read and use the same identity helper.
4. Run exact-head Python 3.11–3.14 quality matrix; test actual wheel+sdist rebuild/parity, independent installed-wheel check and offline wheelhouse. Log head SHA and test outcomes.
5. Skeptical, logically independent adversarial review of frozen diff, malformed real archives and CI evidence. Fix+re-review on any blocking finding. Merge only with successful gates; do not create tag, release, or consumer migration.
