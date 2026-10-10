# Research: quality CI never installs the distributed wheel

Issue #41

## Existing build contract

pyproject.toml uses setuptools.build_meta, finds packages under src, requires Python 3.11+, and declares text-fabric>=13.1,<14 as a runtime dependency. .github/workflows/ci.yml currently uses pip install -e '.[dev]' and then Ruff/mypy/pytest on Python 3.11, 3.12, 3.13 and 3.14. All these jobs may import directly from the checkout. They do not prove that a built wheel contains the public modules, correct metadata, or dependencies and can be imported by a clean consumer.

## Minimal consumer evidence

The public modules actually present under src/tf_build include agora, feature_docs, fingerprint, report, source, tf_strings, validate and workspace. Several import Text-Fabric while the rest use only stdlib. A pure Python wheel should contain the package and the public APIs. An isolated installed-wheel smoke must import all these modules and exercise a simple Git full-SHA validator and CR-safe string preflight from a noneditable venv.

## Design

Build one wheel from HEAD with pip wheel --no-deps into an ephemeral runner-owned directory. Create a fresh venv without the editable source path and first run the smoke before installing the wheel, requiring RED (missing distribution). Then install the wheel with its runtime requirements and run the same check to GREEN from outside the checkout. Require the imported package path to be outside the repository root to prevent accidentally accepting editable installs.

Use a dedicated CI distribution job on Python 3.12. The existing four matrix jobs already establish interpreter compatibility, while one clean installed artifact smoke tests the wheel packaging, with no PyPI upload, secrets, publishing or arbitrary plugin execution. Python's stdlib importlib.metadata provides independent version evidence.

## Limits

This does not certify reproducible wheel bytes, signatures, future compatibility with another TF major version, sdist completeness or release readiness; those need separate demonstrated requirements.
