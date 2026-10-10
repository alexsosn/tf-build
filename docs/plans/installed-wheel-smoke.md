# Plan: wheel distribution check

Issue #41

1. RED-first standalone scripts/check_installed_wheel.py: require a repository-root argument; verify installed tf-build distribution metadata and import all documented public modules, check each module path outside the checkout, test immutable SHA and exact CR-safe string behavior, and fail with actionable nonzero exit on missing package or missing API.
2. CI distribution job: checkout and Python 3.12; create empty private venv; run script from a noncheckout working directory, explicitly require its failure before wheel installation; then run pip wheel --no-deps ., install the built wheel and its dependencies in that venv, and run script to GREEN.
3. Avoid mutable global site packages / editable installs in distribution verification and do not alter existing full Python 3.11-3.14 quality matrix.
4. Add concise README developer instructions for local reproduction. No release tags, publish permissions, upload actions or package API broadening.
5. Final exact-head GitHub Actions including four quality jobs and distribution gate green, followed by logically independent adversarial review of actual wheel-import path, package modules and CI isolation.
