# Public-index delivery of the existing software release (#127)

Research and plan, 2026-11-26.

## Consumer need and existing mechanisms

The four verified source-tree consumers use the published rc1 GitHub wheel:
ORAEC has an explicit wheel-acquisition step, and IIP, Coptic and CATSS use
direct SHA256-pinned URL requirements. The [PyPA direct-reference specification](https://packaging.python.org/en/latest/specifications/version-specifiers/#direct-references)
discourages direct references in distributions uploaded to public indexes.
A normal PyPI name/version would remove this installation barrier and allow
normal downstream software metadata. Do not change any consumer pin before
actual availability and compatible consumer E2E.

The current main candidate is rc2 at 5802e8093178a3d6e89e86abdfb0abbf3eb6eefd
with green main CI; #122 awaits an owner-created tag and protected GitHub
release dispatch. Actual GitHub Releases exposes only rc1, whose wheel,
sdist and manifest exist. rc1's tagged runtime __version__ is
0.1.0.dev0, not its distribution version; do not promote that mismatch.
The PyPI name/ownership was not verifiable from this environment. The owner
must confirm ownership/availability and configure a pending Trusted Publisher.

CAL-MCP's existing release.yml demonstrates isolated OIDC publication via
pypa/gh-action-pypi-publish@release/v1. PyPA's
[Trusted Publisher setup](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
supports first publication without storing a token. Reuse this ordinary path.

## Plan before changes

1. Test first against the actual existing wheel_manifest.py CLI. Its generation
   already validates the wheel and sdist names/metadata, source revision,
   tag and bytes. Add an exclusive --verify-existing mode to compare a
   canonical release manifest from an independently downloaded asset set.
   A valid pair passes without writing anything; changed wheel, sdist,
   manifest or source identity fails. Reuse the canonical JSON encoding.
2. One separate owner-dispatched publish-pypi.yml (not triggered on push/tag/PR).
   Read-only preparation fetches the published wheel, sdist and manifest
   anonymously at an explicit version tag already in main, compares the
   recomputed manifest, and runs the existing tagged installed-wheel
   example plus an explicit distribution/runtime version agreement check.
   Only the exact two checked distribution files go to a CI artifact.
   No rebuild or GitHub asset edits. Test workflow boundaries and actual
   verification on the existing deterministic wheel/sdist fixtures.
3. Isolated protected pypi environment job downloads the verified pair
   and uses the existing PyPA action with id-token: write only there.
   A later read-only job downloads the exact named wheel from PyPI, compares
   bytes with the CI artifact, installs in a fresh venv and runs the tagged
   Text-Fabric smoke. No index publication attempted in PR CI.
4. Document the owner setup and independent GitHub release path. Run exact-head
   existing quality/pytest 3.11–3.14, installed-wheel direct/sdist/offline
   TF E2E and producer inventory. Independently review actual diff, shell
   and permissions, negative byte fixtures and final CI.

This is a release-only maintainer path, not a general publisher or a new
trust/certification system. No new package APIs, corpus data, version bump,
automatic publishing, release or downstream dependency changes. #127
remains open until the owner runs the real public-index acceptance.
