# Public Text-Fabric producer coverage audit — 2026-10-12

Tracking issue: [#90](https://github.com/alexsosn/tf-build/issues/90).

## Scope and source evidence

GitHub's owner inventory currently has 44 public, non-fork repositories.
The reviewed manifest deliberately classifies **every one**, including the
33 repositories that do not produce TF corpora or modules. This ensures a
newly published public non-fork repository fails the central CI gate until
someone decides if it is a producer.

Nine implementations and their actual PR CI proof were inspected:
CTC-TF (CUC-aligned Burns module), TLHdig-TF, ORACC-TF,
Pseudepigrapha-TF, CopticScriptorium-TF, CATSS-TF, IIP-TF,
ORAEC-TF and BHSA-cantillation-trees. Both incomplete producers are
tracked: PG-TF #3/#4 (converter/validator) and OpenGreek-TF #6/#9
(complete served corpus writer/whole-corpus independent validator).
OpenGreek also ships native-TF partial writers and pinned-source smoke
workflows; its classification stays `tracked` until the complete supported
snapshot is built and verified.

`cuc-morph` produces TSV morphology annotations, not a TF corpus or
module, and `UgaritOCR` produces recognized text / searchable PDFs.
`midrash-atlas` produces Sefaria citation graphs, and `ontoTF` maps
semantic concepts onto existing TF corpora. These are excluded from
**the producer contract**, not assessed as broken projects. Source
corpus forks are excluded by the live GitHub `fork` flag.

## Policy

Edit `policy/public-tf-producers.json` in a reviewed PR. To change an
entry to `supported`, identify a real source/writer/test file plus a
PR-triggered GitHub Actions workflow with a specific executable test
invocation. For `tracked`, provide an **open** issue for native TF
support and an existing PR CI workflow. Closing an implementation issue
before changing the policy is intentionally a CI failure.

The script reads **public** owner repository metadata and only the
explicitly declared producer files/issues through GitHub's REST API. It
does not access or enumerate private repository contents, download
upstream corpora, execute remote code, mutate GitHub state, or publish
data. It fails closed on API errors, inventory drift, missing files,
missing PR trigger, missing workflow command, or a closed tracking issue.
All IO is bounded and has a timeout. The audit runs for every PR to
`tf-build`, on main pushes, and every Monday.

## Limits (do not overclaim)

This static cross-repository policy audit checks **coverage and declared
CI wiring**, not whether upstream CI runs are currently green. It cannot
prove that a path-filtered job ran for every relevant change, that
`pytest` executed a specific native TF test, that large corpus builds
fit resources, or that the corpus semantics are correct. Stronger
per-repository jobs must actually generate/reload Text-Fabric and compare
source facts to loaded nodes and features. New projects cannot be
classified as supported on README claims alone.

For recurring full-corpus checks, pin immutable source revisions, avoid
downloading licensed raw data into artifacts, and retain independent
source-vs-TF conservation tests. If a producer's PR CI is path-filtered,
validate that filter when changing conversion paths; a generic passing
workflow must not mask skipped native validation.

## Running

```bash
python -m pytest -q tests/test_audit_tf_producers.py
GITHUB_TOKEN=... python scripts/audit_tf_producers.py policy/public-tf-producers.json
```

Without a token the script uses public unauthenticated API quotas. Never
print a token, request headers or a credential-bearing URL.
